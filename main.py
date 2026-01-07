# system_plant_simple.py - BRUTALISM EDITION
import network
import socket
from machine import Pin
from time import sleep, time, localtime
import ujson as json

# ===================== KONFIGURASI =====================
SSID = "Lab Telkom"
PASSWORD = ""

# ===================== PIN ESP32 =====================
PUMP_1_PIN = 2
PUMP_2_PIN = 4

relay_pump1 = Pin(PUMP_1_PIN, Pin.OUT)
relay_pump2 = Pin(PUMP_2_PIN, Pin.OUT)

relay_pump1.value(1)  # OFF (active LOW)
relay_pump2.value(1)  # OFF (active LOW)

# ===================== STATUS =====================
pump1_state = 0
pump2_state = 0
pump2_mode = "manual"

# ===================== SCHEDULE =====================
schedule_enabled = False
schedule_start_hour = 8
schedule_start_minute = 0
schedule_duration = 30
schedule_unit = "detik"
schedule_days = [1, 1, 1, 1, 1, 1, 1]

last_schedule_check = 0
pump_start_time = 0
schedule_executed = False  # anti loop

# ===================== RELAY =====================
def control_pump1(state):
    relay_pump1.value(0 if state else 1)

def control_pump2(state):
    relay_pump2.value(0 if state else 1)

# ===================== SCHEDULE CORE =====================
def check_schedule():
    global pump2_state, last_schedule_check
    global pump_start_time, schedule_executed

    if pump2_mode != "schedule" or not schedule_enabled:
        return

    now = time()

    # cek tiap 1 detik
    if now - last_schedule_check < 1:
        return
    last_schedule_check = now

    lt = localtime()
    hour = lt[3]
    minute = lt[4]
    weekday = lt[6]

    # reset flag jika menit berganti
    if minute != schedule_start_minute:
        schedule_executed = False

    if schedule_days[weekday] != 1:
        return

    # ===== START SEKALI =====
    if (hour == schedule_start_hour and
        minute == schedule_start_minute and
        not schedule_executed):

        pump2_state = 1
        control_pump2(1)
        pump_start_time = now
        schedule_executed = True
        print("SCHEDULE START")

    # ===== STOP SESUAI DURASI =====
    if pump2_state == 1:
        elapsed = now - pump_start_time

        multiplier = 1
        if schedule_unit == "menit":
            multiplier = 60
        elif schedule_unit == "jam":
            multiplier = 3600

        if elapsed >= schedule_duration * multiplier:
            pump2_state = 0
            control_pump2(0)
            print("SCHEDULE STOP")

# ===================== HTML (BRUTALISM STYLE) =====================

