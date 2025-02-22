from flask import Flask, Response, render_template, request, jsonify
import cv2
from datetime import datetime
import json

app = Flask(__name__)

# Global variable to store the latest detection data
latest_detection = {
    "timestamp": None,
    "location": None,
    "detections": [],
    "total_persons": 0
}

def generate_frames():
    cap = cv2.VideoCapture("udp://127.0.0.1:5010", cv2.CAP_FFMPEG)
    while True:
        success, frame = cap.read()
        if not success:
            print("Unable to read frame.")
            break
        else:
            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/update_detection", methods=['POST'])
def update_detection():
    global latest_detection
    data = request.json
    latest_detection = data
    return jsonify({"status": "success"})

@app.route("/get_detection")
def get_detection():
    return jsonify(latest_detection)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
