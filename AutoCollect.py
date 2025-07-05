from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyautogui
import time
import checker
import os
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials

def collect(socketio, sheet_index=4, bulan_index=3, bulan_nama="APR", control=None):
    log = []
    control = control or {}

    def emit_log(message):
        log.append(message)
        try:
            socketio.emit("collect_log", message)
        except Exception as emit_err:
            log.append(f"⚠️ Gagal mengirim log ke client: {emit_err}")

    emit_log(f"📅 Memproses bulan {bulan_nama} (index {bulan_index})...")

    home_dir = os.path.expanduser("~")
    key_path = "D:\\Code\\key.json"
    download_dir = os.path.join(home_dir, "Downloads")

    LOGIN_URL = "https://subsiditepatlpg.mypertamina.id/merchant-login"
    DOWNLOAD_URL = "https://subsiditepatlpg.mypertamina.id/merchant/app/logbook"
    LOGOUT_URL = "https://subsiditepatlpg.mypertamina.id/merchant/app/profile-merchant"

    # Setup Google Sheets
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key("1J-Hu6RgyJgj_5TI0YzMEhNPFpwy8RiYHvTImtszzPb8")
        sheet = spreadsheet.get_worksheet(sheet_index)
        rows = sheet.get_all_records(expected_headers=["username", "password", "key", "pangkalan"])
    except Exception as sheet_err:
        emit_log(f"❌ Gagal mengakses Google Sheets: {sheet_err}")
        return log

    driver = webdriver.Chrome()
    driver.maximize_window()
    wait = WebDriverWait(driver, 30)

    try:
        for idx, row in enumerate(rows, start=2):
            if control.get('stop_requested'):
                emit_log("🛑 Proses dihentikan oleh pengguna.")
                break

            required_fields = ["username", "password", "key", "pangkalan"]
            if any(not str(row.get(field)).strip() for field in required_fields):
                emit_log(f"⚠️ Melewati baris karena data tidak lengkap: {row}")
                continue

            try:
                driver.get(LOGIN_URL)
                time.sleep(2)

                username = str(row['username']).zfill(12)
                password = str(row['password']).zfill(6)
                key = row['key']
                nama = row['pangkalan']
                safe_nama = re.sub(r'[\\/*?:"<>|]', "_", nama)

                # Login
                wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Masukkan nomor ponsel atau 𝑒𝑚𝑎𝑖𝑙']"))).send_keys(username)
                wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Masukkan PIN Anda']"))).send_keys(password)
                wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Masuk']"))).click()
                time.sleep(3)

                # Deteksi gagal login
                attempt = 2
                for attempt in range(1, attempt + 1):
                    try:
                        gagal_login = driver.find_element(By.XPATH, "//h5[text()='Gagal Masuk Akun']")
                        if gagal_login:
                            emit_log(f"❌ Login gagal: PIN salah atau terkunci untuk {username}. Menunggu 2 menit...")
                            time.sleep(120)
                            if control.get('stop_requested'):
                                emit_log("🛑 Proses dihentikan saat tunggu karena login gagal.")
                                break
                            continue
                    except:
                        pass

                # Proses download dan unlock
                try:
                    driver.get(DOWNLOAD_URL)
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"button[data-testid='btnDownloadLb{bulan_index}']"))).click()
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='btnFetchDownload']"))).click()
                    time.sleep(1)
                    pyautogui.click(x=500, y=300)
                    time.sleep(1)
                    pyautogui.write(key)
                    pyautogui.press('enter')
                    time.sleep(1)
                    pyautogui.click(x=1268, y=170)
                    time.sleep(1)
                    pyautogui.write(f"{safe_nama}_{bulan_nama}")
                    pyautogui.press('enter')
                    time.sleep(1)

                    if control.get('stop_requested'):
                        emit_log("🛑 Proses dihentikan setelah download sebelum unlock.")
                        break

                    input_path = os.path.join(download_dir, f"{safe_nama}_{bulan_nama}.pdf")
                    output_path = os.path.join(download_dir, f"{safe_nama}_{bulan_nama}_unlocked.pdf")

                    checker.unlock_pdf(input_path, output_path, password=key)
                    try:
                        os.remove(input_path)
                    except FileNotFoundError:
                        emit_log(f"⚠️ File tidak ditemukan untuk dihapus: {input_path}")

                    emit_log(f"✅ Berhasil mengunduh dan meng-unlock {safe_nama}_{bulan_nama}.pdf")

                except Exception as e:
                    emit_log(f"❌ Gagal mengunduh untuk {safe_nama}_{bulan_nama}: {e}")
                    pass

                # Logout
                driver.get(LOGOUT_URL)
                if control.get('stop_requested'):
                    emit_log("🛑 Proses dihentikan sebelum logout.")
                    break
                wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Keluar Aplikasi']"))).click()
                wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Ya, Keluar Aplikasi']"))).click()

            except Exception as e:
                emit_log(f"❌ Terjadi error pada akun {row['username']}: {e}")
                continue

    finally:
        driver.quit()
        emit_log("🔚 Proses pengumpulan data selesai.")
        try:
            socketio.emit("collect_done")
        except:
            pass
        return log
