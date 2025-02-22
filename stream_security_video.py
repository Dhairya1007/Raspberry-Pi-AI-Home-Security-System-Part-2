from flask import Flask, Response, render_template
import cv2

# Initialize the Flask app
app = Flask(__name__)


def generate_frames():
    # Capture video from the UDP Sink configured in the GStreamer pipeline
    cap = cv2.VideoCapture("udp://127.0.0.1:5010", cv2.CAP_FFMPEG)

    # Stream indefinitely
    while True:
        success, frame = cap.read()
        if not success:
            print("Unable to read frame.")
            break
        else:
            # Encode the frame in JPEG format
            _, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()  # Convert the frame to bytes
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )  # Yield the frame in the byte format


@app.route("/")
def index():
    """Video streaming home page."""
    return render_template("index.html")


@app.route("/video_feed")
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    # Run the Flask app
    app.run(host="0.0.0.0", port=8080)
