# 🎨 Background & Object Remover Studio (AI & Photoshop Tools)

Aplikasi web modern untuk menghapus background citra, mengekstrak latar belakang, melubangi objek manual, serta dilengkapi **Photoshop Classic Magic Eraser** berbasis toleransi warna.

Dibangun dengan arsitektur **FastAPI** di backend (ditenagai oleh model AI `rembg` dan akselerasi citra C++ OpenCV) serta frontend berbasis **Fabric.js** dengan antarmuka bertema gelap elegan (*Glassmorphism ala CasaOS*).

---

## ✨ Fitur Utama

1. **AI Background Remover (Auto)**
   - Menghapus latar belakang subjek utama secara otomatis menggunakan model segmentasi `silueta` ONNX yang sangat hemat RAM (~43MB) dan cepat.
2. **Ekstrak Latar Saja (Extract Background)**
   - Menghilangkan objek foreground dan menyisakan latar belakang dengan lubang subjek transparan.
3. **🪄 Photoshop Classic Magic Eraser (Color & Tolerance)**
   - Menghapus warna serupa menjadi transparan hanya dengan **satu kali klik**.
   - Slider **Toleransi Warna (Tolerance)**: Mengatur rentang kemiripan warna yang ingin dihapus (1 - 150).
   - Opsi **Contiguous (Area Tersambung)**:
     - *Aktif*: Hanya menghapus warna serupa yang bersambung (*Flood Fill*).
     - *Mati*: Menghapus semua warna serupa di seluruh area gambar.
   - Dilengkapi riwayat **Undo (`Ctrl + Z`)** dan tombol unduh langsung.
4. **🎯 Manual Shape Masking**
   - Menambahkan bentuk kotak (dengan sudut lengkung yang dapat diatur) atau lingkaran pada area tertentu untuk dilubangi menjadi transparan.
5. **Dukungan Penuh Drag & Drop**
   - Tarik dan lepas file gambar langsung dari desktop/file explorer ke dalam workspace.

---

## 🚀 Menjalankan dengan Docker (Rekomendasi Production)

Aplikasi ini sudah dikemas siap produksi (*production-ready*) dengan **Docker** dan **Docker Compose**. Image Docker otomatis mengunduh bobot model `silueta` saat proses build, sehingga kontainer bersifat **offline-ready** dan menyala seketika.

### 1. Build & Jalankan Kontainer

Pastikan Docker Engine sudah aktif, lalu jalankan:

```bash
docker compose up -d --build
```

### 2. Akses Aplikasi

Buka browser Anda dan akses:
```
http://localhost:8000/
```

### 3. Perintah Manajemen Docker

* **Melihat status kontainer & log:**
  ```bash
  docker compose logs -f
  ```
* **Mematikan kontainer:**
  ```bash
  docker compose down
  ```
* **Mengecek status kesehatan kontainer (Healthcheck):**
  ```bash
  docker compose ps
  ```

---

## 💻 Menjalankan Secara Lokal (Tanpa Docker)

### 1. Prasyarat
* Python 3.10, 3.11, atau 3.12
* Pip & Virtualenv

### 2. Langkah Instalasi

```bash
# 1. Clone repositori & masuk ke direktori
cd remove-bg

# 2. Buat dan aktifkan virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# 3. Install seluruh dependensi
pip install -r requirements.txt

# 4. Jalankan server Uvicorn
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Buka **`http://127.0.0.1:8000/`** di peramban Anda.

---

## 📡 Dokumentasi Endpoint REST API

Semua endpoint dapat diakses secara terpisah untuk integrasi dengan aplikasi lain:

### 1. Hapus Background AI
* **Endpoint:** `POST /remove-bg/`
* **Form Data:** `file` (File gambar: PNG, JPG, WebP)
* **Response:** File PNG transparan.

**Contoh cURL:**
```bash
curl -X POST "http://localhost:8000/remove-bg/" \
     -F "file=@foto.jpg" \
     -o "hasil_no_bg.png"
```

### 2. Photoshop Magic Color Eraser
* **Endpoint:** `POST /magic-color-eraser/`
* **Form Data:**
  * `image`: File gambar asli.
  * `x`: Titik koordinat horizontal (pixel integer).
  * `y`: Titik koordinat vertikal (pixel integer).
  * `tolerance`: Angka toleransi warna (1 - 255, default: 32).
  * `contiguous`: `true` untuk flood-fill, `false` untuk seluruh gambar.
* **Response:** File PNG transparan.

**Contoh cURL:**
```bash
curl -X POST "http://localhost:8000/magic-color-eraser/" \
     -F "image=@gambar.png" \
     -F "x=100" \
     -F "y=150" \
     -F "tolerance=32" \
     -F "contiguous=true" \
     -o "hasil_eraser.png"
```

### 3. Ekstrak Latar Belakang
* **Endpoint:** `POST /remove-object-auto/`
* **Form Data:** `file` (File gambar)
* **Response:** File PNG dengan subjek utama dibuat transparan.

---

## 🌐 Panduan Deployment Nyata (VPS / Cloud)

Jika Anda ingin men-*deploy* aplikasi ini ke VPS (seperti Ubuntu di DigitalOcean, AWS EC2, atau Linode):

### Contoh Konfigurasi Reverse Proxy Nginx

```nginx
server {
    server_name removebg.domainanda.com;

    client_max_body_size 25M; # Izinkan upload gambar hingga 25MB

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Pasang sertifikat SSL gratis dengan Certbot:
```bash
sudo certbot --nginx -d removebg.domainanda.com
```

---

## 👨‍💻 Kontributor & Lisensi

Didesain & Dikembangkan oleh:
* **Bergas Ardiansyah**
  * Portfolio: [bgasrdy.cloud](https://bgasrdy.cloud)
  * LinkedIn: [bgasrdy](https://www.linkedin.com/in/bgasrdy/)

Lisensi: [MIT](LICENSE)
