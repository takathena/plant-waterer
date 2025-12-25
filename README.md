<div align="center">
  
# 🌿 Plant Waterer

**Automated Plant Watering & Monitoring System**  
📡 ESP32 + Soil Moisture Sensor + Web Dashboard

![ESP32](https://img.shields.io/badge/ESP32-IoT-blue)
![Python](https://img.shields.io/badge/Python-MicroPython-yellow)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)

</div>

---

## 🚀 Project Overview

**Plant Waterer** adalah sebuah proyek IoT yang dibuat sebagai tugas akhir untuk mengotomasi penyiraman tanaman.  
Perangkat ini mampu memantau kelembapan tanah secara real-time dan menyiram tanaman secara otomatis — lengkap dengan dashboard visual yang bisa diakses lewat browser setelah terhubung ke Wi-Fi.

---

## 🌟 Features

✨ **Automatic & Manual Watering Mode**  
📊 Real-time soil moisture chart (200-500ms update)  
📱 Cross-platform dashboard interface  
🧠 Easy-to-use firmware on ESP32  
📡 Accessible via local network IP  
🔧 Customizable design & open-source codebase 

---

## 📋 Requirements

### 🔌 Hardware
- ESP32 microcontroller  
- Soil moisture sensor  
- Relay module  
- DC water pump  
- Jumper cables  
- Power supply

### 💻 Software
- Thonny (for Python / ESP32) *or* Arduino IDE  
- Browser to access dashboard UI

---

## 🛠 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/takathena/plant-waterer
2. Connect & flash firmware 
    - Buka Thonny atau Arduino IDE  
    - Hubungkan ESP32
    - Upload main.py (Python/ESP32) atau sesuai firmware Anda
3. Configure Wi-Fi  
    Di dalam kode, sesuaikan:
    ```
    SSID = "your-wifi"
    PASSWORD = "your-password"
    ```
4. Run & Access Dashboard
    - Jalankan kode
    - Catat IP yang muncul di konsol
    - Buka IP tersebut di browser untuk melihat dashboard

## 📊 Dashboard

Setelah ESP32 berhasil terhubung ke Wi-Fi, perangkat akan menampilkan alamat IP.
Buka alamat tersebut di browser untuk mengakses UI yang menunjukkan data kelembapan tanah secara real-time dan opsi watering otomatis/manual.

## 📁 Repository Structure

```
.esp32
├── boot.py
└── main.py
```

## 🧪 Troubleshooting

🔹 ESP32 tidak muncul di IDE?  
🔹Periksa port USB  
🔹Install driver board yang sesuai  
🔹Dashboard tidak muncul?  
🔹Pastikan ESP32 tersambung ke Wi-Fi yang sama dengan perangkat kamu  
🔹Buka alamat IP yang muncul pada serial monitor

## 🤝 Contributing

Contributions are welcome!  
Please read [CONTRIBUTING.md](https://github.com/takathena/plant-waterer/blob/CONTRIBUTING.md/) before submitting changes.

## 📜 License

This project is licensed under the This site was built using [LICENSE](https://github.com/takathena/plant-waterer/blob/simple/LICENSE). License.

© 2025 Takathena