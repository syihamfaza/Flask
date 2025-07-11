import eventlet
eventlet.monkey_patch()

import os
import re
import uuid
import shutil
import zipfile
import fitz  # PyMuPDF
import pikepdf
import pandas as pd
from PIL import Image
from pathlib import Path
from flask import Flask, render_template,render_template_string, request, send_file
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from flask import jsonify, redirect
import subprocess
import win32print
from PyPDF2 import PdfMerger
import unicodedata

from check_stock import run_checker
from map import run_map
from AutoCollect import collect
from menu_penyaluran import run_penyaluran
from menu_InOut import run_inout

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'


UPLOAD_FOLDER = 'D:\\Code\\uploads'
OUTPUT_FOLDER = 'D:\\Code\\result'
OUTPUT_CSV = os.path.join(OUTPUT_FOLDER, 'output.csv')
download_dir = str(Path.home() / "Downloads")
sumatra_path = r"C:\Users\win 10\AppData\Local\SumatraPDF\SumatraPDF.exe"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")
process_control = {}

# ========== Part of Read Logbook ==========
def normalize_text(text):
    return unicodedata.normalize("NFKD", text).replace("\xa0", " ").replace("\u200b", "")

def extract_value(text, label):
    pattern = rf"{label}\D*(\d+)\s*Tbg"
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).zfill(3) if match else "000"

