import network
import socket
import time
import machine
from machine import Pin
import ntptime
import json
import gc

# Konfigurasi WiFi
WIFI_SSID = "iot"
WIFI_PASSWORD = "Iot@12345678"

# Konfigurasi pin
RELAY_PINS = {
    "pompa1": 16,
    "pompa2": 17
}

# Inisialisasi relay
relays = {}
for name, pin in RELAY_PINS.items():
    relays[name] = Pin(pin, Pin.OUT)
    relays[name].value(1)

# Status pompa
pump_status = {
    "pompa1": False,
    "pompa2": False
}

# Default jadwal (kosong)
pump_schedule = {
    "pompa1": [],
    "pompa2": []
}

# Load jadwal dari file
def load_schedule():
    global pump_schedule
    try:
        with open('schedule.json', 'r') as f:
            loaded = json.load(f)
            # Pastikan formatnya benar
            if "pompa1" in loaded and "pompa2" in loaded:
                pump_schedule = loaded
                print("Jadwal loaded")
                return True
    except:
        pass
    return False

# Save jadwal ke file
def save_schedule():
    try:
        with open('schedule.json', 'w') as f:
            json.dump(pump_schedule, f)
        print("Jadwal saved")
        return True
    except:
        print("Gagal save jadwal")
        return False

# Timer aktif pompa
active_timers = {
    "pompa1": {"active": False, "end_time": 0},
    "pompa2": {"active": False, "end_time": 0}
}

# Status waktu
time_synced = False
last_sync = 0
SYNC_INTERVAL = 3600

# Variabel untuk non-blocking delay
last_check = 0
CHECK_INTERVAL = 0.5

# Nama hari dalam seminggu
DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
DAY_NAMES_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Koneksi WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("Connecting WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        timeout = 0
        while not wlan.isconnected() and timeout < 20:
            time.sleep(0.5)
            timeout += 1
    
    if wlan.isconnected():
        print("IP:", wlan.ifconfig()[0])
        return wlan.ifconfig()[0]
    return None

# Setup AP
def setup_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid="PompaAP", password="12345678", authmode=3)
    print("AP IP:", ap.ifconfig()[0])
    return ap.ifconfig()[0]

# Sync waktu
def sync_time():
    global time_synced, last_sync
    
    if not network.WLAN(network.STA_IF).isconnected():
        return False
    
    try:
        ntptime.host = "pool.ntp.org"
        ntptime.settime()
        
        t = time.localtime()
        new_hour = t[3] + 7
        if new_hour >= 24:
            new_hour -= 24
        
        machine.RTC().datetime((t[0], t[1], t[2], t[6], new_hour, t[4], t[5], 0))
        
        time_synced = True
        last_sync = time.time()
        print("Time synced")
        return True
    except:
        return False

# Kontrol pompa
def set_pump(pump, state):
    if pump in pump_status:
        pump_status[pump] = state
        relays[pump].value(0 if state else 1)
        
        if not state:
            active_timers[pump] = {"active": False, "end_time": 0}
        
        return state
    return None

# Timer pompa
def start_timer(pump, duration):
    set_pump(pump, True)
    active_timers[pump] = {
        "active": True,
        "end_time": time.time() + duration
    }

# Cek jadwal
def check_schedule():
    if not time_synced:
        return
    
    now = time.localtime()
    day = now[6]
    hour = now[3]
    minute = now[4]
    
    for pump, schedules in pump_schedule.items():
        for sched in schedules:
            if (sched["day"] == day and 
                sched["hour"] == hour and 
                sched["minute"] == minute):
                
                today = time.localtime()
                today_date = (today[0], today[1], today[2])
                
                if sched.get("last_executed") != today_date:
                    start_timer(pump, sched["duration"])
                    sched["last_executed"] = today_date
                    print(f"Jadwal dieksekusi: {pump} hari {DAYS[day]} {hour:02d}:{minute:02d}")

