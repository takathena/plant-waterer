# dashboard_iot.py
# MicroPython: Dashboard Dark + Real-time chart + JSON API + Actions
import network
import socket
from machine import Pin, ADC
from time import sleep
import dht
import ujson as json	

# === KONFIG WIFI ===
SSID = "gendis"
PASSWORD = "sipwes00"

# === PERANGKAT ===
soil = ADC(Pin(34))
soil.atten(ADC.ATTN_11DB)

relay = Pin(26, Pin.OUT)
relay.value(1)  # relay OFF (active LOW)

dht_sensor = dht.DHT11(Pin(14))

# === KALIBRASI ===
SOIL_DRY = 3500
SOIL_WET = 1500

# === MODE ===
mode_auto = True
manual_state = 1  # 0 = on, 1 = off

# === FUNGSI BACA ===
def read_soil_percent():
    val = soil.read()
    try:
        percent = int((SOIL_DRY - val) * 100 / (SOIL_DRY - SOIL_WET))
    except ZeroDivisionError:
        percent = 0
    percent = max(0, min(100, percent))
    return percent, val

def read_dht():
    try:
        dht_sensor.measure()
        t = dht_sensor.temperature()
        h = dht_sensor.humidity()
        return t, h
    except Exception as e:
        return None, None

# === WIFI CONNECT ===
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

# === HTML DASHBOARD (dark, cards, canvas, AJAX) ===
def dashboard_html():
    return """HTTP/1.1 200 OK
Content-Type: text/html
Connection: close

<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IoT Dashboard</title>
<style>
:root{
  --bg:#0f1115; --card:#111318; --muted:#9aa3b2; --accent:#39c0ff;
}
body{background:var(--bg); color:#e6eef6; font-family:Inter,Arial,Helvetica,sans-serif; margin:0; padding:18px; -webkit-font-smoothing:antialiased;}
.container{max-width:960px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;}
.header{grid-column:1/-1;display:flex;align-items:center;justify-content:space-between;}
.title{font-size:18px;font-weight:600;}
.controls button{background:transparent;border:1px solid rgba(255,255,255,0.06);color:var(--accent);padding:8px 10px;border-radius:8px;margin-left:8px;cursor:pointer;}
.card{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(0,0,0,0.02));padding:14px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,0.6);border:1px solid rgba(255,255,255,0.02);}
.label{font-size:12px;color:var(--muted); margin-bottom:6px;}
.value{font-size:26px;font-weight:700;}
.small{font-size:13px;color:var(--muted); margin-top:6px;}
.row{display:flex;gap:8px;align-items:center;justify-content:space-between;}
.canvas-wrap{grid-column:1/-1; padding:12px;}
canvas{width:100%;height:160px;background:transparent;border-radius:8px;}
.footer{grid-column:1/-1;color:var(--muted);font-size:12px;text-align:center;padding-top:8px;}
.toggle{padding:8px 12px;border-radius:8px;border:none;cursor:pointer;background:var(--accent);color:#061021;font-weight:600;}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="title">Penyiram Otomatis — Dashboard</div>
    <div class="controls">
      <button id="btnAuto" class="toggle">AUTO</button>
      <button id="btnManual" class="toggle" style="display:none;">MANUAL</button>
      <button id="btnPumpOn">Pompa OFF</button>
      <button id="btnPumpOff">Pompa ON</button>
    </div>
  </div>

  <div class="card">
    <div class="label">Kelembapan Tanah</div>
    <div class="value" id="soilPercent">--%</div>
    <div class="small" id="soilRaw">ADC: --</div>
  </div>

  <div class="card">
    <div class="label">Suhu Ruangan</div>
    <div class="value" id="temp">--°C</div>
    <div class="small" id="hum">Kelembapan Udara: --%</div>
  </div>

  <div class="card">
    <div class="label">Pompa</div>
    <div class="value" id="pump">--</div>
    <div class="small" id="mode">Mode: --</div>
  </div>

  <div class="canvas-wrap card">
    <div class="label">Grafik Kelembapan Tanah (Terakhir)</div>
    <canvas id="chart" width="800" height="160"></canvas>
  </div>

  <div class="footer">Data refresh setiap 1 detik · API: <code>/data</code> · Actions: <code>/action?mode=auto</code>, <code>/action?pump=on</code></div>
</div>

<script>
const UPDATE_MS = 1000;
const MAX_POINTS = 40;
let soilData = [];

async function fetchData(){
  try{
    const r = await fetch('/data');
    if(!r.ok) return;
    const j = await r.json();
    // update UI
    document.getElementById('soilPercent').textContent = j.soil_percent + '%';
    document.getElementById('soilRaw').textContent = 'ADC: ' + j.soil_raw;
    document.getElementById('temp').textContent = (j.temp === null ? '--' : j.temp + '°C');
    document.getElementById('hum').textContent = 'Kelembapan Udara: ' + (j.hum === null ? '--' : j.hum + '%');
    document.getElementById('pump').textContent = j.pump ? 'ON' : 'OFF';
    document.getElementById('mode').textContent = 'Mode: ' + (j.mode ? 'AUTO' : 'MANUAL');

    // push to soil graph
    const t = Date.now();
    soilData.push({x:t, y:j.soil_percent});
    if(soilData.length > MAX_POINTS) soilData.shift();
    drawChart();
  }catch(e){
    console.log('fetchData error', e);
  }
}

function drawChart(){
  const c = document.getElementById('chart');
  const ctx = c.getContext('2d');
  // clear
  ctx.clearRect(0,0,c.width,c.height);
  // background grid
  ctx.fillStyle = '#0f1115';
  ctx.fillRect(0,0,c.width,c.height);
  ctx.strokeStyle = 'rgba(255,255,255,0.03)';
  ctx.lineWidth = 1;
  for(let i=0;i<5;i++){
    const y = (i/4)*c.height;
    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(c.width,y); ctx.stroke();
  }
  if(soilData.length < 2) return;
  // compute bounds
  const ys = soilData.map(p=>p.y);
  const ymin = 0;
  const ymax = 100;
  const xmin = soilData[0].x;
  const xmax = soilData[soilData.length-1].x;
  // draw line
  ctx.strokeStyle = '#39c0ff';
  ctx.lineWidth = 2;
  ctx.beginPath();
  for(let i=0;i<soilData.length;i++){
    const p = soilData[i];
    const px = c.width * ((p.x - xmin) / (xmax - xmin || 1));
    const py = c.height - ( (p.y - ymin) / (ymax - ymin) * c.height );
    if(i===0) ctx.moveTo(px,py); else ctx.lineTo(px,py);
  }
  ctx.stroke();
  // draw dots
  ctx.fillStyle = '#39c0ff';
  for(let p of soilData){
    const px = c.width * ((p.x - xmin) / (xmax - xmin || 1));
    const py = c.height - ( (p.y - ymin) / (ymax - ymin) * c.height );
    ctx.beginPath(); ctx.arc(px,py,2,0,2*Math.PI); ctx.fill();
  }
}

document.getElementById('btnPumpOn').addEventListener('click', ()=>fetch('/action?pump=on'));
document.getElementById('btnPumpOff').addEventListener('click', ()=>fetch('/action?pump=off'));
document.getElementById('btnAuto').addEventListener('click', async ()=>{
  await fetch('/action?mode=auto');
  document.getElementById('btnAuto').style.display='none';
  document.getElementById('btnManual').style.display='inline-block';
});
document.getElementById('btnManual').addEventListener('click', async ()=>{
  await fetch('/action?mode=manual');
  document.getElementById('btnManual').style.display='none';
  document.getElementById('btnAuto').style.display='inline-block';
});

// initial toggle visibility based on server value (fetch once)
(async function init(){
  await fetchData();
  setInterval(fetchData, UPDATE_MS);
})();
</script>
</body>
</html>
"""

