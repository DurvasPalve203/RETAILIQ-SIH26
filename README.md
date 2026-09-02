# RetailIQ — Edge-Native Retail Computer Vision & Shelf Intelligence

**RetailIQ** is a 100% offline edge computer vision and shelf intelligence platform designed for single-board computers (Jetson / Raspberry Pi 5 / Edge PC). It turns continuous camera streams into actionable floor tasks, predictive stock-out alerts, dwell & footfall analytics, few-shot SKU onboarding, and automated active learning triage.

---

## Technical Specification & Module Architecture

| Module | Component | Implementation Highlights |
| :--- | :--- | :--- |
| **Module 2** | **Video Capture Layer** | Producer/Consumer ring buffer (size 1) at 640x360 processing resolution with frame-drop policy; 8 FPS sampling; auto-reconnect with exponential backoff; CLAHE illumination normalization; sudden frame-difference occlusion detector & alert suppression. |
| **Module 3.1** | **Shelf Zone & Product Detection** | Spatial polygon filtering using YOLOv8n ONNX (with Haar cascade fallback) (point-in-polygon) separating calibrated shelf tiers, entrance gates, and staff counters from extraneous bounding boxes. |
| **Module 3.2** | **Few-Shot SKU Recognition** | 128-d L2-normalized convolutional feature encoder; few-shot photo averaging into SQLite `sku_gallery`; sub-second runtime cosine kNN matching without retraining. |
| **Module 3.3** | **Dual-Signal Gap & Occupancy** | Structural Similarity (SSIM) differencing vs baseline + detection density signal with rolling SMA smoothing; granular severity (`low`/`medium`/`high`); restock recovery detection; staff presence cooldown suppression. |
| **Module 4** | **Footfall & Dwell Tracking** | ByteTrack multi-object tracker for persistent shopper IDs; centroid dwell accumulation; entrance footfall bucket counters; staff zone exclusion. |
| **Module 5.1** | **Depletion & ETA Predictor** | Explainable linear regression & exponential smoothing over occupancy slope + footfall velocity; rolling forecast emitting `predicted_stockout` with ETA minutes and confidence. |
| **Module 5.2** | **Merchandising Insights** | Zone-level 2x2 correlation matrix (Footfall × Depletion): *Healthy Fast-Mover*, *Placement Friction*, *Dead Stock*, *Investigate Shrink/Theft*. |
| **Module 5.3** | **Alert & Rule Engine** | Urgency prioritization ($\text{Severity} \times \frac{1}{\text{ETA}}$); alert storm deduplication; camera occlusion suppression. |
| **Module 6** | **Active Learning Triage** | Confidence-based triage routing low-confidence crops to staff review queue; 1-click verification or new SKU creation instantly updating embedding gallery online. |
| **Module 7 & 8** | **FastAPI & Offline Sync Layer** | Thread-safe SQLite WAL database; WebSocket live event broadcasting; MQTT offline queue with exponential backoff retry; zero raw video egress. |
| **Module 9** | **React Operator Dashboard** | React + Vite + Tailwind CSS + Recharts + Lucide Icons: Live Action Feed, 2D Zone Map & CV Stream overlay, Interactive Zone Calibration, 2x2 Matrix, SKU Onboarding, Review Queue, ROI Impact Calculator, System Health HUD. |

---

## Quickstart & Local Execution

### 1. Requirements
- Python 3.10+
- Node.js 18+ & npm

### 2. Backend Setup
```bash
# Navigate to project root
cd retailiq

# Install Python dependencies
pip install -r backend/requirements.txt

# Run backend unit tests
python -m unittest discover -s backend/tests -p "test_*.py"

# Start the FastAPI edge backend (runs on port 8000)
python backend/main.py
```

### 3. Frontend Setup
```bash
# In a second terminal
cd retailiq/frontend

# Install dependencies (if not already done)
npm install

# Start Vite development server (runs on port 3000)
npm run dev
```

Open your browser at **`http://localhost:3000`** to access the live dashboard.

---

## Running with Docker Compose

```bash
docker-compose up --build
```
- Frontend UI: `http://localhost:3000`
- Backend API Docs: `http://localhost:8000/docs`

---

## Core API Endpoints

- `GET /health` — Edge diagnostics (camera, FPS, DB status, sync queue)
- `GET /zones`, `POST /zones/calibrate` — Zone definitions and baseline setup
- `GET /sku/list`, `POST /sku/onboard` — Few-shot SKU gallery onboarding
- `GET /events/live` (WebSocket) — Real-time event stream for alerts, predictions, occupancy
- `GET /dashboard/summary`, `GET /dashboard/insights`, `GET /dashboard/roi` — Analytics endpoints
- `GET /review-queue`, `POST /review-queue/{id}/correct` — Active learning triage
- `GET /video/feed` (MJPEG) — Live annotated computer vision video stream
- `POST /video/control` — Simulation triggers for stockouts, restocks, occlusion, low-light
