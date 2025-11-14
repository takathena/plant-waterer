import network
import socket
from machine import Pin, ADC
from time import sleep

# === KONFIGURASI WIFI ===
SSID = "Lab Telkom"
PASSWORD = ""

# === INISIALISASI KOMPONEN ===
soil = ADC(Pin(34))
soil.atten(ADC.ATTN_11DB)
relay = Pin(26, Pin.OUT)
relay.value(1)  # relay off awal (aktif LOW)

# === NILAI KALIBRASI SENSOR ===
SOIL_DRY = 3500
SOIL_WET = 1500

# === VARIABEL MODE ===
mode_auto = True
manual_state = 1

# === FUNGSI BACA SENSOR ===
def read_soil_percent():
    val = soil.read()
    percent = int((SOIL_DRY - val) * 100 / (SOIL_DRY - SOIL_WET))
    percent = max(0, min(100, percent))
    return percent, val

# === KONEKSI WIFI ===
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Menghubungkan ke WiFi...", end="")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            print(".", end="")
            sleep(0.5)
    print("\nTerhubung:", wlan.ifconfig())
    return wlan

# === HALAMAN WEB DENGAN WAKTU & TANGGAL REALTIME ===
def web_page(percent, mode_auto):
    pump_status = "MENYALA" if relay.value() == 0 else "MATI"
    mode_status = "Otomatis" if mode_auto else "Manual"

    html = f"""
    <html>
    <head>
        <title>Penyiram Otomatis</title>
        <meta http-equiv="refresh" content="2">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.cdnfonts.com/css/rubik-2" rel="stylesheet">
        <style>
        body{{font-family:'Rubik', Arial, sans-serif;text-align:center;margin-top:40px; font-weight: bold;}}
        button{{border: 1px dashed gray;border-radius: 0; padding:10px 20px;margin:5px;font-size:16px;}}
        .on , .off {{color:black;border:1px dashed grey;}}
        .on:hover, .off:hover {{background-color: #9AA4BA; border: 1px dashed gray; color:white;}}
        #waktu{{font-size:18px; margin-bottom:10px;}}
        </style>

        <script>
        function updateTime() {{
            const now = new Date();
            const date = now.toLocaleDateString('id-ID');
            const time = now.toLocaleTimeString('id-ID');
            document.getElementById("waktu").innerHTML = date + " - " + time;
        }}
        setInterval(updateTime, 1000);
        </script>

    </head>
    <body onload="updateTime()">
        <h2>Penyiram Tanaman Otomatis</h2>

        <p><b id="waktu"></b></p>

        <p>Kelembapan Tanah: <b>{percent}%</b></p>
        <p>Status Pompa: <b>{pump_status}</b></p>
        <p>Mode: <b>{mode_status}</b></p>

        <form>
            <button name="mode" value="auto">Mode Otomatis</button>
            <button name="mode" value="manual">Mode Manual</button><br><br>

            <button name="pump" value="on" class="on">Pompa ON</button>
            <button name="pump" value="off" class="off">Pompa OFF</button>
        </form>
    </body>
    </html>
    """
    return html

# === MULAI SERVER ===
wlan = connect_wifi()
addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
s.settimeout(0.5)
print("Server siap di http://%s" % wlan.ifconfig()[0])

# === LOOP UTAMA ===
while True:
    # Baca sensor
    percent, raw = read_soil_percent()
    print("Soil:", percent, "% (ADC:", raw, ")")

    # Kontrol otomatis
    if mode_auto:
        if percent < 40:
            relay.value(0)
        else:
            relay.value(1)
    else:
        relay.value(manual_state)

    # Layani request web
    try:
        conn, addr = s.accept()
        request = str(conn.recv(1024))
        print("Web:", addr)

        # MODE
        if "mode=auto" in request:
            mode_auto = True
        elif "mode=manual" in request:
            mode_auto = False

        # MANUAL CONTROL
        elif "pump=on" in request:
            manual_state = 0
            relay.value(0)
        elif "pump=off" in request:
            manual_state = 1
            relay.value(1)

        # KIRIM HALAMAN WEB
        html = web_page(percent, mode_auto)
        conn.send("HTTP/1.1 200 OK\nContent-Type: text/html\nConnection: close\n\n")
        conn.sendall(html)
        conn.close()

    except OSError:
        pass  # timeout agar tidak menggantung

    sleep(1)

