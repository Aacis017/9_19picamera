from flask import Flask, Response, render_template, request, jsonify
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
from libcamera import Transform
import io
import os
import json
import time
import threading

# Platform-specific imports


import serial
import numpy as np

app = Flask(__name__)

# -------------------------
# Arduino serial setup
# -------------------------
try:
    if os.name == "nt":
        arduino = serial.Serial("COM1", 9600, timeout=1)
    else:
        arduino = serial.Serial("/dev/ttyACM0", 9600, timeout=1)
    time.sleep(2)
    arduino.reset_input_buffer()
    print("✅ Arduino connected")
except Exception as e:
    print("❌ Arduino connection failed:", e)
    arduino = None

# -------------------------
# Camera setup
# -------------------------

# Initialize camera with 180° rotation
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (320, 240)},  # smaller resolution for faster Pi Zero
    transform=Transform(hflip=1, vflip=1)
)
picam2.configure(config)
picam2.start()

def generate_frames():
    while True:
        stream = io.BytesIO()
        picam2.capture_file(stream, format="jpeg")  # fast JPEG capture
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + stream.getvalue() + b'\r\n')


# -------------------------
# Flask routes
# -------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/filo')
def filo():
    return render_template('filo.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Joystick control
@app.route('/joystick', methods=['POST'])
def joystick():
    try:
        data = request.get_json()
        print("🎮 Joystick data:", data)
        if arduino:
            command = json.dumps(data) + "\n"
            arduino.write(command.encode("utf-8"))
        return jsonify({"status": "ok", "sent": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Blockly program upload
@app.route('/run', methods=['POST'])
def run_program():
    try:
        program = request.json
        print("📦 Blockly program:", program)
        if arduino:
            command = json.dumps(program) + "\n"
            arduino.write(command.encode("utf-8"))
        return jsonify({"status": "ok", "sent": program})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------------
# Run Flask app
# -------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