# Cek timer
def check_timers():
    now = time.time()
    
    for pump, timer in active_timers.items():
        if timer["active"] and now >= timer["end_time"]:
            set_pump(pump, False)
            print(f"Timer selesai: {pump}")

# Cek sync
def check_sync():
    global time_synced
    if not time_synced or (time.time() - last_sync) > SYNC_INTERVAL:
        sync_time()

# Ambil data status untuk JSON
def get_status_data():
    t = time.localtime()
    time_str = f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
    day_str = DAYS[t[6]]
    
    timer1 = 0
    timer2 = 0
    
    if active_timers["pompa1"]["active"]:
        timer1 = max(0, int(active_timers["pompa1"]["end_time"] - time.time()))
    
    if active_timers["pompa2"]["active"]:
        timer2 = max(0, int(active_timers["pompa2"]["end_time"] - time.time()))
    
    return {
        "pompa1": {
            "status": pump_status["pompa1"],
            "timer": timer1
        },
        "pompa2": {
            "status": pump_status["pompa2"],
            "timer": timer2
        },
        "time": time_str,
        "day": day_str,
        "sync": time_synced
    }

# Ambil data jadwal
def get_schedule_data():
    schedule_list = []
    
    for pump, schedules in pump_schedule.items():
        for idx, sched in enumerate(schedules):
            day_name = DAYS[sched["day"]]
            hour_str = f"{sched['hour']:02d}"
            minute_str = f"{sched['minute']:02d}"
            
            # Konversi durasi ke menit dan detik
            total_seconds = sched["duration"]
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            schedule_list.append({
                "id": f"{pump}_{idx}",
                "pump": pump,
                "day": sched["day"],
                "day_name": day_name,
                "hour": sched["hour"],
                "minute": sched["minute"],
                "hour_str": hour_str,
                "minute_str": minute_str,
                "duration": total_seconds,
                "duration_hours": hours,
                "duration_minutes": minutes,
                "duration_seconds": seconds
            })
    
    # Sort by day and time
    schedule_list.sort(key=lambda x: (x["day"], x["hour"], x["minute"]))
    
    return schedule_list

# Parsing URL
def parse_query_string(query_string):
    params = {}
    if query_string:
        pairs = query_string.split('&')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
    return params

# Handler untuk API
def handle_api(client, path, params):
    response = {"success": False}
    
    try:
        if path == "/api/status":
            response = get_status_data()
            response["success"] = True
            
        elif path == "/api/schedule":
            response = {
                "success": True,
                "schedules": get_schedule_data()
            }
            
        elif path == "/api/add_schedule":
            pump = params.get("pump", "")
            day = int(params.get("day", 0))
            hour = int(params.get("hour", 0))
            minute = int(params.get("minute", 0))
            
            # Parse durasi
            hours = int(params.get("duration_hours", 0))
            minutes = int(params.get("duration_minutes", 0))
            seconds = int(params.get("duration_seconds", 0))
            duration = hours * 3600 + minutes * 60 + seconds
            
            if pump in ["pompa1", "pompa2"] and 0 <= day <= 6 and 0 <= hour <= 23 and 0 <= minute <= 59 and duration > 0:
                pump_schedule[pump].append({
                    "day": day,
                    "hour": hour,
                    "minute": minute,
                    "duration": duration
                })
                save_schedule()
                response = {
                    "success": True,
                    "message": "Jadwal ditambahkan"
                }
            else:
                response["message"] = "Data tidak valid"
                
        elif path == "/api/delete_schedule":
            schedule_id = params.get("id", "")
            if "_" in schedule_id:
                pump, idx = schedule_id.split("_")
                idx = int(idx)
                if pump in pump_schedule and 0 <= idx < len(pump_schedule[pump]):
                    del pump_schedule[pump][idx]
                    save_schedule()
                    response = {
                        "success": True,
                        "message": "Jadwal dihapus"
                    }
                else:
                    response["message"] = "Jadwal tidak ditemukan"
                    
        elif path == "/api/clear_schedule":
            pump = params.get("pump", "")
            if pump == "all":
                pump_schedule["pompa1"] = []
                pump_schedule["pompa2"] = []
            elif pump in pump_schedule:
                pump_schedule[pump] = []
            save_schedule()
            response = {
                "success": True,
                "message": "Jadwal dikosongkan"
            }
            
    except Exception as e:
        response["message"] = f"Error: {str(e)}"
    
    return json.dumps(response)

