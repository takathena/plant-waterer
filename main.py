import network
import socket
import time
import machine
from machine import Pin, ADC
import json

# Konfigurasi WiFi
WIFI_SSID = "osu"
WIFI_PASSWORD = "11111111"

# Konfigurasi pin
RELAY_PINS = {
    "pompa1": 33,
    "pompa2": 26
}

# Pin TDS Meter (ADC)
TDS_PIN = 34  # Gunakan pin ADC yang sesuai (GPIO34, GPIO35, GPIO36, GPIO39)

# Pin HC-SR04a
HCSR04_TRIGGER_PIN = 12  # Sesuaikan dengan pin yang Anda gunakan
HCSR04_ECHO_PIN = 13    # Sesuaikan dengan pin yang Anda gunakan

# Konfigurasi Level Air
WATER_TANK_HEIGHT = 30  # Tinggi wadah (cm)
SENSOR_DEPTH = 3        # Sensor masuk ke dalam wadah (cm)
WATER_GAP = 2           # Gap aman sensor ke air (cm)
DISTANCE_EMPTY = 25     # Jarak saat air kosong (cm)
DISTANCE_FULL = 2       # Jarak saat air penuh / gap aman (cm)
MAX_WATER_HEIGHT = 25   # Tinggi air maksimal (cm)

# Level air minimum untuk menyalakan pompa (dalam persen)
WATER_LEVEL_MIN = 20    # Jika level air < 20%, pompa akan mati (proteksi)

# Konfigurasi TDS
TDS_THRESHOLD = 300  # Batas minimum TDS (ppm) - sesuaikan dengan kebutuhan
TDS_HYSTERESIS = 50  # Hysteresis untuk menghindari switching berulang
VREF = 3.3  # Tegangan referensi ADC
ADC_RESOLUTION = 4095  # Resolusi ADC 12-bit

# Inisialisasi TDS sensor
tds_sensor = ADC(Pin(TDS_PIN))
tds_sensor.atten(ADC.ATTN_11DB)  # Range 0-3.3V
tds_sensor.width(ADC.WIDTH_12BIT)  # Resolusi 12-bit

# Inisialisasi HC-SR04
trigger = Pin(HCSR04_TRIGGER_PIN, Pin.OUT)
echo = Pin(HCSR04_ECHO_PIN, Pin.IN)

# Inisialisasi relay
relays = {}
for name, pin in RELAY_PINS.items():
    relays[name] = Pin(pin, Pin.OUT)
    relays[name].value(1)  # Matikan relay saat start (aktif low)

# Status pompa
pump_status = {
    "pompa1": False,
    "pompa2": False
}

# Status otomatis
auto_mode = True
tds_value = 0
pump_auto_active = False

# Status level air
water_distance = 0
water_level_cm = 0
water_level_percent = 0
water_low_warning = False

# Koneksi WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("Menghubungkan ke WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
    
    if wlan.isconnected():
        print("\nTerhubung ke WiFi!")
        print("Alamat IP:", wlan.ifconfig()[0])
        return wlan.ifconfig()[0]
    else:
        print("\nGagal terhubung ke WiFi!")
        return None

# Setup Access Point
def setup_access_point():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="PompaController", password="12345678", authmode=3)
    print("Access Point aktif!")
    print("SSID: PompaController")
    print("Password: 12345678")
    print("Alamat IP:", ap.ifconfig()[0])
    return ap.ifconfig()[0]

# Baca HC-SR04 (Level Air)
def read_distance():
    global water_distance, water_level_cm, water_level_percent, water_low_warning
    
    try:
        # Kirim pulsa trigger
        trigger.value(0)
        time.sleep_us(2)
        trigger.value(1)
        time.sleep_us(10)
        trigger.value(0)
        
        # Tunggu echo
        timeout = 30000  # 30ms timeout
        start = time.ticks_us()
        
        # Tunggu echo HIGH
        while echo.value() == 0:
            if time.ticks_diff(time.ticks_us(), start) > timeout:
                return None
            start_time = time.ticks_us()
        
        # Tunggu echo LOW
        while echo.value() == 1:
            if time.ticks_diff(time.ticks_us(), start_time) > timeout:
                return None
            end_time = time.ticks_us()
        
        # Hitung jarak (dalam cm)
        duration = time.ticks_diff(end_time, start_time)
        distance = (duration * 0.0343) / 2  # Kecepatan suara 343 m/s
        
        # Filter nilai yang tidak masuk akal
        if distance < 1 or distance > 400:
            return None
        
        # Update jarak
        water_distance = round(distance, 1)
        
        # Hitung tinggi air
        # Jika jarak = 25cm (kosong), tinggi air = 0cm
        # Jika jarak = 2cm (penuh), tinggi air = 23cm
        if water_distance >= DISTANCE_EMPTY:
            water_level_cm = 0
        elif water_distance <= DISTANCE_FULL:
            water_level_cm = MAX_WATER_HEIGHT
        else:
            water_level_cm = DISTANCE_EMPTY - water_distance
        
        # Hitung persentase level air
        water_level_percent = int((water_level_cm / MAX_WATER_HEIGHT) * 100)
        
        # Cek warning level air rendah
        water_low_warning = water_level_percent < WATER_LEVEL_MIN
        
        return distance
        
    except Exception as e:
        print("Error HC-SR04:", str(e))
        return None

