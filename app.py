import os
from dotenv import load_dotenv
from flask import Flask, jsonify
import tinytuya
import threading

app = Flask(__name__)
load_dotenv()

DEVICE_ID = os.getenv('device_id')
LOCAL_KEY = os.getenv('local_key')
IP = os.getenv('device_ip')
VERSION = 3.3

device_lock = threading.Lock()
device_info = {"ip": IP, "product_key": "--", "device_id": DEVICE_ID}

def get_device():
    target_ip = device_info.get("ip") or IP 
    d = tinytuya.Device(
        dev_id=DEVICE_ID,
        address=target_ip,
        local_key=LOCAL_KEY,
        version=VERSION
    )
    d.set_socketTimeout(3)
    return d

def send_command(dps_dict):
    try:
        with device_lock:
            d = get_device()
            for dp, val in dps_dict.items():
                d.set_value(dp, val)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def scan_device_info():
    global device_info
    try:
        print("Scansione rete per informazioni dispositivo...")
        devices = tinytuya.deviceScan(verbose=False)
        for ip, info in devices.items():
            if info.get("gwId") == DEVICE_ID or info.get("id") == DEVICE_ID:
                device_info = {
                    "ip": info.get("ip", IP),
                    "product_key": info.get("productKey", "--"),
                    "device_id": info.get("gwId", DEVICE_ID),
                }
                print(f"Device Found: {device_info}")
                return
        print("Device not found in scan")
    except Exception as e:
        print(f"Scan error: {e}")

threading.Thread(target=scan_device_info, daemon=True).start()

@app.route("/")
def index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.route("/status")
def status():
    try:
        with device_lock:
            d = get_device()
            data = d.status()
        dps = data.get("dps", {})
        return jsonify({
            "ok":          True,
            "battery":     dps.get("39", 0),
            "status":      str(dps.get("38", "0")),
            "mode":        dps.get("25", "NONE"),
            "fan":         dps.get("27", "normal"),
            "working":     dps.get("33", False),
            "sweep_type":  dps.get("49", "sweep"),
            "fault":       dps.get("11", 0),
            "area":        round(dps.get("41", 0) / 10, 1),
            "time":        dps.get("42", 0),
            "filter":      dps.get("45", 0),
            "edge_brush":  dps.get("47", 0),
            "main_brush":  dps.get("48", 0),
            "sensor":      dps.get("44", 0),
            "lights":      dps.get("51", False),
            "serial":      dps.get("58", "--"),
            "water":       dps.get("60", "medium"),
            "ip":          device_info["ip"],
            "product_key": device_info["product_key"],
            "device_id":   device_info["device_id"],
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/move/<direction>")
def move(direction):
    if direction not in ["forward", "backward", "turnleft", "turnright", "stop"]:
        return jsonify({"ok": False})
    return jsonify({"ok": send_command({26: direction})})

@app.route("/mode/<mode>")
def mode(mode):
    if mode not in ["smart", "wallfollow", "sprial", "mop", "chargego"]:
        return jsonify({"ok": False})
    return jsonify({"ok": send_command({25: mode})})

@app.route("/pause")
def pause():
    return jsonify({"ok": send_command({33: False})})
    
@app.route("/reboot")
def reboot():
    return jsonify({"ok": send_command({52: True})})

@app.route("/fan/<level>")
def fan(level):
    if level not in ["strong", "normal", "ECO"]:
        return jsonify({"ok": False})
    return jsonify({"ok": send_command({27: level})})

@app.route("/lights/<state>")
def lights(state):
    return jsonify({"ok": send_command({51: state == "on"})})

@app.route("/beep")
def beep():
    return jsonify({"ok": send_command({50: True})})

@app.route("/water/<level>")
def water(level):
    if level not in ["small", "medium", "Big"]:
        return jsonify({"ok": False})
    return jsonify({"ok": send_command({60: level})})

@app.route("/reset/<part>")
def reset(part):
    mapping = {"sensor": 54, "filter": 55, "edge_brush": 56, "main_brush": 57}
    if part not in mapping:
        return jsonify({"ok": False})
    return jsonify({"ok": send_command({mapping[part]: True})})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
