# 🛠️ Flask Debug Tools by syihamfaza

**Flask Debug Tools** adalah aplikasi berbasis web menggunakan Python + Flask yang dirancang untuk _automasi pelaporan data_ internal, khususnya untuk pelaporan LPG Subsidi berbasis Google Sheets & website Pertamina (MAP & SIMELON). Aplikasi ini juga dilengkapi dengan berbagai fitur pendukung untuk efisiensi operasional sehari-hari.

---

## 🚀 Fitur Utama

| Fitur         | Deskripsi                                                                 |
|---------------|---------------------------------------------------------------------------|
| 🔍 Cek Stok   | Ambil dan proses data stok LPG dari Google Sheets, lalu kirim ke MAP.     |
| ➔ Input MAP   | Otomasi pengisian data ke website MAP (Merchant Apps Pertamina).          |
| 📥 Penyaluran | Unduh data penyaluran dari SIMELON berdasarkan bulan & jenis.             |
| 📥 In/Out     | Unduh data IN/OUT agen dari SIMELON secara otomatis.                      |
| 🗜️ Kompres Foto | Kompresi ukuran file JPG/PNG langsung di browser.                        |
| ✍️ Edit PDF   | Tambahkan teks otomatis ke halaman tertentu di file PDF.                  |
| 🔓 Unlock PDF | Membuka file PDF yang diproteksi menggunakan password.                    |
| 📘 Baca Logbook | Ekstraksi data dari file logbook PDF (.zip) ke CSV.                      |
| 🖨️ Printer     | Upload dan cetak file PDF via printer default lokal.                     |

---

## ⚙️ Instalasi

```bash
# Clone repo
git clone https://github.com/syihamfaza/Flask.git
cd Flask

# Install dependencies
pip install -r requirements.txt

# Jalankan aplikasi
python app.py