# Baca TDS Meter
def read_tds():
    # Rata-rata 10 pembacaan untuk stabilitas
    total = 0
    for _ in range(10):
        total += tds_sensor.read()
        time.sleep_ms(10)
    
    adc_value = total / 10
    
    # Konversi ADC ke tegangan
    voltage = (adc_value / ADC_RESOLUTION) * VREF
    
    # Konversi tegangan ke TDS (ppm)
    tds_ppm = voltage * 500  # Faktor konversi sederhana, sesuaikan dengan sensor
    
    return int(tds_ppm)

# Fungsi kontrol pompa
def set_pump(pump_name, state):
    global water_low_warning
    
    if pump_name in pump_status:
        # Proteksi: Jangan nyalakan pompa jika air terlalu rendah
        if state and water_low_warning:
            print("PERINGATAN: Air terlalu rendah! Pompa tidak dapat dinyalakan.")
            return False
        
        pump_status[pump_name] = state
        relays[pump_name].value(0 if state else 1)
        status_text = "HIDUP" if state else "MATI"
        print(pump_name + ": " + status_text)
        return state
    return None

# Kontrol otomatis berdasarkan TDS dan Level Air
def auto_control_pumps():
    global pump_auto_active, tds_value
    
    if not auto_mode:
        return
    
    # Baca sensor
    read_distance()
    tds_value = read_tds()
    
    # Cek level air rendah - matikan pompa untuk proteksi
    if water_low_warning and pump_auto_active:
        print("PROTEKSI: Level air rendah (" + str(water_level_percent) + "%) - Mematikan pompa...")
        set_pump("pompa1", False)
        set_pump("pompa2", False)
        pump_auto_active = False
        return
    
    # Logika dengan hysteresis untuk TDS
    if tds_value < TDS_THRESHOLD and not pump_auto_active and not water_low_warning:
        # TDS rendah dan air cukup, nyalakan pompa
        print("TDS rendah (" + str(tds_value) + " ppm) - Menyalakan pompa...")
        set_pump("pompa1", True)
        set_pump("pompa2", True)
        pump_auto_active = True
        
    elif tds_value >= (TDS_THRESHOLD + TDS_HYSTERESIS) and pump_auto_active:
        # TDS sudah cukup, matikan pompa
        threshold_upper = TDS_THRESHOLD + TDS_HYSTERESIS
        print("TDS cukup (" + str(tds_value) + " ppm) - Mematikan pompa...")
        set_pump("pompa1", False)
        set_pump("pompa2", False)
        pump_auto_active = False

