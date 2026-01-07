# Plant Waterer 🚿🌱

**Plant Waterer** adalah proyek open‑source untuk sistem penyiraman tanaman otomatis berbasis **ESP32** dengan dashboard realtime melalui browser.

Proyek ini menyediakan kontrol **manual** dan **otomatis**, serta monitoring status pompa dan sistem melalui antarmuka web.

---

## 🛠️ Fitur

- Mode **Automatic** & **Manual** watering
- Dashboard realtime via browser
- Kontrol pompa air
- Monitoring status sistem
- Berbasis Wi‑Fi (ESP32)

---

## 📦 Persyaratan

### 🔌 Hardware

| Komponen | Jumlah |
|--------|--------|
| ESP32 Dev Board | 1 |
| Soil Moisture Sensor | 1 |
| Relay Module | 1 |
| Water Pump | 1 |
| Kabel Jumper | Secukupnya |
| Breadboard (opsional) | 1 |

> Pastikan relay dan pompa menggunakan catu daya yang sesuai.

### 💻 Software

- Thonny IDE (disarankan)
- Arduino IDE (opsional)
- Browser (Chrome / Firefox)
- Kabel USB data

---

## 🚀 Instalasi & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/takathena/plant-waterer.git
cd plant-waterer
```

---

### 2️⃣ Persiapan ESP32

1. Install **Thonny IDE**
2. Pilih interpreter **MicroPython (ESP32)**
3. Hubungkan ESP32 ke PC menggunakan USB

---

### 3️⃣ Upload Program

1. Buka file `main.py`
2. Edit konfigurasi Wi‑Fi:

```python
SSID = "nama_wifi_anda"
PASSWORD = "password_wifi_anda"
```

3. Jalankan / upload file ke ESP32
4. Buka **Serial Monitor** dan catat IP Address ESP32

---

### 4️⃣ Akses Dashboard

1. Buka browser
2. Masukkan IP Address ESP32
3. Dashboard kontrol akan muncul

Demo UI:
👉 https://takathena.github.io/plant-waterer/

---

## 🔌 Konfigurasi Pin ESP32

### 📟 Soil Moisture Sensor

| Sensor | ESP32 |
|------|-------|
| VCC | 3V3 |
| GND | GND |
| A0 | GPIO 34 |

### 🔁 Relay & Pompa

| Relay | ESP32 |
|-----|-------|
| IN | GPIO 26 |
| VCC | 5V / 3V3 |
| GND | GND |

Pompa dihubungkan ke **NO & COM relay**.

> ⚠️ Gunakan power supply terpisah untuk pompa agar ESP32 aman.

---

## ⚙️ Cara Kerja Sistem

1. ESP32 membaca sensor kelembapan tanah
2. Data diproses dan ditampilkan di dashboard
3. Pompa aktif otomatis atau manual
4. Status sistem ditampilkan realtime

---

## 🧠 Pengembangan Lanjutan

- Tambah threshold kelembapan
- Integrasi MQTT / IoT Platform
- Tambah sensor suhu & kelembapan udara
- Logging data

---

## ⚠️ Catatan Penting

- Jangan memberi beban pompa langsung ke ESP32
- Gunakan relay / MOSFET
- Hindari ESP32 terkena air

---

## 🔗 Referensi

- Repository: https://github.com/takathena/plant-waterer
- Demo UI: https://takathena.github.io/plant-waterer/

---

## 📄 Lisensi

MIT License
