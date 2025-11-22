from machine import Pin, ADC
import dht
import time

# ====================================
# Konfigurasi Pin
# ====================================
soil_pin = ADC(Pin(34))
soil_pin.atten(ADC.ATTN_11DB)      # 0–3.3V

relay_pin = Pin(26, Pin.OUT)
relay_active_level = 0             # Relay aktif LOW

dht_pin = dht.DHT11(Pin(14))

# ====================================
# Kalibrasi Soil Moisture
# GANTI nilai ini berdasarkan pengukuranmu
# ====================================
SOIL_WET = 1200     # ADC saat tanah basah
SOIL_DRY = 3300     # ADC saat tanah kering

# Threshold persen untuk penyiraman
MOISTURE_THRESHOLD_PERCENT = 40    # <40% → kering

# ====================================
# Fungsi kontrol pompa
# ====================================
def pump_on():
    relay_pin.value(relay_active_level)

def pump_off():
    relay_pin.value(1 - relay_active_level)

pump_off()

# ====================================
# Konversi ADC → Persen
# ====================================
def adc_to_percent(adc_value):
    # Batasi agar tidak keluar rentang
    if adc_value < SOIL_WET:
        return 100
    if adc_value > SOIL_DRY:
        return 0
    
    percent = (SOIL_DRY - adc_value) * 100 / (SOIL_DRY - SOIL_WET)
    return int(percent)

# ====================================
# Loop utama
# ====================================
while True:
    soil_adc = soil_pin.read()
    soil_percent = adc_to_percent(soil_adc)

    # Baca suhu
    try:
        dht_pin.measure()
        temperature = dht_pin.temperature()
    except:
        temperature = None

    print("Soil:", soil_adc, "|", soil_percent, "% | Temperatur:", temperature)

    # Logika penyiraman
    if soil_percent > MOISTURE_THRESHOLD_PERCENT:
        print("Tanah Lembap → Pompa OFF")
        pump_on()
    else:
        print("Tanah Kering → Pompa ON")
        pump_off()

    time.sleep(2)

