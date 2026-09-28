# 📌 Pinterest Downloader Telegram Bot

Bot Telegram untuk mengunduh gambar dan video dari Pinterest secara langsung melalui obrolan Telegram. Dibangun di atas library `pinterest-dl` dan siap dijalankan dengan Docker & Docker Compose.

---

## ✨ Fitur Utama

- 📥 **Unduh Langsung Single Pin**: Kirim link pin Pinterest (`https://pin.it/...` atau `https://pinterest.com/pin/...`), bot otomatis mengunduh gambar resolusi penuh atau video `.mp4`.
- 🎥 **Support Video HLS / Stream**: Otomatis menggabungkan dan meremux video stream menggunakan `ffmpeg` ke format MP4.
- 🔍 **Pencarian Pin**: Gunakan `/search <kata kunci> [jumlah]` untuk mencari dan mengunduh pin langsung dari Telegram.
- 📦 **Unduh Board / Album**: Gunakan `/scrape <link_board> [jumlah]` untuk mengunduh beberapa item sekaligus (dikirim dalam bentuk Telegram Media Group/Album).
- 🧹 **Auto Cleanup**: File temporary di server/container langsung dihapus setelah berhasil terkirim ke pengguna, menghemat ruang penyimpanan.
- 🐳 **Docker Ready**: Terisolasi dan mudah di-deploy dengan Docker & Docker Compose.

---

## 🚀 Panduan Setup & Menjalankan Bot

### 1. Dapatkan Bot Token dari Telegram
1. Buka aplikasi Telegram dan cari bot [@BotFather](https://t.me/BotFather).
2. Kirim perintah `/newbot` dan ikuti petunjuknya (masukkan nama dan username bot).
3. Salin token API yang diberikan (contoh: `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### 2. Konfigurasi File `.env`
Di dalam folder `pinterest-dl-main`, buat file `.env` dari template `.env.example`:

```bash
cd pinterest-dl-main
cp .env.example .env
```

Buka file `.env` dan masukkan token bot Anda:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
DEFAULT_NUM=5
MAX_NUM=10
LOG_LEVEL=INFO
```

---

### 3. Jalankan Menggunakan Docker

Pastikan Docker & Docker Compose sudah terpasang di sistem Anda.

#### Menjalankan Bot (Background):
```bash
# Dari dalam folder pinterest-dl-main:
docker compose up -d --build
```
*(Atau Anda juga dapat menjalankan `docker compose up -d --build` dari root folder project).*

#### Melihat Log Aktivitas Bot:
```bash
docker compose logs -f
```

#### Menghentikan Bot:
```bash
docker compose down
```

#### Memulai Ulang (Restart) Bot:
```bash
docker compose restart
```

---

## 📱 Cara Penggunaan Bot di Telegram

| Perintah / Aksi | Contoh | Keterangan |
|---|---|---|
| **Kirim Link Pin** | `https://pin.it/abcd123` | Bot akan mengunduh gambar atau video MP4 dari pin tersebut. |
| `/search` atau `/cari` | `/search aesthetic landscape 4` | Mencari pin sesuai kata kunci dan mengirim hasilnya. |
| `/scrape` | `/scrape https://pinterest.com/user/board/ 5` | Mengunduh kumpulan pin dari board tertentu. |
| `/start` | `/start` | Menampilkan pesan sambutan dan panduan singkat. |
| `/help` | `/help` | Menampilkan bantuan lengkap. |

---

## 🔒 Mengunduh Pin / Board Privat (Opsional)

Jika Anda ingin mengunduh pin atau board privat milik akun Anda:
1. Export cookies akun Pinterest Anda ke file `cookies.json` menggunakan extension browser (seperti *Cookie-Editor* atau `pinterest-dl login`).
2. Letakkan file `cookies.json` di dalam folder `pinterest-dl-main`.
3. Buka `docker-compose.yml`, lalu uncomment bagian volume `cookies.json`:
   ```yaml
   volumes:
     - ./cookies.json:/app/cookies.json:ro
   ```
4. Jalankan ulang container: `docker compose up -d`.
