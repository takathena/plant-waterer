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
PUMP_1_PIN = 16
PUMP_2_PIN = 4
PUMP_3_PIN = 17  # Tambah pin untuk relay 3

relay_pump1 = Pin(PUMP_1_PIN, Pin.OUT)
relay_pump2 = Pin(PUMP_2_PIN, Pin.OUT)
relay_pump3 = Pin(PUMP_3_PIN, Pin.OUT)  # Tambah relay 3

relay_pump1.value(1)  # OFF (active LOW)
relay_pump2.value(1)  # OFF (active LOW)
relay_pump3.value(1)  # OFF (active LOW)

# ===================== STATUS =====================
pump1_state = 0
pump2_state = 0
pump3_state = 0
pump2_mode = "manual"
pump3_mode = "manual"  # Tambah mode untuk relay 3

# ===================== SCHEDULE =====================
schedule_enabled = False
schedule_enabled_3 = False  # Tambah schedule untuk relay 3
schedule_start_hour = 8
schedule_start_minute = 0
schedule_duration = 30
schedule_unit = "detik"
schedule_days = [1, 1, 1, 1, 1, 1, 1]

# Schedule untuk relay 3
schedule_start_hour_3 = 9
schedule_start_minute_3 = 0
schedule_duration_3 = 30
schedule_unit_3 = "detik"
schedule_days_3 = [1, 1, 1, 1, 1, 1, 1]

last_schedule_check = 0
last_schedule_check_3 = 0  # Tambah untuk relay 3
pump_start_time = 0
pump_start_time_3 = 0  # Tambah untuk relay 3
schedule_executed = False  # anti loop
schedule_executed_3 = False  # Tambah untuk relay 3

# ===================== RELAY =====================
def control_pump1(state):
    relay_pump1.value(0 if state else 1)

def control_pump2(state):
    relay_pump2.value(0 if state else 1)

def control_pump3(state):  # Tambah fungsi kontrol relay 3
    relay_pump3.value(0 if state else 1)

