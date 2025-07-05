from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from flask import request
import time
import gspread
import random
from oauth2client.service_account import ServiceAccountCredentials

def run_map(socketio, sheet_index=5, control=None, sid=None):
    log = []

    def emit_log(message):
        print("[LOG]", message)
        log.append(message)
        if sid:
            socketio.emit("map_log", message, to=sid)
        else:
            socketio.emit("map_log", message)

    emit_log("🔍 Memulai proses MAP...")

    # Setup headless Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    key = "D:\\Code\\key.json"

    try:
        # Setup Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(key, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key("1J-Hu6RgyJgj_5TI0YzMEhNPFpwy8RiYHvTImtszzPb8")
        sheet = spreadsheet.get_worksheet(sheet_index)
        rows = sheet.get_all_records(expected_headers=["NIK", "username", "password"])
    except Exception as sheet_err:
        emit_log(f"❌ Gagal mengakses Google Sheets: {sheet_err}")
        return log

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 20)
    except Exception as driver_err:
        emit_log(f"❌ Gagal membuka Chrome WebDriver: {driver_err}")
        return log

    indexed_rows = list(enumerate(rows, start=2))
    random.shuffle(indexed_rows)

    username = [row['username'] for row in rows if 'username' in row and row['username']][0]
    password = [row['password'] for row in rows if 'password' in row and row['password']][0]
    password = str(password).zfill(6)

    LOGIN_URL = "https://subsiditepatlpg.mypertamina.id/merchant-login"
    driver.get(LOGIN_URL)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Masukkan nomor ponsel atau 𝑒𝑚𝑎𝑖𝑙']"))).send_keys(username)
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Masukkan PIN Anda']"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Masuk']"))).click()
    emit_log(f"""🔑 Berhasil login sebagai {username}\n""")
    time.sleep(3)

    jumlah = 1

    for idx, row in indexed_rows:
        if control and control.get("stop_requested"):
            emit_log("⛔ Proses dihentikan oleh user.")
            break

        NIK = str(row.get('NIK', '')).strip()
        if not NIK.isdigit():
            emit_log(f"⚠️ Melewati baris {idx}: Data tidak lengkap atau jumlah tidak valid → {row}")
            continue

        wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Masukkan 16 digit NIK Pelanggan']"))).send_keys(NIK)
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Mulai Transaksi']"))).click()
        emit_log(f"🔍 Memproses NIK: {NIK} (Baris {idx})")
        time.sleep(2)

        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'NIK pelanggan tidak terdaftar')]"))
            )
            emit_log(f"❌ NIK tidak ditemukan: {NIK} (Baris {idx})")
            sheet.update_cell(idx, 2, "❌ NIK Tidak Ditemukan")
            driver.refresh()
            time.sleep(2)
            continue
        except:
            pass

        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[data-testid='radio-Usaha Mikro']"))
            )
            emit_log(f"✅ Usaha Mikro {NIK} ditemukan (Baris {idx}).")
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Lanjut Transaksi']"))).click()
            sheet.update_cell(idx, 1, "")
            time.sleep(2)
        except:
            pass

        berhasil = False
        for i in range(jumlah):
            try:
                tombol = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='actionIcon2']")))
                driver.execute_script("arguments[0].scrollIntoView(true);", tombol)
                tombol.click()
                berhasil = True
                break
            except TimeoutException:
                emit_log(f"⚠️ Tombol tidak muncul untuk NIK: {NIK} (Baris {idx})")

        if not berhasil:
            emit_log(f"❌ Gagal menemukan tombol actionIcon2 untuk NIK: {NIK} (Baris {idx})")
            sheet.update_cell(idx, 1, "")
            driver.refresh()
            time.sleep(2)
            continue

        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='btnCheckOrder']"))).click()
        emit_log(f"⌛ Pesanan untuk NIK {NIK} dicek.")
        time.sleep(2)

        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='btnPay']"))).click()
        time.sleep(2)

        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Ke Beranda"))).click()
        time.sleep(2)

        sheet.update_cell(idx, 1, "")
        emit_log(f"✅ Sukses : {NIK} (Baris {idx}) Qty: {jumlah}\n--------------------------------")

    driver.quit()
    emit_log("✔ Selesai memproses semua data.")
    socketio.emit("map_done", to=request.sid)