def get_html():
    return """HTTP/1.1 200 OK
Content-Type: text/html
Connection: close

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLANT_CTRL_SYS</title>
    <style>
        /* BRUTALISM CSS RESET */
        * { box-sizing: border-box; }
        body { 
            font-family: 'Courier New', Courier, monospace; 
            padding: 20px; 
            background-color: #e0e0e0; 
            color: #000;
        }
        
        h1, h2, h3, h4 {
            text-transform: uppercase;
            letter-spacing: -1px;
            margin-bottom: 15px;
        }

        h1 { 
            font-size: 2rem; 
            border-bottom: 5px solid black; 
            padding-bottom: 10px;
            background: #fff;
            border: 4px solid black;
            box-shadow: 6px 6px 0px #000;
            padding: 15px;
        }

        /* MAIN CONTAINER */
        .container {
            max-width: 700px;
            margin: 0 auto;
        }

        /* CARD STYLE */
        .pump { 
            margin: 30px 0; 
            padding: 20px; 
            background: #fff; 
            border: 4px solid #000; 
            box-shadow: 8px 8px 0px #000;
        }

        /* BUTTON CONTROLS */
        .toggle-btn { 
            display: block;
            width: 100%;
            padding: 20px; 
            font-size: 24px; 
            font-weight: 900;
            font-family: 'Courier New', monospace;
            text-transform: uppercase;
            border: 4px solid #000;
            cursor: pointer;
            transition: all 0.1s;
            margin-bottom: 15px;
            border-radius: 0 !important; /* NO ROUNDED CORNERS */
        }

        .toggle-btn:active {
            transform: translate(4px, 4px);
            box-shadow: none !important;
        }

        .btn-on { 
            background: #00ff66; /* Neon Green */
            color: black; 
            box-shadow: 6px 6px 0px #000;
        }
        
        .btn-off { 
            background: #ff3333; /* Brutal Red */
            color: black; 
            box-shadow: 6px 6px 0px #000;
        }

        /* MODE BUTTONS */
        .mode-btn { 
            padding: 10px 20px; 
            margin: 5px 5px 5px 0;
            background: #fff; 
            color: black;
            border: 3px solid #000;
            font-weight: bold;
            font-family: 'Courier New', monospace;
            cursor: pointer;
            box-shadow: 4px 4px 0px #000;
        }
        
        .mode-btn:active { transform: translate(2px, 2px); box-shadow: 2px 2px 0px #000; }

        .mode-btn.active {
            background: #000;
            color: #fff;
        }

        /* STATUS BADGE */
        .status {
            font-weight: bold;
            padding: 10px;
            border: 3px solid #000;
            display: inline-block;
            text-transform: uppercase;
            background: #ffff00; /* Yellow */
            font-size: 1.2rem;
        }
        
        .status-on { background: #00ff66; color: black; }
        .status-off { background: #ff3333; color: black; }

        /* SCHEDULE CONTAINER */
        .schedule-container {
            margin-top: 25px;
            padding: 20px;
            background: #d4d4d4;
            border: 4px solid #000;
            display: none;
        }
        
        .schedule-container.active { display: block; }

        .schedule-section {
            margin: 15px 0;
            padding: 15px;
            background: #fff;
            border: 3px solid #000;
        }

        /* INPUTS */
        .schedule-input, .schedule-select {
            padding: 10px;
            border: 3px solid #000;
            background: #eee;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            font-size: 1rem;
            border-radius: 0;
        }
        
        .schedule-input:focus, .schedule-select:focus {
            background: #fff;
            outline: none;
            box-shadow: 4px 4px 0px #000;
        }

        /* DAY SELECTOR */
        .day-selector {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin: 10px 0;
        }
        
        .day-btn {
            padding: 10px;
            border: 3px solid #000;
            background: #fff;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            cursor: pointer;
            flex-grow: 1;
            text-align: center;
        }
        
        .day-btn.active {
            background: #000;
            color: #fff;
        }

        /* INFO BOX */
        .info {
            margin-top: 15px;
            padding: 15px;
            background: #000;
            color: #00ff66; /* Terminal green text */
            border: 3px solid #000;
            font-family: 'Courier New', monospace;
        }

        .timer-display {
            font-size: 1.2rem;
            color: #ff3333;
            font-weight: bold;
            border-top: 1px dashed #00ff66;
            margin-top: 10px;
            padding-top: 5px;
        }

        /* UTILITY */
        .btn-action {
            padding: 15px; 
            border: 3px solid #000;
            font-weight: bold;
            cursor: pointer;
            text-transform: uppercase;
            font-family: 'Courier New', monospace;
            box-shadow: 5px 5px 0px #000;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        
        .btn-action:active { transform: translate(3px, 3px); box-shadow: 2px 2px 0px #000; }
        
        hr { border: 2px solid #000; margin: 20px 0; }

    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 SYSTEM_PLANT_CTRL</h1>
        
        <div class="pump">
            <h2>💧 WATER_PUMP_01</h2>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span id="status1" class="status status-off">OFFLINE</span>
            </div>
            <button id="toggle1" class="toggle-btn btn-off" onclick="togglePump(1)">
                SWITCH ON
            </button>
        </div>
        
        <div class="pump">
            <h2>🧪 NUTRIENT_PUMP_02</h2>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <span id="status2" class="status status-off">OFFLINE</span>
            </div>
            <button id="toggle2" class="toggle-btn btn-off" onclick="togglePump(2)">
                SWITCH ON
            </button>
            
            <hr>

            <div style="margin-top: 15px;">
                <span style="font-weight:bold; background:#000; color:#fff; padding:5px;">MODE_SELECT:</span><br><br>
                <button id="btnManual" class="mode-btn active" onclick="setMode('manual')">MANUAL</button>
                <button id="btnSchedule" class="mode-btn" onclick="setMode('schedule')">AUTO_SCHED</button>
            </div>
            
            <div style="margin-top: 15px;">
                <span>CURRENT MODE: <strong id="mode2" style="background:#ffff00; padding:2px 5px; border:2px solid black;">MANUAL</strong></span>
                <span id="scheduleStatus" style="display:block; margin-top:5px; font-weight:bold;"></span>
            </div>

            <div id="scheduleContainer" class="schedule-container">
                <h3>⏰ SCHED_CONFIG</h3>
                
                <div class="schedule-section">
                    <h4>START_TIME</h4>
                    <div>
                        <label>HR:</label>
                        <input type="number" id="startHour" class="schedule-input" value="8" min="0" max="23" style="width: 60px;">
                        <label>MN:</label>
                        <input type="number" id="startMinute" class="schedule-input" value="0" min="0" max="59" style="width: 60px;">
                    </div>
                </div>
                
                <div class="schedule-section">
                    <h4>ACTIVE_DAYS</h4>
                    <div class="day-selector">
                        <button class="day-btn active" onclick="toggleDay(0)">MON</button>
                        <button class="day-btn active" onclick="toggleDay(1)">TUE</button>
                        <button class="day-btn active" onclick="toggleDay(2)">WED</button>
                        <button class="day-btn active" onclick="toggleDay(3)">THU</button>
                        <button class="day-btn active" onclick="toggleDay(4)">FRI</button>
                        <button class="day-btn active" onclick="toggleDay(5)">SAT</button>
                        <button class="day-btn active" onclick="toggleDay(6)">SUN</button>
                    </div>
                </div>
                
                <div class="schedule-section">
                    <h4>DURATION</h4>
                    <div>
                        <input type="number" id="scheduleDuration" class="schedule-input" value="30" min="1" max="999" style="width: 80px;">
                        <select id="scheduleUnit" class="schedule-select">
                            <option value="detik">SEC</option>
                            <option value="menit">MIN</option>
                            <option value="jam">HR</option>
                        </select>
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <button onclick="toggleSchedule()" id="scheduleToggleBtn" class="btn-action" style="background: #ffff00;">
                        ⚠ ACTIVATE
                    </button>
                    <button onclick="saveSchedule()" class="btn-action" style="background: #00ccff;">
                        💾 SAVE_CFG
                    </button>
                </div>
                
                <div class="info" id="scheduleInfo">
                    <div>NO_ACTIVE_SCHEDULE</div>
                    <div id="currentTime" class="time-display" style="margin-top:5px; color:#fff;"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
    let activeDays = [1, 1, 1, 1, 1, 1, 1];
    let timerInterval;
    
    async function togglePump(pump) {
        const res = await fetch('/status');
        const data = await res.json();
        
        const currentState = (pump === 1) ? data.pump1 : data.pump2;
        const action = currentState ? 'off' : 'on';
        
        await fetch('/control?pump=' + pump + '&action=' + action);
        updateStatus();
    }
    
    async function setMode(mode) {
        await fetch('/mode?mode=' + mode);
        
        document.getElementById('btnManual').classList.remove('active');
        document.getElementById('btnSchedule').classList.remove('active');
        
        if (mode === 'manual') {
            document.getElementById('btnManual').classList.add('active');
            document.getElementById('scheduleContainer').classList.remove('active');
        } else {
            document.getElementById('btnSchedule').classList.add('active');
            document.getElementById('scheduleContainer').classList.add('active');
        }
        
        updateStatus();
    }
    
    function toggleDay(dayIndex) {
        const btn = document.querySelectorAll('.day-btn')[dayIndex];
        activeDays[dayIndex] = activeDays[dayIndex] ? 0 : 1;
        
        if (activeDays[dayIndex]) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    }
    
    async function toggleSchedule() {
        const btn = document.getElementById('scheduleToggleBtn');
        const isActive = btn.textContent.includes('ACTIVATE');
        
        if (isActive || btn.textContent.includes('AKTIFKAN')) {
            await fetch('/schedule_enable?enable=1');
        } else {
            await fetch('/schedule_enable?enable=0');
        }
        updateStatus();
    }
    
    async function saveSchedule() {
        const hour = document.getElementById('startHour').value;
        const minute = document.getElementById('startMinute').value;
        const duration = document.getElementById('scheduleDuration').value;
        const unit = document.getElementById('scheduleUnit').value;
        const days = activeDays.join(',');
        
        await fetch('/schedule_set?hour=' + hour + '&minute=' + minute + 
                    '&duration=' + duration + '&unit=' + unit + '&days=' + days);
        
        updateStatus();
        alert('CONFIG_SAVED');
    }
    
    async function updateStatus() {
        const res = await fetch('/status');
        const data = await res.json();
        
        // Update pompa 1
        const toggleBtn1 = document.getElementById('toggle1');
        const status1 = document.getElementById('status1');
        
        if (data.pump1) {
            toggleBtn1.textContent = 'SWITCH OFF';
            toggleBtn1.className = 'toggle-btn btn-on';
            status1.textContent = 'ONLINE';
            status1.className = 'status status-on';
        } else {
            toggleBtn1.textContent = 'SWITCH ON';
            toggleBtn1.className = 'toggle-btn btn-off';
            status1.textContent = 'OFFLINE';
            status1.className = 'status status-off';
        }
        
        // Update pompa 2
        const toggleBtn2 = document.getElementById('toggle2');
        const status2 = document.getElementById('status2');
        
        if (data.pump2) {
            toggleBtn2.textContent = 'SWITCH OFF';
            toggleBtn2.className = 'toggle-btn btn-on';
            status2.textContent = 'ONLINE';
            status2.className = 'status status-on';
        } else {
            toggleBtn2.textContent = 'SWITCH ON';
            toggleBtn2.className = 'toggle-btn btn-off';
            status2.textContent = 'OFFLINE';
            status2.className = 'status status-off';
        }
        
        // Update mode
        document.getElementById('mode2').textContent = data.mode.toUpperCase();
        
        // Update schedule info
        if (data.schedule_enabled !== undefined) {
            const toggleBtn = document.getElementById('scheduleToggleBtn');
            const statusLabel = document.getElementById('scheduleStatus');
            
            if (data.schedule_enabled) {
                toggleBtn.innerHTML = '⏸ DEACTIVATE';
                toggleBtn.style.background = '#ff3333'; 
                statusLabel.textContent = '>> SCHEDULER: ACTIVE';
                statusLabel.style.color = '#009900';
            } else {
                toggleBtn.innerHTML = '⚠ ACTIVATE';
                toggleBtn.style.background = '#ffff00';
                statusLabel.textContent = '>> SCHEDULER: INACTIVE';
                statusLabel.style.color = '#cc0000';
            }
        }
        
        // Update schedule details
        if (data.schedule_start_hour !== undefined) {
            const dayNames = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
            let activeDayNames = [];
            if (data.schedule_days) {
                for (let i = 0; i < data.schedule_days.length; i++) {
                    if (data.schedule_days[i] === 1) {
                        activeDayNames.push(dayNames[i]);
                    }
                }
            }
            
            const scheduleText = `${data.schedule_start_hour.toString().padStart(2, '0')}:${data.schedule_start_minute.toString().padStart(2, '0')} - ${data.schedule_duration} ${data.schedule_unit.toUpperCase()}`;
            const daysText = activeDayNames.join(', ');
            
            let infoHtml = `
                <div>TARGET: <strong>${scheduleText}</strong></div>
                <div>DAYS: [ ${daysText} ]</div>
                <div>STATE: ${data.schedule_enabled ? 'RUNNING' : 'STOPPED'}</div>
            `;
            
            if (data.pump2 && data.mode === 'schedule' && data.schedule_enabled) {
                let multiplier = 1;
                if (data.schedule_unit === 'menit') multiplier = 60;
                else if (data.schedule_unit === 'jam') multiplier = 3600;
                const totalSeconds = data.schedule_duration * multiplier;
                infoHtml += `<div id="timerDisplay" class="timer-display">>>> PUMPING: 0/${totalSeconds}s</div>`;
            }
            
            document.getElementById('scheduleInfo').innerHTML = infoHtml;
            
            const now = new Date();
            document.getElementById('currentTime').textContent = `SYS_TIME: ${now.toLocaleTimeString('id-ID')}`;
        }
    }
    
    setInterval(updateStatus, 2000);
    updateStatus();
    </script>
</body>
</html>"""