# HTML Dashboard
def get_dashboard():
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kontrol Pompa Otomatis</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .status-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        
        .time-display {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }
        
        .sync-status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
        }
        
        .sync-on {
            background: #d4edda;
            color: #155724;
        }
        
        .sync-off {
            background: #f8d7da;
            color: #721c24;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            padding: 30px;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            border: 1px solid #e9ecef;
        }
        
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #4facfe;
        }
        
        .pump-control {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .pump-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            transition: all 0.3s ease;
        }
        
        .pump-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .pump-info h3 {
            color: #333;
            margin-bottom: 5px;
        }
        
        .pump-status {
            font-size: 1.1em;
            font-weight: bold;
        }
        
        .status-on {
            color: #28a745;
        }
        
        .status-off {
            color: #dc3545;
        }
        
        .timer-display {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
        
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 1em;
            transition: all 0.3s ease;
        }
        
        .btn-toggle {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-width: 120px;
        }
        
        .btn-toggle:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-on {
            background: linear-gradient(135deg, #42e695 0%, #3bb2b8 100%);
            color: white;
        }
        
        .btn-off {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
        }
        
        .btn-small {
            padding: 8px 15px;
            font-size: 0.9em;
        }
        
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        
        .btn-danger:hover {
            background: #c82333;
        }
        
        .schedule-form {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }
        
        .form-group {
            display: flex;
            flex-direction: column;
        }
        
        .form-group label {
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }
        
        select, input {
            padding: 12px;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }
        
        select:focus, input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .duration-inputs {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }
        
        .duration-inputs input {
            text-align: center;
        }
        
        .schedule-list {
            max-height: 400px;
            overflow-y: auto;
            margin-top: 20px;
        }
        
        .schedule-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 10px;
            border-left: 5px solid #4facfe;
        }
        
        .schedule-info {
            flex: 1;
        }
        
        .schedule-time {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        
        .schedule-details {
            font-size: 0.9em;
            color: #666;
        }
        
        .delete-btn {
            background: none;
            border: none;
            color: #dc3545;
            cursor: pointer;
            font-size: 1.2em;
            padding: 5px 10px;
            border-radius: 5px;
            transition: background 0.3s ease;
        }
        
        .delete-btn:hover {
            background: #f8d7da;
        }
        
        .clear-btn {
            margin-top: 15px;
            width: 100%;
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 10px;
            color: white;
            font-weight: bold;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            transform: translateX(120%);
            transition: transform 0.3s ease;
            z-index: 1000;
        }
        
        .notification.show {
            transform: translateX(0);
        }
        
        .notification.success {
            background: linear-gradient(135deg, #42e695 0%, #3bb2b8 100%);
        }
        
        .notification.error {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }
        
        .loading {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.8);
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }
        
        .loading.active {
            display: flex;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏭 KONTROL POMPA OTOMATIS</h1>
            <p>Sistem Pengontrolan Pompa dengan Penjadwalan</p>
        </header>
        
        <div class="status-bar">
            <div class="time-display">
                📅 <span id="currentDay">-</span> 
                🕒 <span id="currentTime">-</span>
            </div>
            <div id="syncStatus" class="sync-status"></div>
        </div>
        
        <div class="main-content">
            <!-- Kontrol Pompa -->
            <div class="card">
                <h2>🎛️ KONTROL MANUAL</h2>
                <div class="pump-control">
                    <div class="pump-item" id="pump1Control">
                        <div class="pump-info">
                            <h3>POMPA 1</h3>
                            <div class="pump-status" id="pump1Status">LOADING...</div>
                            <div class="timer-display" id="pump1Timer"></div>
                        </div>
                        <button class="btn btn-toggle" onclick="togglePump('pompa1')">TOGGLE</button>
                    </div>
                    
                    <div class="pump-item" id="pump2Control">
                        <div class="pump-info">
                            <h3>POMPA 2</h3>
                            <div class="pump-status" id="pump2Status">LOADING...</div>
                            <div class="timer-display" id="pump2Timer"></div>
                        </div>
                        <button class="btn btn-toggle" onclick="togglePump('pompa2')">TOGGLE</button>
                    </div>
                    
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-on" onclick="controlPump('all', 'on')">NYALAKAN SEMUA</button>
                        <button class="btn btn-off" onclick="controlPump('all', 'off')">MATIKAN SEMUA</button>
                    </div>
                </div>
            </div>
            
            <!-- Penjadwalan -->
            <div class="card">
                <h2>📅 PENJADWALAN OTOMATIS</h2>
                
                <!-- Form Tambah Jadwal -->
                <div class="schedule-form">
                    <div class="form-group">
                        <label for="pumpSelect">Pompa</label>
                        <select id="pumpSelect">
                            <option value="pompa1">Pompa 1</option>
                            <option value="pompa2">Pompa 2</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="daySelect">Hari</label>
                        <select id="daySelect">
                            <option value="0">Senin</option>
                            <option value="1">Selasa</option>
                            <option value="2">Rabu</option>
                            <option value="3">Kamis</option>
                            <option value="4">Jumat</option>
                            <option value="5">Sabtu</option>
                            <option value="6">Minggu</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="hourSelect">Jam</label>
                        <select id="hourSelect">
                            """ + "".join([f'<option value="{i:02d}">{i:02d}</option>' for i in range(24)]) + """
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="minuteSelect">Menit</label>
                        <select id="minuteSelect">
                            """ + "".join([f'<option value="{i:02d}">{i:02d}</option>' for i in range(60)]) + """
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>Durasi</label>
                        <div class="duration-inputs">
                            <input type="number" id="durationHours" min="0" max="23" value="0" placeholder="Jam">
                            <input type="number" id="durationMinutes" min="0" max="59" value="1" placeholder="Menit">
                            <input type="number" id="durationSeconds" min="0" max="59" value="0" placeholder="Detik">
                        </div>
                    </div>
                </div>
                
                <button class="btn btn-toggle" onclick="addSchedule()">➕ TAMBAH JADWAL</button>
                
                <!-- Daftar Jadwal -->
                <div class="schedule-list" id="scheduleList">
                    <!-- Jadwal akan dimuat di sini -->
                </div>
                
                <button class="btn btn-danger clear-btn" onclick="clearSchedule('all')">
                    🗑️ HAPUS SEMUA JADWAL
                </button>
            </div>
        </div>
    </div>
    
    <!-- Notification -->
    <div class="notification" id="notification"></div>
    
    <!-- Loading -->
    <div class="loading" id="loading">
        <div class="spinner"></div>
    </div>
    
    <script>
        let currentSchedules = [];
        
        // Format waktu
        function formatTime(hours, minutes, seconds) {
            let totalSeconds = hours * 3600 + minutes * 60 + seconds;
            let parts = [];
            
            if (hours > 0) parts.push(`${hours} jam`);
            if (minutes > 0) parts.push(`${minutes} menit`);
            if (seconds > 0) parts.push(`${seconds} detik`);
            
            return parts.join(' ') || '0 detik';
        }
        
        // Tampilkan notifikasi
        function showNotification(message, type = 'success') {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = `notification ${type}`;
            notification.classList.add('show');
            
            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }
        
        // Tampilkan loading
        function showLoading(show) {
            document.getElementById('loading').classList.toggle('active', show);
        }
        
        // Update status pompa
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (data.success) {
                    // Update waktu
                    document.getElementById('currentDay').textContent = data.day;
                    document.getElementById('currentTime').textContent = data.time;
                    
                    // Update status sync
                    const syncStatus = document.getElementById('syncStatus');
                    syncStatus.textContent = data.sync ? '🔄 Tersinkronisasi' : '⚠️ Tidak tersinkronisasi';
                    syncStatus.className = data.sync ? 'sync-status sync-on' : 'sync-status sync-off';
                    
                    // Update pompa 1
                    updatePumpDisplay('pompa1', data.pompa1);
                    
                    // Update pompa 2
                    updatePumpDisplay('pompa2', data.pompa2);
                }
            } catch (error) {
                console.error('Error updating status:', error);
            }
        }
        
        // Update tampilan pompa
        function updatePumpDisplay(pump, data) {
            const pumpNum = pump === 'pompa1' ? '1' : '2';
            const statusElement = document.getElementById(`pump${pumpNum}Status`);
            const timerElement = document.getElementById(`pump${pumpNum}Timer`);
            
            // Update status
            statusElement.textContent = data.status ? '🟢 ON' : '🔴 OFF';
            statusElement.className = `pump-status ${data.status ? 'status-on' : 'status-off'}`;
            
            // Update timer
            if (data.timer > 0) {
                const minutes = Math.floor(data.timer / 60);
                const seconds = data.timer % 60;
                timerElement.textContent = `⏰ Timer: ${minutes}:${seconds.toString().padStart(2, '0')}`;
                timerElement.style.color = '#ff9800';
            } else {
                timerElement.textContent = '⏰ Tidak ada timer aktif';
                timerElement.style.color = '#666';
            }
        }
        
        // Kontrol pompa
        async function togglePump(pump) {
            showLoading(true);
            try {
                const response = await fetch(`/toggle/${pump}`);
                await response.json();
                await updateStatus();
                showNotification(`Pompa ${pump} di-toggle`, 'success');
            } catch (error) {
                showNotification('Gagal mengontrol pompa', 'error');
            } finally {
                showLoading(false);
            }
        }
        
        async function controlPump(pump, action) {
            showLoading(true);
            try {
                if (pump === 'all') {
                    // Kontrol semua pompa
                    for (const p of ['pompa1', 'pompa2']) {
                        const state = action === 'on';
                        // Ini hanya contoh - perlu endpoint API untuk set state spesifik
                        await fetch(`/api/set_pump?pump=${p}&state=${state}`);
                    }
                } else {
                    await fetch(`/api/set_pump?pump=${pump}&state=${action === 'on'}`);
                }
                await updateStatus();
                showNotification(`Semua pompa ${action === 'on' ? 'dinyalakan' : 'dimatikan'}`, 'success');
            } catch (error) {
                showNotification('Gagal mengontrol pompa', 'error');
            } finally {
                showLoading(false);
            }
        }
        
        // Jadwal functions
        async function loadSchedules() {
            try {
                const response = await fetch('/api/schedule');
                const data = await response.json();
                
                if (data.success) {
                    currentSchedules = data.schedules;
                    renderSchedules();
                }
            } catch (error) {
                console.error('Error loading schedules:', error);
            }
        }
        
        function renderSchedules() {
            const scheduleList = document.getElementById('scheduleList');
            
            if (currentSchedules.length === 0) {
                scheduleList.innerHTML = `
                    <div style="text-align: center; padding: 30px; color: #666;">
                        📭 Tidak ada jadwal yang ditambahkan
                    </div>
                `;
                return;
            }
            
            scheduleList.innerHTML = '';
            
            // Urutkan berdasarkan hari dan waktu
            currentSchedules.sort((a, b) => {
                if (a.day !== b.day) return a.day - b.day;
                if (a.hour !== b.hour) return a.hour - b.hour;
                return a.minute - b.minute;
            });
            
            const days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'];
            
            currentSchedules.forEach(schedule => {
                const scheduleItem = document.createElement('div');
                scheduleItem.className = 'schedule-item';
                scheduleItem.innerHTML = `
                    <div class="schedule-info">
                        <div class="schedule-time">
                            📅 ${days[schedule.day]} - ${schedule.hour_str}:${schedule.minute_str}
                        </div>
                        <div class="schedule-details">
                            Pompa: ${schedule.pump === 'pompa1' ? 'POMPA 1' : 'POMPA 2'} | 
                            Durasi: ${formatTime(schedule.duration_hours, schedule.duration_minutes, schedule.duration_seconds)}
                        </div>
                    </div>
                    <button class="delete-btn" onclick="deleteSchedule('${schedule.id}')">
                        ❌
                    </button>
                `;
                scheduleList.appendChild(scheduleItem);
            });
        }
        
        async function addSchedule() {
            const pump = document.getElementById('pumpSelect').value;
            const day = parseInt(document.getElementById('daySelect').value);
            const hour = parseInt(document.getElementById('hourSelect').value);
            const minute = parseInt(document.getElementById('minuteSelect').value);
            const hours = parseInt(document.getElementById('durationHours').value) || 0;
            const minutes = parseInt(document.getElementById('durationMinutes').value) || 0;
            const seconds = parseInt(document.getElementById('durationSeconds').value) || 0;
            
            // Validasi
            if (hours === 0 && minutes === 0 && seconds === 0) {
                showNotification('Durasi tidak boleh 0', 'error');
                return;
            }
            
            if (minutes > 59 || seconds > 59) {
                showNotification('Menit/detik tidak valid', 'error');
                return;
            }
            
            showLoading(true);
            
            try {
                const params = new URLSearchParams({
                    pump: pump,
                    day: day,
                    hour: hour,
                    minute: minute,
                    duration_hours: hours,
                    duration_minutes: minutes,
                    duration_seconds: seconds
                });
                
                const response = await fetch(`/api/add_schedule?${params}`);
                const data = await response.json();
                
                if (data.success) {
                    showNotification('Jadwal berhasil ditambahkan', 'success');
                    await loadSchedules();
                    
                    // Reset form
                    document.getElementById('durationMinutes').value = '1';
                    document.getElementById('durationSeconds').value = '0';
                } else {
                    showNotification(data.message || 'Gagal menambahkan jadwal', 'error');
                }
            } catch (error) {
                showNotification('Terjadi kesalahan', 'error');
            } finally {
                showLoading(false);
            }
        }
        
        async function deleteSchedule(scheduleId) {
            if (!confirm('Hapus jadwal ini?')) return;
            
            showLoading(true);
            
            try {
                const response = await fetch(`/api/delete_schedule?id=${scheduleId}`);
                const data = await response.json();
                
                if (data.success) {
                    showNotification('Jadwal berhasil dihapus', 'success');
                    await loadSchedules();
                } else {
                    showNotification(data.message || 'Gagal menghapus jadwal', 'error');
                }
            } catch (error) {
                showNotification('Terjadi kesalahan', 'error');
            } finally {
                showLoading(false);
            }
        }
        
        async function clearSchedule(pump) {
            if (!confirm(`Hapus semua jadwal${pump === 'all' ? '' : ' untuk pompa ini'}?`)) return;
            
            showLoading(true);
            
            try {
                const response = await fetch(`/api/clear_schedule?pump=${pump}`);
                const data = await response.json();
                
                if (data.success) {
                    showNotification('Jadwal berhasil dikosongkan', 'success');
                    await loadSchedules();
                } else {
                    showNotification(data.message || 'Gagal mengosongkan jadwal', 'error');
                }
            } catch (error) {
                showNotification('Terjadi kesalahan', 'error');
            } finally {
                showLoading(false);
            }
        }
        
        // Inisialisasi
        document.addEventListener('DOMContentLoaded', () => {
            updateStatus();
            loadSchedules();
            
            // Update setiap 2 detik
            setInterval(updateStatus, 2000);
            
            // Update jadwal setiap 10 detik
            setInterval(loadSchedules, 10000);
        });
    </script>
