# RetailIQ Production Runbook & Operations Guide

This guide covers real-world setup, live camera connection, zone calibration, and troubleshooting for the **RetailIQ** Edge Retail Intelligence System.

---

## 1. Quick Start & Startup Validation

### Running Backend Locally
```bash
# Activate environment & install requirements
pip install -r backend/requirements.txt

# Run backend API server on port 8000
python backend/main.py
```

### Running Frontend
```bash
cd frontend
npm install
npm run dev
# Dashboard accessible at http://localhost:3000
```

---

## 2. Connecting Real Mobile IP Cameras & Hardware

### Option A: Android / iOS Phone (IP Webcam)
1. Install **IP Webcam** (by Pavel Khlebovich) from Google Play Store or **DroidCam**.
2. Open the app, scroll to the bottom, and tap **"Start server"**.
3. Note the displayed IPv4 address (e.g. `http://192.168.1.14:8080`).
4. In the RetailIQ Dashboard, click **"Camera Source"** on the navigation header.
5. Enter the stream URL: `http://<phone-ip>:8080/video` (or click the **Android IP Webcam** preset).
6. Set orientation rotation if needed (e.g., `0°`, `90°`, `180°`, `270°`).
7. Click **"Connect & Apply Camera"**. The stream immediately begins live edge inference.

### Option B: USB Webcam / DirectShow Sensor
1. Connect USB webcam.
2. In the Camera Source modal, select **"USB / Built-in Webcam"** (Device index `0` or `1`).
3. Click **"Connect & Apply Camera"**.

### Option C: RTSP / Security IP Camera
1. Enter your RTSP URL (e.g., `rtsp://admin:password@192.168.1.50:554/stream1`).
2. Click **"Connect & Apply Camera"**.

---

## 3. Calibrating Zones & Baseline Reference Images

1. Go to the **"Zone Map & Live Video"** tab and click **"Calibrate Zones"** (or click the calibration button on the feed).
2. Point the camera at the full shelf when inventory is 100% restocked.
3. On each shelf zone, click **"Capture Full-Shelf Baseline"**.
4. The system stores the high-resolution crop in `backend/data/baselines/` and uses it for dual-signal SSIM structural differencing.
5. Click **"Save Zone Calibration"**.

---

## 4. Onboarding New SKUs (Few-Shot Visual Embedding)

1. Go to the **"Few-Shot SKU Onboarding"** tab.
2. Enter the SKU ID (e.g., `SKU-DRINK-01`), Product Name, Category, and Price.
3. Upload 3 to 10 sample photos or webcam crops showing the product from different angles.
4. Click **"Onboard SKU to Edge Gallery"**.
5. The embedding encoder calculates the 128-dimensional unit vector and persists it immediately in SQLite. It is queryable within milliseconds.

---

## 4.5 Detection & Pipeline Architecture
- **Detector**: YOLOv8n ONNX model (`yolov8n.onnx`) is loaded by default.
- **Fallback**: Automatically falls back to Haar Cascade if the YOLO model is missing.
- **Buffer & Resolution**: The pipeline uses a fixed ring buffer (size 1) and processes video at 640x360 resolution (with 640x360 preview resolution) to maintain low latency without overloading edge CPU/RAM.

## 5. Health & Diagnostic Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health/live` | `GET` | Lightweight liveness probe (200 if alive). |
| `/health/ready` | `GET` | Readiness probe (checks DB, camera, pipeline). Returns 503 if degraded. |
| `/health` | `GET` | Full telemetry diagnostics (CPU%, RAM MB, FPS, latencies). |
| `/video/status` | `GET` | Camera capture FPS, connection state, reconnect retries, downtime. |
| `/video/feed` | `GET` | Real-time MJPEG live stream with privacy blur and detection overlays. |

---

## 6. Docker Production Deployment

```bash
# Build and run containers
docker-compose up --build -d

# Verify container health
docker-compose ps
```

---

## 7. Troubleshooting & Recovery

| Issue | Cause | Solution |
|---|---|---|
| **"Camera Reconnecting..." Banner** | Phone screen slept or IP changed. | Ensure phone IP Webcam is running, keep screen on, and verify IP in Camera Source modal. |
| **False Stock-Out Alerts** | Sudden lighting drop or blockage. | Ensure baseline image is captured via Calibration modal. System automatically triggers occlusion suppression if blockage occurs. |
| **High Queue Wait Time Warning** | Shoppers standing in queue line. | Staff acknowledge alert on dashboard to silence buzzer/LED cooldown. |