# ===================== SCHEDULE CORE =====================
def check_schedule():
    global pump2_state, pump3_state, last_schedule_check, last_schedule_check_3
    global pump_start_time, pump_start_time_3, schedule_executed, schedule_executed_3

    # ===== CHECK SCHEDULE PUMP 2 =====
    if pump2_mode == "schedule" and schedule_enabled:
        now = time()
        
        # cek tiap 1 detik
        if now - last_schedule_check >= 1:
            last_schedule_check = now
            lt = localtime()
            hour = lt[3]
            minute = lt[4]
            weekday = lt[6]

            # reset flag jika menit berganti
            if minute != schedule_start_minute:
                schedule_executed = False

            if schedule_days[weekday] == 1:
                # ===== START SEKALI =====
                if (hour == schedule_start_hour and
                    minute == schedule_start_minute and
                    not schedule_executed):

                    pump2_state = 1
                    control_pump2(1)
                    pump_start_time = now
                    schedule_executed = True
                    print("SCHEDULE PUMP 2 START")

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
                        print("SCHEDULE PUMP 2 STOP")

    # ===== CHECK SCHEDULE PUMP 3 =====
    if pump3_mode == "schedule" and schedule_enabled_3:
        now = time()
        
        # cek tiap 1 detik
        if now - last_schedule_check_3 >= 1:
            last_schedule_check_3 = now
            lt = localtime()
            hour = lt[3]
            minute = lt[4]
            weekday = lt[6]

            # reset flag jika menit berganti
            if minute != schedule_start_minute_3:
                schedule_executed_3 = False

            if schedule_days_3[weekday] == 1:
                # ===== START SEKALI =====
                if (hour == schedule_start_hour_3 and
                    minute == schedule_start_minute_3 and
                    not schedule_executed_3):

                    pump3_state = 1
                    control_pump3(1)
                    pump_start_time_3 = now
                    schedule_executed_3 = True
                    print("SCHEDULE PUMP 3 START")

                # ===== STOP SESUAI DURASI =====
                if pump3_state == 1:
                    elapsed = now - pump_start_time_3

                    multiplier = 1
                    if schedule_unit_3 == "menit":
                        multiplier = 60
                    elif schedule_unit_3 == "jam":
                        multiplier = 3600

                    if elapsed >= schedule_duration_3 * multiplier:
                        pump3_state = 0
                        control_pump3(0)
                        print("SCHEDULE PUMP 3 STOP")

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
            max-width: 900px;
            margin: 0 auto;
        }

        /* PUMP GRID LAYOUT */
        .pump-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }

        /* CARD STYLE */
        .pump { 
            padding: 20px; 
            background: #fff; 
            border: 4px solid #000; 
            box-shadow: 8px 8px 0px #000;
            height: fit-content;
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
            border-radius: 0 !important;
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

        /* PUMP LABEL COLORS */
        .pump-label-1 { color: #0066cc; }
        .pump-label-2 { color: #cc3300; }
        .pump-label-3 { color: #6633cc; }

    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 SYSTEM_PLANT_CTRL - 3 RELAYS</h1>
        
        <div class="pump-grid">
            <!-- PUMP 1 -->
            <div class="pump">
                <h2 class="pump-label-1">💧 WATER_PUMP_01</h2>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span id="status1" class="status status-off">OFFLINE</span>
                </div>
                <button id="toggle1" class="toggle-btn btn-off" onclick="togglePump(1)">
                    SWITCH ON
                </button>
                <div class="info">
                    <div>MANUAL CONTROL ONLY</div>
                    <div>TYPE: WATER SUPPLY</div>
                </div>
            </div>
            
            <!-- PUMP 2 -->
            <div class="pump">
                <h2 class="pump-label-2">🧪 NUTRIENT_PUMP_02</h2>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <span id="status2" class="status status-off">OFFLINE</span>
                </div>
                <button id="toggle2" class="toggle-btn btn-off" onclick="togglePump(2)">
                    SWITCH ON
                </button>
                
                <hr>

                <div style="margin-top: 15px;">
                    <span style="font-weight:bold; background:#000; color:#fff; padding:5px;">MODE_SELECT:</span><br><br>
                    <button id="btnManual2" class="mode-btn active" onclick="setMode(2, 'manual')">MANUAL</button>
                    <button id="btnSchedule2" class="mode-btn" onclick="setMode(2, 'schedule')">AUTO_SCHED</button>
                </div>
                
                <div style="margin-top: 15px;">
                    <span>CURRENT MODE: <strong id="mode2" style="background:#ffff00; padding:2px 5px; border:2px solid black;">MANUAL</strong></span>
                    <span id="scheduleStatus2" style="display:block; margin-top:5px; font-weight:bold;"></span>
                </div>

                <div id="scheduleContainer2" class="schedule-container">
                    <h3>⏰ SCHED_CONFIG PUMP 2</h3>
                    
                    <div class="schedule-section">
                        <h4>START_TIME</h4>
                        <div>
                            <label>HR:</label>
                            <input type="number" id="startHour2" class="schedule-input" value="8" min="0" max="23" style="width: 60px;">
                            <label>MN:</label>
                            <input type="number" id="startMinute2" class="schedule-input" value="0" min="0" max="59" style="width: 60px;">
                        </div>
                    </div>
                    
                    <div class="schedule-section">
                        <h4>ACTIVE_DAYS</h4>
                        <div class="day-selector">
                            <button class="day-btn active" onclick="toggleDay(2, 0)">MON</button>
                            <button class="day-btn active" onclick="toggleDay(2, 1)">TUE</button>
                            <button class="day-btn active" onclick="toggleDay(2, 2)">WED</button>
                            <button class="day-btn active" onclick="toggleDay(2, 3)">THU</button>
                            <button class="day-btn active" onclick="toggleDay(2, 4)">FRI</button>
                            <button class="day-btn active" onclick="toggleDay(2, 5)">SAT</button>
                            <button class="day-btn active" onclick="toggleDay(2, 6)">SUN</button>
                        </div>
                    </div>
                    
                    <div class="schedule-section">
                        <h4>DURATION</h4>
                        <div>
                            <input type="number" id="scheduleDuration2" class="schedule-input" value="30" min="1" max="999" style="width: 80px;">
                            <select id="scheduleUnit2" class="schedule-select">
                                <option value="detik">SEC</option>
                                <option value="menit">MIN</option>
                                <option value="jam">HR</option>
                            </select>
                        </div>
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <button onclick="toggleSchedule(2)" id="scheduleToggleBtn2" class="btn-action" style="background: #ffff00;">
                            ⚠ ACTIVATE
                        </button>
                        <button onclick="saveSchedule(2)" class="btn-action" style="background: #00ccff;">
                            💾 SAVE_CFG
                        </button>
                    </div>
                    
                    <div class="info" id="scheduleInfo2">
                        <div>NO_ACTIVE_SCHEDULE</div>
                        <div id="currentTime2" class="time-display" style="margin-top:5px; color:#fff;"></div>
                    </div>
                </div>
            </div>
            
            <!-- PUMP 3 -->
            <div class="pump">
                <h2 class="pump-label-3">🌡️ AUX_PUMP_03</h2>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <span id="status3" class="status status-off">OFFLINE</span>
                </div>
                <button id="toggle3" class="toggle-btn btn-off" onclick="togglePump(3)">
                    SWITCH ON
                </button>
                
                <hr>

                <div style="margin-top: 15px;">
                    <span style="font-weight:bold; background:#000; color:#fff; padding:5px;">MODE_SELECT:</span><br><br>
                    <button id="btnManual3" class="mode-btn active" onclick="setMode(3, 'manual')">MANUAL</button>
                    <button id="btnSchedule3" class="mode-btn" onclick="setMode(3, 'schedule')">AUTO_SCHED</button>
                </div>
                
                <div style="margin-top: 15px;">
                    <span>CURRENT MODE: <strong id="mode3" style="background:#ffff00; padding:2px 5px; border:2px solid black;">MANUAL</strong></span>
                    <span id="scheduleStatus3" style="display:block; margin-top:5px; font-weight:bold;"></span>
                </div>

                <div id="scheduleContainer3" class="schedule-container">
                    <h3>⏰ SCHED_CONFIG PUMP 3</h3>
                    
                    <div class="schedule-section">
                        <h4>START_TIME</h4>
                        <div>
                            <label>HR:</label>
                            <input type="number" id="startHour3" class="schedule-input" value="9" min="0" max="23" style="width: 60px;">
                            <label>MN:</label>
                            <input type="number" id="startMinute3" class="schedule-input" value="0" min="0" max="59" style="width: 60px;">
                        </div>
                    </div>
                    
                    <div class="schedule-section">
                        <h4>ACTIVE_DAYS</h4>
                        <div class="day-selector">
                            <button class="day-btn active" onclick="toggleDay(3, 0)">MON</button>
                            <button class="day-btn active" onclick="toggleDay(3, 1)">TUE</button>
                            <button class="day-btn active" onclick="toggleDay(3, 2)">WED</button>
                            <button class="day-btn active" onclick="toggleDay(3, 3)">THU</button>
                            <button class="day-btn active" onclick="toggleDay(3, 4)">FRI</button>
                            <button class="day-btn active" onclick="toggleDay(3, 5)">SAT</button>
                            <button class="day-btn active" onclick="toggleDay(3, 6)">SUN</button>
                        </div>
                    </div>
                    
                    <div class="schedule-section">
                        <h4>DURATION</h4>
                        <div>
                            <input type="number" id="scheduleDuration3" class="schedule-input" value="30" min="1" max="999" style="width: 80px;">
                            <select id="scheduleUnit3" class="schedule-select">
                                <option value="detik">SEC</option>
                                <option value="menit">MIN</option>
                                <option value="jam">HR</option>
                            </select>
                        </div>
                    </div>
                    
                    <div style="margin-top: 20px;">
                        <button onclick="toggleSchedule(3)" id="scheduleToggleBtn3" class="btn-action" style="background: #ffff00;">
                            ⚠ ACTIVATE
                        </button>
                        <button onclick="saveSchedule(3)" class="btn-action" style="background: #00ccff;">
                            💾 SAVE_CFG
                        </button>
                    </div>
                    
                    <div class="info" id="scheduleInfo3">
                        <div>NO_ACTIVE_SCHEDULE</div>
                        <div id="currentTime3" class="time-display" style="margin-top:5px; color:#fff;"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
    let activeDays2 = [1, 1, 1, 1, 1, 1, 1];
    let activeDays3 = [1, 1, 1, 1, 1, 1, 1];
    
    async function togglePump(pump) {
        const currentState = await getPumpState(pump);
        const action = currentState ? 'off' : 'on';
        
        await fetch('/control?pump=' + pump + '&action=' + action);
        updateStatus();
    }
    
    async function getPumpState(pump) {
        const res = await fetch('/status');
        const data = await res.json();
        if (pump === 1) return data.pump1;
        if (pump === 2) return data.pump2;
        if (pump === 3) return data.pump3;
        return 0;
    }
    
    async function setMode(pump, mode) {
        await fetch('/mode?pump=' + pump + '&mode=' + mode);
        
        // Update UI untuk pump yang sesuai
        if (pump === 2) {
            document.getElementById('btnManual2').classList.remove('active');
            document.getElementById('btnSchedule2').classList.remove('active');
            document.getElementById('scheduleContainer2').classList.remove('active');
            
            if (mode === 'manual') {
                document.getElementById('btnManual2').classList.add('active');
            } else {
                document.getElementById('btnSchedule2').classList.add('active');
                document.getElementById('scheduleContainer2').classList.add('active');
            }
        } else if (pump === 3) {
            document.getElementById('btnManual3').classList.remove('active');
            document.getElementById('btnSchedule3').classList.remove('active');
            document.getElementById('scheduleContainer3').classList.remove('active');
            
            if (mode === 'manual') {
                document.getElementById('btnManual3').classList.add('active');
            } else {
                document.getElementById('btnSchedule3').classList.add('active');
                document.getElementById('scheduleContainer3').classList.add('active');
            }
        }
        
        updateStatus();
    }
    
    function toggleDay(pump, dayIndex) {
        if (pump === 2) {
            const btn = document.querySelectorAll('#scheduleContainer2 .day-btn')[dayIndex];
            activeDays2[dayIndex] = activeDays2[dayIndex] ? 0 : 1;
            btn.classList.toggle('active');
        } else if (pump === 3) {
            const btn = document.querySelectorAll('#scheduleContainer3 .day-btn')[dayIndex];
            activeDays3[dayIndex] = activeDays3[dayIndex] ? 0 : 1;
            btn.classList.toggle('active');
        }
    }
    
    async function toggleSchedule(pump) {
        const btnId = pump === 2 ? 'scheduleToggleBtn2' : 'scheduleToggleBtn3';
        const btn = document.getElementById(btnId);
        const isActive = btn.textContent.includes('ACTIVATE');
        
        if (isActive) {
            await fetch('/schedule_enable?pump=' + pump + '&enable=1');
        } else {
            await fetch('/schedule_enable?pump=' + pump + '&enable=0');
        }
        updateStatus();
    }
    
    async function saveSchedule(pump) {
        if (pump === 2) {
            const hour = document.getElementById('startHour2').value;
            const minute = document.getElementById('startMinute2').value;
            const duration = document.getElementById('scheduleDuration2').value;
            const unit = document.getElementById('scheduleUnit2').value;
            const days = activeDays2.join(',');
            
            await fetch('/schedule_set?pump=' + pump + '&hour=' + hour + '&minute=' + minute + 
                        '&duration=' + duration + '&unit=' + unit + '&days=' + days);
        } else if (pump === 3) {
            const hour = document.getElementById('startHour3').value;
            const minute = document.getElementById('startMinute3').value;
            const duration = document.getElementById('scheduleDuration3').value;
            const unit = document.getElementById('scheduleUnit3').value;
            const days = activeDays3.join(',');
            
            await fetch('/schedule_set?pump=' + pump + '&hour=' + hour + '&minute=' + minute + 
                        '&duration=' + duration + '&unit=' + unit + '&days=' + days);
        }
        
        updateStatus();
        alert('CONFIG_SAVED_PUMP_' + pump);
    }
    
    async function updateStatus() {
        const res = await fetch('/status');
        const data = await res.json();
        
        // Update pompa 1
        updatePumpUI(1, data.pump1);
        
        // Update pompa 2
        updatePumpUI(2, data.pump2);
        
        // Update pompa 3
        updatePumpUI(3, data.pump3);
        
        // Update schedule info untuk pump 2
        if (data.schedule_enabled !== undefined) {
            updateScheduleUI(2, data.schedule_enabled, data);
        }
        
        // Update schedule info untuk pump 3
        if (data.schedule_enabled_3 !== undefined) {
            updateScheduleUI(3, data.schedule_enabled_3, data);
        }
        
        // Update time display
        const now = new Date();
        if (document.getElementById('currentTime2')) {
            document.getElementById('currentTime2').textContent = `SYS_TIME: ${now.toLocaleTimeString('id-ID')}`;
        }
        if (document.getElementById('currentTime3')) {
            document.getElementById('currentTime3').textContent = `SYS_TIME: ${now.toLocaleTimeString('id-ID')}`;
        }
    }
    
    function updatePumpUI(pumpNum, state) {
        const toggleBtn = document.getElementById('toggle' + pumpNum);
        const status = document.getElementById('status' + pumpNum);
        
        if (state) {
            toggleBtn.textContent = 'SWITCH OFF';
            toggleBtn.className = 'toggle-btn btn-on';
            status.textContent = 'ONLINE';
            status.className = 'status status-on';
        } else {
            toggleBtn.textContent = 'SWITCH ON';
            toggleBtn.className = 'toggle-btn btn-off';
            status.textContent = 'OFFLINE';
            status.className = 'status status-off';
        }
    }
    
    function updateScheduleUI(pumpNum, enabled, data) {
        const toggleBtn = document.getElementById('scheduleToggleBtn' + pumpNum);
        const statusLabel = document.getElementById('scheduleStatus' + pumpNum);
        const modeLabel = document.getElementById('mode' + pumpNum);
        
        if (enabled) {
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
        
        // Update mode display
        if (pumpNum === 2) {
            modeLabel.textContent = data.mode2 ? data.mode2.toUpperCase() : 'MANUAL';
        } else if (pumpNum === 3) {
            modeLabel.textContent = data.mode3 ? data.mode3.toUpperCase() : 'MANUAL';
        }
        
        // Update schedule details
        const infoElement = document.getElementById('scheduleInfo' + pumpNum);
        if (infoElement) {
            let scheduleData;
            if (pumpNum === 2) {
                scheduleData = {
                    hour: data.schedule_start_hour,
                    minute: data.schedule_start_minute,
                    duration: data.schedule_duration,
                    unit: data.schedule_unit,
                    days: data.schedule_days
                };
            } else {
                scheduleData = {
                    hour: data.schedule_start_hour_3,
                    minute: data.schedule_start_minute_3,
                    duration: data.schedule_duration_3,
                    unit: data.schedule_unit_3,
                    days: data.schedule_days_3
                };
            }
            
            const dayNames = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
            let activeDayNames = [];
            if (scheduleData.days) {
                for (let i = 0; i < scheduleData.days.length; i++) {
                    if (scheduleData.days[i] === 1) {
                        activeDayNames.push(dayNames[i]);
                    }
                }
            }
            
            const scheduleText = `${scheduleData.hour.toString().padStart(2, '0')}:${scheduleData.minute.toString().padStart(2, '0')} - ${scheduleData.duration} ${scheduleData.unit.toUpperCase()}`;
            const daysText = activeDayNames.join(', ');
            
            let infoHtml = `
                <div>TARGET: <strong>${scheduleText}</strong></div>
                <div>DAYS: [ ${daysText} ]</div>
                <div>STATE: ${enabled ? 'RUNNING' : 'STOPPED'}</div>
            `;
            
            infoElement.innerHTML = infoHtml;
        }
    }
    
    setInterval(updateStatus, 2000);
    updateStatus();
    </script>
</body>
</html>"""

# ===================== SERVER =====================
def handle_request(conn, request):
    global pump1_state, pump2_state, pump3_state, pump2_mode, pump3_mode
    global schedule_enabled, schedule_enabled_3, schedule_start_hour, schedule_start_hour_3
    global schedule_start_minute, schedule_start_minute_3, schedule_duration, schedule_duration_3
    global schedule_unit, schedule_unit_3, schedule_days, schedule_days_3
    global schedule_executed, schedule_executed_3

    if "/ " in request:
        conn.send(get_html())

    elif "/status" in request:
        data = {
            "pump1": pump1_state,
            "pump2": pump2_state,
            "pump3": pump3_state,
            "mode2": pump2_mode,
            "mode3": pump3_mode,
            "schedule_enabled": schedule_enabled,
            "schedule_enabled_3": schedule_enabled_3,
            "schedule_start_hour": schedule_start_hour,
            "schedule_start_hour_3": schedule_start_hour_3,
            "schedule_start_minute": schedule_start_minute,
            "schedule_start_minute_3": schedule_start_minute_3,
            "schedule_duration": schedule_duration,
            "schedule_duration_3": schedule_duration_3,
            "schedule_unit": schedule_unit,
            "schedule_unit_3": schedule_unit_3,
            "schedule_days": schedule_days,
            "schedule_days_3": schedule_days_3
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
        elif "pump=2" in request:
            if "action=on" in request:
                pump2_state = 1
                control_pump2(1)
            elif "action=off" in request:
                pump2_state = 0
                control_pump2(0)
                schedule_executed = False

        # ===== PUMP 3 =====
        elif "pump=3" in request:
            if "action=on" in request:
                pump3_state = 1
                control_pump3(1)
            elif "action=off" in request:
                pump3_state = 0
                control_pump3(0)
                schedule_executed_3 = False

        conn.send("HTTP/1.1 200 OK\r\n\r\n")

    elif "/mode" in request:
        q = request.split("?")[1].split(" ")[0]
        p = dict(x.split("=") for x in q.split("&"))
        
        pump_num = int(p.get("pump", 2))
        mode = p.get("mode", "manual")
        
        if pump_num == 2:
            pump2_mode = mode
            if mode == "manual":
                pump2_state = 0
                control_pump2(0)
                schedule_executed = False
        elif pump_num == 3:
            pump3_mode = mode
            if mode == "manual":
                pump3_state = 0
                control_pump3(0)
                schedule_executed_3 = False
                
        conn.send("HTTP/1.1 200 OK\r\n\r\n")

    elif "/schedule_enable" in request:
        q = request.split("?")[1].split(" ")[0]
        p = dict(x.split("=") for x in q.split("&"))
        
        pump_num = int(p.get("pump", 2))
        enable = p.get("enable") == "1"
        
        if pump_num == 2:
            schedule_enabled = enable
        elif pump_num == 3:
            schedule_enabled_3 = enable
            
        conn.send("HTTP/1.1 200 OK\r\n\r\n")

    elif "/schedule_set" in request:
        try:
            q = request.split("?")[1].split(" ")[0]
            p = dict(x.split("=") for x in q.split("&"))
            
            pump_num = int(p.get("pump", 2))
            
            if pump_num == 2:
                schedule_start_hour = int(p["hour"])
                schedule_start_minute = int(p["minute"])
                schedule_duration = int(p["duration"])
                schedule_unit = p["unit"]
                schedule_days = [int(x) for x in p["days"].split(",")]
                schedule_executed = False
                print("SCHEDULE PUMP 2 UPDATED")
                
            elif pump_num == 3:
                schedule_start_hour_3 = int(p["hour"])
                schedule_start_minute_3 = int(p["minute"])
                schedule_duration_3 = int(p["duration"])
                schedule_unit_3 = p["unit"]
                schedule_days_3 = [int(x) for x in p["days"].split(",")]
                schedule_executed_3 = False
                print("SCHEDULE PUMP 3 UPDATED")

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