# HTML Dashboard
def generate_html():
    status1 = "HIDUP" if pump_status["pompa1"] else "MATI"
    status2 = "HIDUP" if pump_status["pompa2"] else "MATI"
    status_color1 = "#28a745" if pump_status["pompa1"] else "#dc3545"
    status_color2 = "#28a745" if pump_status["pompa2"] else "#dc3545"
    
    auto_status = "AKTIF" if auto_mode else "NONAKTIF"
    auto_color = "#28a745" if auto_mode else "#6c757d"
    
    # TDS status
    tds_status_color = "#dc3545" if tds_value < TDS_THRESHOLD else "#28a745"
    tds_status_text = "RENDAH" if tds_value < TDS_THRESHOLD else "NORMAL"
    
    # Water level status
    if water_level_percent >= 70:
        water_status_color = "#28a745"
        water_status_text = "CUKUP"
    elif water_level_percent >= 30:
        water_status_color = "#ffc107"
        water_status_text = "SEDANG"
    else:
        water_status_color = "#dc3545"
        water_status_text = "RENDAH"
    
    # Waktu saat ini
    current_time = time.localtime()
    time_str = "{:02d}:{:02d}:{:02d}".format(current_time[3], current_time[4], current_time[5])
    date_str = "{}/{}/{}".format(current_time[2], current_time[1], current_time[0])
    
    auto_button_text = "NONAKTIFKAN" if auto_mode else "AKTIFKAN"
    auto_info = "Sistem otomatis mengendalikan pompa berdasarkan nilai TDS dan level air" if auto_mode else "Kontrol manual aktif - pompa tidak akan otomatis menyala"
    
    warning_text = "<p style='color: #ff9800; margin-top: 10px;'><em>&#9888; Mode AUTO aktif</em></p>" if auto_mode else ""
    
    water_warning = ""
    if water_low_warning:
        water_warning = "<div style='background-color: #dc3545; color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; font-weight: bold; text-align: center;'>&#9888; PERINGATAN: LEVEL AIR TERLALU RENDAH! POMPA DIMATIKAN UNTUK PROTEKSI</div>"
    
    threshold_upper = TDS_THRESHOLD + TDS_HYSTERESIS
    
    # Water level bar
    water_bar_color = water_status_color
    water_bar_width = str(water_level_percent) + "%"
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Dashboard Kontrol Pompa TDS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f0f0f0; }
        .container { max-width: 900px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .time-display { text-align: center; font-size: 1.2em; color: #666; margin-bottom: 20px; }
        
        .sensor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        
        @media (max-width: 768px) {
            .sensor-grid { grid-template-columns: 1fr; }
        }
        
        .tds-section { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 25px; 
            border-radius: 15px; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .water-section {
            background: linear-gradient(135deg, #56ccf2 0%, #2f80ed 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .sensor-value { 
            font-size: 2.5em; 
            font-weight: bold; 
            text-align: center; 
            margin: 15px 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .sensor-label { 
            text-align: center; 
            font-size: 1.2em; 
            opacity: 0.9;
        }
        .sensor-status { 
            text-align: center; 
            font-size: 1.3em; 
            font-weight: bold; 
            margin-top: 15px;
            padding: 10px;
            background-color: rgba(255,255,255,0.2);
            border-radius: 10px;
        }
        .threshold-info { 
            text-align: center; 
            margin-top: 10px; 
            font-size: 0.9em; 
            opacity: 0.8;
        }
        
        .water-bar-container {
            background-color: rgba(255,255,255,0.3);
            border-radius: 10px;
            height: 30px;
            margin: 15px 0;
            overflow: hidden;
        }
        .water-bar {
            height: 100%;
            background-color: rgba(255,255,255,0.9);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #2f80ed;
        }
        
        .water-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 15px;
        }
        .water-detail-item {
            background-color: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        .water-detail-label {
            font-size: 0.9em;
            opacity: 0.8;
        }
        .water-detail-value {
            font-size: 1.3em;
            font-weight: bold;
            margin-top: 5px;
        }
        
        .auto-control { 
            background-color: #f8f9fa; 
            padding: 20px; 
            border-radius: 10px; 
            margin-bottom: 20px; 
            text-align: center;
        }
        .auto-status { 
            font-size: 1.3em; 
            font-weight: bold; 
            margin: 10px 0;
        }
        
        .pump-container { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
        .pump-control { 
            flex: 1; 
            min-width: 280px; 
            padding: 20px; 
            background-color: #f8f9fa; 
            border-radius: 10px; 
            text-align: center; 
        }
        .status { 
            font-size: 1.5em; 
            font-weight: bold; 
            margin: 15px 0; 
            padding: 10px; 
            border-radius: 5px; 
            background-color: #e9ecef; 
        }
        .button { 
            padding: 12px 24px; 
            font-size: 1.1em; 
            margin: 5px; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            transition: all 0.3s;
        }
        .button:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .on { background-color: #28a745; color: white; }
        .off { background-color: #dc3545; color: white; }
        .auto-toggle { background-color: #007bff; color: white; font-size: 1.2em; padding: 15px 30px; }
        .auto-refresh { text-align: center; margin-top: 20px; color: #999; font-size: 0.9em; }
        
        .info-box { 
            background-color: #e7f3ff; 
            border-left: 4px solid #007bff; 
            padding: 15px; 
            margin-top: 20px; 
            border-radius: 5px;
        }
        .info-box h3 { margin-top: 0; color: #007bff; }
        .info-box ul { margin: 10px 0; padding-left: 20px; }
    </style>
    <script>
        var waterLowWarning = """ + ("true" if water_low_warning else "false") + """;
        
        function setPump(pumpName, state) {
            if (waterLowWarning && state) {
                alert('PERINGATAN: Level air terlalu rendah! Pompa tidak dapat dinyalakan untuk melindungi sistem.');
                return;
            }
            
            fetch('/set/' + pumpName + '/' + (state ? '1' : '0'))
                .then(response => response.text())
                .then(data => {
                    setTimeout(() => { location.reload(); }, 100);
                });
        }
        
        function toggleAutoMode() {
            fetch('/toggle_auto')
                .then(response => response.text())
                .then(data => {
                    setTimeout(() => { location.reload(); }, 100);
                });
        }
        
        setTimeout(() => {
            location.reload();
        }, 2000);
    </script>
</head>
<body>
    <div class="container">
        <h1>&#128167; Dashboard Kontrol Pompa TDS</h1>
        
        <div class="time-display">
            <strong>""" + date_str + " " + time_str + """</strong>
        </div>
        
        """ + water_warning + """
        
        <div class="sensor-grid">
            <div class="tds-section">
                <div class="sensor-label">NILAI TDS</div>
                <div class="sensor-value">""" + str(tds_value) + """ <span style="font-size: 0.5em;">ppm</span></div>
                <div class="sensor-status" style="color: """ + tds_status_color + """;">
                    """ + tds_status_text + """
                </div>
                <div class="threshold-info">
                    Min: """ + str(TDS_THRESHOLD) + """ ppm | Max: """ + str(threshold_upper) + """ ppm
                </div>
            </div>
            
            <div class="water-section">
                <div class="sensor-label">LEVEL AIR</div>
                <div class="sensor-value">""" + str(water_level_percent) + """ <span style="font-size: 0.5em;">%</span></div>
                
                <div class="water-bar-container">
                    <div class="water-bar" style="width: """ + water_bar_width + """; background-color: """ + water_bar_color + """;">
                        """ + str(water_level_percent) + """%
                    </div>
                </div>
                
                <div class="sensor-status" style="color: """ + water_status_color + """;">
                    """ + water_status_text + """
                </div>
                
                <div class="water-details">
                    <div class="water-detail-item">
                        <div class="water-detail-label">Tinggi Air</div>
                        <div class="water-detail-value">""" + str(water_level_cm) + """ cm</div>
                    </div>
                    <div class="water-detail-item">
                        <div class="water-detail-label">Jarak Sensor</div>
                        <div class="water-detail-value">""" + str(water_distance) + """ cm</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="auto-control">
            <h2>MODE OTOMATIS</h2>
            <div class="auto-status" style="color: """ + auto_color + """;">""" + auto_status + """</div>
            <button class="button auto-toggle" onclick="toggleAutoMode()">
                """ + auto_button_text + """ MODE AUTO
            </button>
            <p style="margin-top: 15px; color: #666;">
                """ + auto_info + """
            </p>
        </div>
        
        <div class="pump-container">
            <div class="pump-control">
                <h2>POMPA 1</h2>
                <div class="status" style="color: """ + status_color1 + """;">""" + status1 + """</div>
                <button class="button on" onclick="setPump('pompa1', true)" """ + ("disabled" if water_low_warning else "") + """>HIDUPKAN</button>
                <button class="button off" onclick="setPump('pompa1', false)">MATIKAN</button>
                """ + warning_text + """
            </div>
            
            <div class="pump-control">
                <h2>POMPA 2</h2>
                <div class="status" style="color: """ + status_color2 + """;">""" + status2 + """</div>
                <button class="button on" onclick="setPump('pompa2', true)" """ + ("disabled" if water_low_warning else "") + """>HIDUPKAN</button>
                <button class="button off" onclick="setPump('pompa2', false)">MATIKAN</button>
                """ + warning_text + """
            </div>
        </div>
        
        <div class="info-box">
            <h3>&#128161; Informasi Sistem</h3>
            <ul>
                <li><strong>Mode Otomatis:</strong> Pompa menyala otomatis saat TDS &lt; """ + str(TDS_THRESHOLD) + """ ppm dan level air cukup</li>
                <li><strong>Proteksi Level Air:</strong> Pompa otomatis mati jika level air &lt; """ + str(WATER_LEVEL_MIN) + """%</li>
                <li><strong>Hysteresis TDS:</strong> Pompa mati saat TDS &gt;= """ + str(threshold_upper) + """ ppm</li>
                <li><strong>Tinggi Wadah:</strong> """ + str(WATER_TANK_HEIGHT) + """ cm (Max air: """ + str(MAX_WATER_HEIGHT) + """ cm)</li>
                <li><strong>HC-SR04:</strong> Trigger=GPIO """ + str(HCSR04_TRIGGER_PIN) + """, Echo=GPIO """ + str(HCSR04_ECHO_PIN) + """</li>
                <li><strong>TDS Sensor:</strong> GPIO """ + str(TDS_PIN) + """ (ADC)</li>
                <li><strong>Relay:</strong> Pompa 1=GPIO 16, Pompa 2=GPIO 17</li>
            </ul>
        </div>
        
        <div class="auto-refresh">
            &#128472; Halaman refresh otomatis setiap 2 detik
        </div>
    </div>
</body>
</html>"""
    return html

# Web server
def run_web_server(ip_address):
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    
    print("Server berjalan di http://" + ip_address)
    
    # Timeout socket 1 detik
    s.settimeout(1.0)
    
    while True:
        try:
            # Cek TDS dan kontrol otomatis
            auto_control_pumps()
            
            try:
                cl, addr = s.accept()
                print("Koneksi dari: " + str(addr))
                
                request = cl.recv(1024).decode()
                
                if "GET / " in request or "GET /index" in request or "GET / HTTP" in request:
                    response = generate_html()
                    cl.send('HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n')
                    cl.send(response)
                    
                elif "GET /set/" in request:
                    parts = request.split()
                    if len(parts) > 0:
                        url = parts[1]
                        url_parts = url.split('/')
                        if len(url_parts) >= 4:
                            pump_name = url_parts[2]
                            state = int(url_parts[3])
                            new_state = set_pump(pump_name, bool(state))
                            response_json = json.dumps({"pump": pump_name, "status": new_state})
                            cl.send('HTTP/1.1 200 OK\r\nContent-type: application/json\r\n\r\n')
                            cl.send(response_json)
                
                elif "GET /toggle_auto" in request:
                    global auto_mode
                    auto_mode = not auto_mode
                    mode_text = "AKTIF" if auto_mode else "NONAKTIF"
                    print("Mode Auto: " + mode_text)
                    response_json = json.dumps({"auto_mode": auto_mode})
                    cl.send('HTTP/1.1 200 OK\r\nContent-type: application/json\r\n\r\n')
                    cl.send(response_json)
                    
                elif "GET /status" in request:
                    response_json = json.dumps({
                        "tds": tds_value,
                        "threshold": TDS_THRESHOLD,
                        "auto_mode": auto_mode,
                        "pompa1": pump_status["pompa1"],
                        "pompa2": pump_status["pompa2"],
                        "water_distance": water_distance,
                        "water_level_cm": water_level_cm,
                        "water_level_percent": water_level_percent,
                        "water_low_warning": water_low_warning
                    })
                    cl.send('HTTP/1.1 200 OK\r\nContent-type: application/json\r\n\r\n')
                    cl.send(response_json)
                    
                else:
                    cl.send('HTTP/1.1 404 Not Found\r\n\r\n')
                    
            except socket.timeout:
                continue
            except OSError as e:
                if e.errno == 110:
                    continue
            finally:
                try:
                    cl.close()
                except:
                    pass
                    
        except KeyboardInterrupt:
            print("\nServer dihentikan")
            break
        except Exception as e:
            print("Error: " + str(e))
            time.sleep(1)

# Setup time
def setup_time():
    try:
        import ntptime
        ntptime.host = "pool.ntp.org"
        ntptime.settime()
        print("Waktu disinkronisasi")
    except:
        print("Gagal sinkronisasi waktu")

# Main program
def main():
    print("=== SISTEM KONTROL POMPA TDS + LEVEL AIR ===")
    print("Pin " + str(TDS_PIN) + ": TDS Sensor (ADC)")
    print("Pin " + str(HCSR04_TRIGGER_PIN) + ": HC-SR04 Trigger")
    print("Pin " + str(HCSR04_ECHO_PIN) + ": HC-SR04 Echo")
    print("Pin 16: Pompa 1 (Relay)")
    print("Pin 17: Pompa 2 (Relay)")
    print("Batas TDS: " + str(TDS_THRESHOLD) + " ppm")
    print("Level Air Minimum: " + str(WATER_LEVEL_MIN) + "%")
    
    setup_time()
    
    ip_address = connect_wifi()
    
    if ip_address is None:
        print("\nMenggunakan mode Access Point...")
        ip_address = setup_access_point()
    
    try:
        run_web_server(ip_address)
    except KeyboardInterrupt:
        print("\nProgram dihentikan")
    finally:
        print("Mematikan semua pompa...")
        for pump_name in pump_status:
            set_pump(pump_name, False)

# Jalankan program
if __name__ == "__main__":
    main()