</body>
</html>"""
    return html

# Handler request
def handle_request(client, request):
    try:
        request_line = request.split('\r\n')[0]
        method_path = request_line.split(' ')
        
        if len(method_path) < 2:
            client.close()
            return
            
        method = method_path[0]
        path = method_path[1]
        
        # Extract query string
        path_parts = path.split('?')
        endpoint = path_parts[0]
        query_string = path_parts[1] if len(path_parts) > 1 else ''
        
        if endpoint == '/':
            client.send('HTTP/1.1 200 OK\r\nContent-type: text/html\r\n\r\n')
            client.send(get_dashboard())
            
        elif endpoint.startswith('/api/'):
            params = parse_query_string(query_string)
            response = handle_api(client, endpoint, params)
            client.send('HTTP/1.1 200 OK\r\nContent-type: application/json\r\n\r\n')
            client.send(response)
            
        elif endpoint.startswith('/toggle/'):
            if 'pompa1' in endpoint:
                set_pump("pompa1", not pump_status["pompa1"])
            elif 'pompa2' in endpoint:
                set_pump("pompa2", not pump_status["pompa2"])
            client.send('HTTP/1.1 200 OK\r\nContent-type: application/json\r\n\r\n')
            client.send('{"success":true}')
            
        elif endpoint == '/api/set_pump':
            params = parse_query_string(query_string)
            pump = params.get('pump', '')
            state = params.get('state', '').lower() == 'true'
            
            if pump == 'all':
                set_pump("pompa1", state)
                set_pump("pompa2", state)
                response = '{"success":true}'
            elif pump in pump_status:
                set_pump(pump, state)
                response = '{"success":true}'
            else:
                response = '{"success":false,"message":"Pompa tidak ditemukan"}'
                
            client.send('HTTP/1.1 200 OK\r\nContent-type: application/json\r\n\r\n')
            client.send(response)
            
        else:
            client.send('HTTP/1.1 404 Not Found\r\nContent-type: text/plain\r\n\r\n')
            client.send('404 Not Found')
            
    except Exception as e:
        try:
            client.send('HTTP/1.1 500 Internal Error\r\nContent-type: text/plain\r\n\r\n')
            client.send('Internal Server Error')
        except:
            pass
    finally:
        try:
            client.close()
        except:
            pass

# Server web
def run_server(ip):
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(5)
    
    s.setblocking(False)
    
    print(f"Server: http://{ip}")
    
    global last_check
    
    while True:
        try:
            current_time = time.time()
            if current_time - last_check >= CHECK_INTERVAL:
                check_sync()
                check_schedule()
                check_timers()
                last_check = current_time
            
            try:
                client, addr = s.accept()
                try:
                    client.settimeout(5.0)
                    request = client.recv(4096).decode()
                    if request:
                        handle_request(client, request)
                except:
                    client.close()
            except OSError:
                pass
            
            time.sleep(0.01)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(0.1)

# Main
def main():
    # Load jadwal dari file
    load_schedule()
    
    # Coba sync waktu
    for _ in range(3):
        if sync_time():
            break
        time.sleep(1)
    
    # Koneksi WiFi
    ip = connect_wifi()
    if ip is None:
        ip = setup_ap()
    
    # Jalankan server
    try:
        run_server(ip)
    finally:
        # Matikan semua pompa saat keluar
        for pump in pump_status:
            set_pump(pump, False)

if __name__ == "__main__":
    main()
