import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst
import cv2
import hailo
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests
from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.detection_pipeline import GStreamerDetectionApp

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntruderDetectionCallback(app_callback_class):
    def __init__(self):
        super().__init__()
        # Email configuration
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = "sender@email.com"
        self.sender_password = "sender_app_password"
        self.receiver_email = "receiver@email.com"

        # Detection parameters
        self.last_alert_time = datetime.min
        self.alert_cooldown = 300  # 5 minutes between alerts
        self.confidence_threshold = 0.6
        self.location_name = "Main Entrance"

        # Server configuration
        self.server_url = "http://localhost:8080"

    def format_email_body(self, detections, current_time):
        """Create a formal, structured email body"""
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="padding: 20px;">
                <h2 style="color: #FF0000;">SECURITY ALERT: Intruder Detection</h2>
                
                <div style="background-color: #f5f5f5; padding: 15px; margin: 10px 0;">
                    <h3>Incident Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Location:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{self.location_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Date:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{current_time.strftime("%B %d, %Y")}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Time:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{current_time.strftime("%H:%M:%S %Z")}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Total Persons Detected:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #ddd;">{len(detections)}</td>
                        </tr>
                    </table>
                </div>

                <div style="background-color: #f5f5f5; padding: 15px; margin: 10px 0;">
                    <h3>Detection Summary</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background-color: #e0e0e0;">
                            <th style="padding: 8px; border: 1px solid #ddd;">Detection ID</th>
                            <th style="padding: 8px; border: 1px solid #ddd;">Confidence Score</th>
                        </tr>
                        {self._format_detection_table(detections)}
                    </table>
                </div>

                <div style="margin-top: 20px; font-size: 12px; color: #666;">
                    <p>This is an automated security alert. Please do not reply to this email.</p>
                    <p>If this alert requires immediate attention, please contact security personnel.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_body

    def _format_detection_table(self, detections):
        return "".join(
            [
                f'<tr><td style="padding: 8px; border: 1px solid #ddd;">{det["id"]}</td>'
                f'<td style="padding: 8px; border: 1px solid #ddd;">{det["confidence"]:.2f}</td></tr>'
                for det in detections
            ]
        )

    def send_alert(self, detections):
        current_time = datetime.now()

        if (current_time - self.last_alert_time).total_seconds() < self.alert_cooldown:
            return

        try:
            # Send email alert
            msg = MIMEMultipart()
            msg["Subject"] = (
                f"SECURITY ALERT - Intruder Detection at {self.location_name}"
            )
            msg["From"] = self.sender_email
            msg["To"] = self.receiver_email

            html_body = self.format_email_body(detections, current_time)
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            # Send detection data to web server
            alert_data = {
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "location": self.location_name,
                "detections": detections,
                "total_persons": len(detections),
            }

            try:
                requests.post(f"{self.server_url}/update_detection", json=alert_data)
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to send detection data to server: {str(e)}")

            self.last_alert_time = current_time
            logger.info("Alert email sent and detection data updated")

        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")


def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    format, width, height = get_caps_from_pad(pad)
    frame = None
    if user_data.use_frame and format and width and height:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    detection_info = []
    for detection in detections:
        confidence = detection.get_confidence()
        if (
            detection.get_label() == "person"
            and confidence > user_data.confidence_threshold
        ):
            bbox = detection.get_bbox()
            track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
            track_id = track[0].get_id() if track else 0

            detection_info.append({"id": track_id, "confidence": confidence})

            if frame is not None:
                x1, y1, x2, y2 = map(
                    int,
                    [
                        bbox.xmin * width,
                        bbox.ymin * height,
                        bbox.xmax * width,
                        bbox.ymax * height,
                    ],
                )
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"ID: {track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    2,
                )

    if detection_info:
        user_data.send_alert(frame, detection_info)

    if frame is not None:
        user_data.set_frame(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    return Gst.PadProbeReturn.OK


if __name__ == "__main__":
    user_data = IntruderDetectionCallback()
    app = GStreamerDetectionApp(app_callback, user_data)
    logger.info("Starting Intruder Detection System")
    app.run()