# === SERVER ===
def send_json(conn, data):
    payload = json.dumps(data)
    conn.send("HTTP/1.1 200 OK\nContent-Type: application/json\nConnection: close\n\n")
    conn.sendall(payload)

def send_html(conn, html_bytes):
    conn.send(html_bytes)

def handle_request(req):
    global mode_auto, manual_state
    # minimal parsing: find path
    try:
        first_line = req.split('\r\n')[0]
    except:
        first_line = ''
    # e.g. GET /path?x=1 HTTP/1.1
    parts = first_line.split(' ')
    path = '/'
    if len(parts) >= 2:
        path = parts[1]
    return path

# start
wlan = connect_wifi()
addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
s = socket.socket()
s.setsockopt(0x1002, 0x0001, 1)  # SO_REUSEADDR
s.bind(addr)
s.listen(1)
s.settimeout(0.5)
print("Server ready at http://%s" % wlan.ifconfig()[0])

while True:
    # update sensor readings for loop logic
    soil_percent, soil_raw = read_soil_percent()
    temp, hum = read_dht()
    # control auto (note: logic preserved but inverted? Keep same as earlier: percent>40 -> relay on)
    if mode_auto:
        relay.value(0 if soil_percent > 40 else 1)
    else:
        relay.value(manual_state)

    try:
        conn, addr = s.accept()
        # read request
        req = conn.recv(1024).decode('utf-8')
        path = handle_request(req)
        print('REQ', addr, path)

        # ROUTING
        if path.startswith('/data'):
            data = {
                'soil_percent': soil_percent,
                'soil_raw': soil_raw,
                'temp': temp,
                'hum': hum,
                'pump': (relay.value() == 0),
                'mode': mode_auto
            }
            send_json(conn, data)
            conn.close()

        elif path.startswith('/action'):
            # parse query simple
            # /action?mode=auto or /action?pump=on
            if 'mode=auto' in path:
                mode_auto = True
            elif 'mode=manual' in path:
                mode_auto = False
            elif 'pump=on' in path:
                manual_state = 0
                relay.value(0)
            elif 'pump=off' in path:
                manual_state = 1
                relay.value(1)
            # Respond 204 No Content minimal
            conn.send("HTTP/1.1 204 No Content\nConnection: close\n\n")
            conn.close()

        else:
            # serve dashboard
            html = dashboard_html()
            conn.send(html)
            conn.close()

    except OSError:
        # timeout or other socket error - continue loop
        pass
    except Exception as e:
        print('Server error', e)
    sleep(0.2)
