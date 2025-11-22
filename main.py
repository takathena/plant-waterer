from machine import Pin, ADC
import dht
import time

# ================================
# Konfigurasi Pin
# ================================
soil_pin = ADC(Pin(34))          # Soil moisture (ADC)
soil_pin.atten(ADC.ATTN_11DB)    # Range 0–3.3V

relay_pin = Pin(26, Pin.OUT)     # Relay untuk pompa
relay_active_level = 0           # Relay aktif LOW (0 = ON)

dht_pin = dht.DHT11(Pin(14))     # Sensor DHT11 untuk suhu

# ================================
# Ambang batas kelembapan tanah
# ================================
# Semakin tinggi nilai ADC → semakin kering
SOIL_THRESHOLD = 2500            # Sesuaikan berdasarkan kalibrasi

# ================================
# Fungsi kontrol pompa
# ================================
def pump_on():
    relay_pin.value(relay_active_level)

def pump_off():
    relay_pin.value(1 - relay_active_level)

# Mulai dengan pompa mati
pump_off()

# ================================
# Loop utama
# ================================
while True:
    # Baca soil moisture (ADC)
    soil_value = soil_pin.read()

    # Baca DHT11
    try:
        dht_pin.measure()
        temperature = dht_pin.temperature()
    except:
        temperature = None

    # Log ke serial
    print("Soil ADC:", soil_value, "| Temperature:", temperature)

    # ================================
    # Logika penyiraman otomatis
    # ================================
    # Sesuai permintaan:
    # LEMBAB = soil_value < threshold → pompa MENYALA
    # KERING = soil_value >= threshold → pompa MATI

    if soil_value < SOIL_THRESHOLD:
        print("Tanah Lembap → Pompa ON")
        pump_on()
    else:
        print("Tanah Kering → Pompa OFF")
        pump_off()

    time.sleep(2)
