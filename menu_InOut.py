import time
import checker
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from pathlib import Path 

def run_inout(username, password, tanggal, bulan_label, download_dir, socketio=None, sid=None):
    download_dir = str(Path.home() / "Downloads")
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    driver.get("https://apps.pertamina.com/simelon_v2_r4/login")
    wait.until(EC.presence_of_element_located((By.ID, "UserName"))).send_keys(username)
    wait.until(EC.presence_of_element_located((By.ID, "Password"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Login']"))).click()
    if socketio: socketio.emit('inout_log', f"✅ login {username}", to=sid)

    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[span[contains(text(), 'IN / OUT Agen')]]"))).click()
    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/inout-agen/index')]"))).click()

    datepicker = wait.until(EC.element_to_be_clickable((By.ID, "date")))
    datepicker.clear()
    datepicker.send_keys(tanggal)
    datepicker.send_keys(Keys.ENTER)
    wait.until(EC.invisibility_of_element_located((By.ID, "loading-spinner")))
    time.sleep(2)

    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Download Sebagai')]"))).click()
    wait.until(EC.element_to_be_clickable((By.ID, "linkpdf"))).click()
    time.sleep(5)
    checker.rename_latest_file(".pdf", f"{bulan_label}_INOUT.pdf")
    if socketio: socketio.emit('inout_log', f"✅ berhasil unduh {bulan_label}.pdf", to=sid)

    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Download Sebagai')]"))).click()
    wait.until(EC.element_to_be_clickable((By.ID, "linkexcel"))).click()
    time.sleep(5)
    checker.rename_latest_file(".xlsx", f"{bulan_label}_INOUT.xlsx")
    if socketio: socketio.emit('inout_log', f"✅ berhasil unduh {bulan_label}.xlsx", to=sid)

    driver.quit()
