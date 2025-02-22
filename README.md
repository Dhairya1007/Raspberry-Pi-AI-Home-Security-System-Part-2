# Raspberry-Pi-AI-Home-Security-System-Part-2

Official code repository for the Circuit Cellar Article: "Create an AI-Driven Smart Home Security System (Part 2): Adding Person Detection and Alerts"

## Repository Structure

- `home_security_system_core.py`: This script sets up the core functionality of the home security system, including person detection and alerting via email and server updates.
- `stream_security_video.py`: This script sets up a Flask server to stream video from the security camera.
- `templates/index.html`: The HTML template for the video streaming home page.
- `README.md`: This file.

## Setup Instructions

### 1. Activate the Virtual Environment and Clone Article Repository

Activate the virtual environment created for the hailo rpi5 examples repo in the last article using the following commands:

```sh
cd <location-of-examples-repo>/hailo-rpi5-examples
source setup_env.sh   // To start the virtual environment.
```

Next, just clone this repository and get into it's home directory with the following command:

```sh
git clone https://github.com/Dhairya1007/Raspberry-Pi-AI-Home-Security-System-Part-2.git && cd Raspberry-Pi-AI-Home-Security-System-Part-2
```

### 2. Start the Streaming Server

Start the streaming server once in the environment with the following command:

```sh
python stream_security_video.py
```

### 3. Start the Home Security System

Finally, start the home security system with the following command:

```sh
python home_security_system_core.py --input rpi
```