# ========== Routes ==========
@app.route('/')
def index():
    default = win32print.GetDefaultPrinter()
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
    return render_template('index.html', default=default, printers=printers)

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# ========== Read Logbook ==========
@app.route("/", methods=["GET", "POST"])
def baca_logbook():
    data_rows = []

    if request.method == "POST":
        # Hapus isi upload folder jika ada
        shutil.rmtree(UPLOAD_FOLDER, ignore_errors=True)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        zip_file = request.files.get("zipfile")
        if zip_file and zip_file.filename.endswith(".zip"):
            zip_path = os.path.join(UPLOAD_FOLDER, secure_filename(zip_file.filename))
            zip_file.save(zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(UPLOAD_FOLDER)
            os.remove(zip_path)

            for filename in os.listdir(UPLOAD_FOLDER):
                if filename.endswith(".pdf"):
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    doc = fitz.open(file_path)
                    text = "".join([page.get_text() for page in doc])
                    doc.close()

                    text = normalize_text(text)

                    data_rows.append({
                        "Filename": filename,
                        "Rumah Tangga": extract_value(text, "Rumah Tangga"),
                        "Usaha Mikro": extract_value(text, "Usaha Mikro"),
                        "Total": extract_value(text, "Total")
                    })

            # Simpan ke CSV
            pd.DataFrame(data_rows).to_csv(OUTPUT_CSV, index=False)

    return render_template("index.html", data=data_rows)

@app.route("/download")
def download():
    return send_file(OUTPUT_CSV, as_attachment=True)

# ========== PDF Unlock ==========
@app.route("/unlock", methods=['POST'])
def unlock():
    passwords = request.form.getlist('passwords')
    pdf_files = request.files.getlist('pdfs')
    session_id = str(uuid.uuid4())
    session_output = os.path.join(OUTPUT_FOLDER, session_id)
    os.makedirs(session_output, exist_ok=True)

    failed_files = []

    for pdf_file, password in zip(pdf_files, passwords):
        filename = secure_filename(pdf_file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        output_path = os.path.join(session_output, filename)
        pdf_file.save(input_path)

        try:
            with pikepdf.open(input_path, password=password) as pdf:
                pdf.save(output_path)
        except pikepdf._qpdf.PasswordError:
            failed_files.append(filename)
        except Exception as e:
            failed_files.append(f"{filename} (error: {str(e)})")

    zip_path = os.path.join(OUTPUT_FOLDER, f"{session_id}.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(session_output):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)

    if failed_files:
        return render_template("index.html", failed_unlock=failed_files, download_link=f"/result/{session_id}.zip")
    else:
        return send_file(zip_path, as_attachment=True)
@app.route("/result/<filename>")
def result_file(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist('files')
    for file in files:
        if file and file.filename.endswith('.pdf'):
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
    return redirect('/files')

@app.route('/files')
def list_files():
    files = os.listdir(UPLOAD_FOLDER)
    return render_template('files.html',files=files)

@app.route('/files/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    return redirect('/files')

@app.route('/delete_all', methods=['POST'])
def delete_all_files():
    shutil.rmtree(UPLOAD_FOLDER)
    os.makedirs(UPLOAD_FOLDER)
    return redirect('/files')

def print_pdf(filepath):
    try:
        subprocess.run([sumatra_path, '-print-to-default', '-silent', filepath], check=True)
        return True, "Berhasil mencetak"
    except Exception as e:
        return False, str(e)

@app.route('/print/<filename>', methods=['POST'])
def print_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        success, message = print_pdf(filepath)
        status = 200 if success else 500
        return jsonify({'message': message}), status
    return jsonify({'message': 'File tidak ditemukan'}), 404

@app.route('/print_all', methods=['POST'])
def print_all():
    files = os.listdir(UPLOAD_FOLDER)
    printed = 0
    for file in files:
        filepath = os.path.join(UPLOAD_FOLDER, file)
        success, _ = print_pdf(filepath)
        if success:
            printed += 1
    return jsonify({'message': f'{printed} file berhasil dicetak'})

@app.route("/compress-photo", methods=['GET', 'POST'])
def compress_photo():
    compressed_folder = os.path.join(OUTPUT_FOLDER, 'compressed_photos')
    os.makedirs(compressed_folder, exist_ok=True)
    image_rows = []

    if request.method == 'POST':
        files = request.files.getlist('photos')
        for file in files:
            if file and file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filename = secure_filename(file.filename)
                input_path = os.path.join(UPLOAD_FOLDER, filename)
                output_path = os.path.join(compressed_folder, filename)
                file.save(input_path)

                try:
                    img = Image.open(input_path)
                    img.thumbnail((1024, 1024))
                    img.save(output_path, optimize=True, quality=70)
                    image_rows.append({'filename': filename})
                except Exception as e:
                    print(f"❌ Gagal memproses {filename}: {e}")

    return render_template('index.html', compressed=image_rows)

@app.route("/compressed/<filename>")
def download_compressed_file(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, 'compressed_photos', filename), as_attachment=True)

@app.route("/edit-pdf", methods=['POST'])
def edit_pdf():
    text_agen = request.form.get('agen', '').strip()
    text_nama = request.form.get('nama', '').strip()
    text_jabatan = request.form.get('jabatan', '').strip()
    halaman_ke = int(request.form.get('halaman', '2')) - 1
    pdf_files = request.files.getlist('pdf_files')

    session_id = str(uuid.uuid4())
    session_output = os.path.join(OUTPUT_FOLDER, session_id)
    os.makedirs(session_output, exist_ok=True)

    def find_position(page, label, y_offset=7):
        matches = page.search_for(label)
        for rect in matches:
            if rect.x0 > page.rect.width / 2:
                return rect.x1 + 5, rect.y0 + y_offset
        return None

    for file in pdf_files:
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        output_path = os.path.join(session_output, filename)
        file.save(input_path)

        doc = fitz.open(input_path)
        if len(doc) > halaman_ke:
            page = doc[halaman_ke]
            for label, text in [("Agen :", text_agen), ("Nama :", text_nama), ("Jabatan :", text_jabatan)]:
                pos = find_position(page, label)
                if pos:
                    page.insert_text(pos, text, fontsize=8, fontname="courier-bold", fill=(0, 0, 0))
            doc.save(output_path)
        doc.close()

    zip_path = os.path.join(OUTPUT_FOLDER, f"{session_id}.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in os.listdir(session_output):
            zipf.write(os.path.join(session_output, file), arcname=file)

    return send_file(zip_path, as_attachment=True)

# ========== SocketIO Events ==========
@socketio.on('start_check')
def handle_start(data):
    sid = request.sid
    sheet_index = int(data.get('sheet_index', 4))
    process_control[sid] = {"stop_requested": False}

    def background_task():
        socketio.emit('checker_log', "🚀 Proses pengecekan stok dimulai...", to=sid)
        run_checker(socketio, sheet_index=sheet_index, control=process_control[sid])

    socketio.start_background_task(background_task)

@socketio.on("map")
def handle_map(data):
    sid = request.sid
    sheet_index = int(data.get("sheet_index", 5))
    process_control[sid] = {"stop_requested": False}

    def background_task():
        run_map(socketio, sheet_index=sheet_index, control=process_control[sid], sid=sid)

    socketio.start_background_task(background_task)

@socketio.on("collect")
def handle_collect(data):
    sid = request.sid
    sheet_index = int(data.get("sheet_index", 4))
    bulan_index = int(data.get("bulan_index", 3))
    bulan_nama = data.get("bulan_nama", "APR")
    process_control[sid] = {"stop_requested": False}

    def background_task():
        socketio.emit('collect_log', "🚀 Proses pengumpulan data dimulai...", to=sid)
        logs = collect(socketio, sheet_index=sheet_index, bulan_index=bulan_index, bulan_nama=bulan_nama, control=process_control[sid])
        for line in logs:
            socketio.emit('collect_log', line, to=sid)
        socketio.emit('collect_log', "✅ Proses pengumpulan data selesai.", to=sid)
        socketio.emit('collect_done', to=sid)

    socketio.start_background_task(background_task)

@socketio.on("penyaluran")
def handle_penyaluran(data):
    sid = request.sid
    process_control[sid] = {"stop_requested": False}

    def background_task():
        run_penyaluran(
            username=data["username"],
            password=data["password"],
            jenis=data["jenis"],
            bulan_data=data["bulan"],
            socketio=socketio,
            sid=sid
        )
        socketio.emit('penyaluran_done', to=sid)

    socketio.start_background_task(background_task)

@socketio.on("inout")
def handle_inout(data):
    sid = request.sid
    process_control[sid] = {"stop_requested": False}

    def background_task():
        bulan = data["bulan"][0]
        run_inout(
            username=data["username"],
            password=data["password"],
            tanggal=bulan["tgl"],
            bulan_label=bulan["namaBulan"],
            download_dir=download_dir,
            socketio=socketio,
            sid=sid
        )
        socketio.emit("inout_done", to=sid)

    socketio.start_background_task(background_task)

@socketio.on("stop")
def handle_stop():
    sid = request.sid
    if sid in process_control:
        process_control[sid]["stop_requested"] = True

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    process_control.pop(sid, None)
    
# ========== PDF Page Extraction ==========
@app.route("/ambil-halaman", methods=["POST"])
def ambil_halaman_pdf():
    result_path = ""
    pdf_file = request.files["pdf"]
    halaman_input = request.form.get("halaman", "").replace(" ", "")
    halaman_list = [int(h.strip()) - 1 for h in halaman_input.split(",") if h.strip().isdigit()]
    filename = secure_filename(pdf_file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_filename = f"selected_pages_{filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    pdf_file.save(input_path)

    doc = fitz.open(input_path)
    new_doc = fitz.open()
    for i in halaman_list:
        if 0 <= i < len(doc):
            new_doc.insert_pdf(doc, from_page=i, to_page=i)
    new_doc.save(output_path)
    new_doc.close()
    doc.close()

    result_path = f"/unduh-halaman/{output_filename}"

    return render_template_string("""
        <div id="resultArea2">
            <p>✅ Halaman berhasil diproses.</p>
            <a href="{{ result }}" download>⬇️ Download Hasil</a>
        </div>
    """, result=result_path)
    
# ======== Merge PDF Files ==========
@app.route("/gabung-pdf", methods=["POST"])
def gabung_pdf():
    files = request.files.getlist("pdfs")
    order = request.form.getlist("order[]")  # nama file urut dari UI
    file_dict = {f.filename: f for f in files}

    merger = PdfMerger()
    for filename in order:
        file = file_dict.get(filename)
        if file:
            merger.append(file.stream)

    output_path = os.path.join(OUTPUT_FOLDER, "gabungan.pdf")
    merger.write(output_path)
    merger.close()
    return send_file(output_path, as_attachment=True)

# ========== Game Multiplayer ==========
players = {}
ball = {"x": 300, "y": 200, "vx": 4, "vy": 3}
paddles = {"left": 150, "right": 150}
score = {"left": 0, "right": 0}

@app.route("/game")
def game():
    return render_template("game.html")

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    if "left" not in players.values():
        players[sid] = "left"
        emit('role', "left")
    elif "right" not in players.values():
        players[sid] = "right"
        emit('role', "right")
    else:
        emit('role', "spectator")

@socketio.on('paddle_move')
def handle_paddle(data):
    if players.get(request.sid) == "left":
        paddles["left"] = data['y']
    elif players.get(request.sid) == "right":
        paddles["right"] = data['y']

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    players.pop(sid, None)

@socketio.on('reset')
def handle_reset():
    global ball, score
    ball = {"x": 300, "y": 200, "vx": 4, "vy": 3}
    score = {"left": 0, "right": 0}
    socketio.emit('state', {"ball": ball, "paddles": paddles, "score": score})

def game_loop():
    while True:
        ball["x"] += ball["vx"]
        ball["y"] += ball["vy"]

        if ball["y"] <= 0 or ball["y"] >= 400:
            ball["vy"] *= -1

        if ball["x"] <= 20 and paddles["left"] <= ball["y"] <= paddles["left"] + 80:
            ball["vx"] *= -1
        elif ball["x"] >= 580 and paddles["right"] <= ball["y"] <= paddles["right"] + 80:
            ball["vx"] *= -1

        if ball["x"] < 0:
            score["right"] += 1
            ball.update({"x": 300, "y": 200, "vx": -4, "vy": 3})
        elif ball["x"] > 600:
            score["left"] += 1
            ball.update({"x": 300, "y": 200, "vx": 4, "vy": 3})

        socketio.emit('state', {"ball": ball, "paddles": paddles, "score": score})
        socketio.sleep(1 / 60)

socketio.start_background_task(game_loop)
    
# ========== Main ==========
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