# ===================== SERVER =====================
def handle_request(conn, request):
    global pump1_state, pump2_state, pump2_mode
    global schedule_enabled, schedule_start_hour
    global schedule_start_minute, schedule_duration
    global schedule_unit, schedule_days, schedule_executed

    if "/ " in request:
        conn.send(get_html())

    elif "/status" in request:
        data = {
            "pump1": pump1_state,
            "pump2": pump2_state,
            "mode": pump2_mode,
            "schedule_enabled": schedule_enabled,
            "schedule_start_hour": schedule_start_hour,
            "schedule_start_minute": schedule_start_minute,
            "schedule_duration": schedule_duration,
            "schedule_unit": schedule_unit,
            "schedule_days": schedule_days
        }
        conn.send(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
            + json.dumps(data)
        )

    elif "/control" in request:
        # ===== PUMP 1 =====
        if "pump=1" in request:
            if "action=on" in request:
                pump1_state = 1
                control_pump1(1)
            elif "action=off" in request:
                pump1_state = 0
                control_pump1(0)

        # ===== PUMP 2 =====
        if "pump=2" in request:
            if "action=on" in request:
                pump2_state = 1
                control_pump2(1)
            elif "action=off" in request:
                pump2_state = 0
                control_pump2(0)
                schedule_executed = False  # cegah nyala ulang

        conn.send("HTTP/1.1 200 OK\r\n\r\n")

    elif "/mode" in request:
        if "mode=manual" in request:
            pump2_mode = "manual"
            pump2_state = 0
            control_pump2(0)
            schedule_executed = False
        else:
            pump2_mode = "schedule"
        conn.send("HTTP/1.1 200 OK\r\n\r\n")

    elif "/schedule_enable" in request:
        schedule_enabled = "enable=1" in request
        conn.send("HTTP/1.1 200 OK\r\n\r\n")

    elif "/schedule_set" in request:
        try:
            q = request.split("?")[1].split(" ")[0]
            p = dict(x.split("=") for x in q.split("&"))

            schedule_start_hour = int(p["hour"])
            schedule_start_minute = int(p["minute"])
            schedule_duration = int(p["duration"])
            schedule_unit = p["unit"]
            schedule_days = [int(x) for x in p["days"].split(",")]
            schedule_executed = False

            print("SCHEDULE UPDATED")

        except Exception as e:
            print("Schedule error:", e)

        conn.send("HTTP/1.1 200 OK\r\n\r\n")

    else:
        conn.send("HTTP/1.1 404\r\n\r\n")

# ===================== MAIN =====================
def main():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    while not wlan.isconnected():
        sleep(0.5)

    print("IP:", wlan.ifconfig()[0])

    s = socket.socket()
    s.bind(("0.0.0.0", 80))
    s.listen(5)

    while True:
        conn, addr = s.accept()
        request = conn.recv(1024).decode()
        handle_request(conn, request)
        conn.close()

        check_schedule()
        sleep(0.2)

if __name__ == "__main__":
    main()
