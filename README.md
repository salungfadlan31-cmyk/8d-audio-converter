# 8D Audio Converter

> Transform your music into immersive 8D, slow & reverb audio — powered by Python + FastAPI + Next.js.

---

## ✨ Features

- Upload **MP3** or **WAV** (max 50 MB)
- Full **8D + slow + reverb** processing pipeline (existing Python engine)
- Built-in **audio player** with waveform visualizer
- One-click **MP3 download**
- Beautiful **dark glassmorphism** UI

---

## 📁 Project Structure

```
8d-slow-reverb-main/          ← project root
│
├── effects/                  ← existing Python audio effects (unchanged)
│   ├── effect8d.py
│   ├── slow.py
│   └── reverb.py
├── utils/                    ← existing Python utilities (unchanged)
│   ├── loadSound.py
│   └── saveSound.py
├── settings.py               ← existing audio settings (unchanged)
├── main.py                   ← original CLI entry-point (unchanged)
│
├── backend/                  ← FastAPI backend
│   ├── main.py               ← API server
│   ├── requirements.txt      ← Python dependencies
│   ├── uploads/              ← temp uploaded files
│   └── outputs/              ← processed audio files
│
└── frontend/                 ← Next.js 15 frontend
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   └── globals.css
    ├── components/
    │   ├── AudioUploader.tsx
    │   ├── AudioPlayer.tsx
    │   └── ProcessingStatus.tsx
    ├── .env.local
    └── package.json
```

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.9+ |
| Node.js | 18+ |
| FFmpeg | any recent (required by pydub) |

> **Install FFmpeg on Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to your PATH.

---

### 1. Backend Setup

```bash
# Navigate to backend folder
cd backend

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: **http://localhost:8000**
Interactive docs: **http://localhost:8000/docs**

---

### 2. Frontend Setup

```bash
# Navigate to frontend folder
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The app will be available at: **http://localhost:3000**

---

## API Reference

### `POST /api/process`

**Request:** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | File | MP3 or WAV audio file (max 50 MB) |

**Response:**
```json
{
  "success": true,
  "file_url": "/outputs/abc123_song_8d.mp3",
  "file_name": "abc123_song_8d.mp3",
  "original": "song.mp3"
}
```

### `GET /outputs/{filename}`

Returns the processed MP3 file for playback or download.

---

## Configuration

### Backend (`settings.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `timeLtoR` | `10000` ms | Time for audio to pan L→R |
| `jumpPercentage` | `5` | Pan jump step size (%) |
| `panBoundary` | `100` | Max pan distance from center (%) |
| `volumeMultiplier` | `6` | Volume increase at edges (dB) |
| `speedMultiplier` | `0.92` | Playback speed (1.0 = original) |

### Frontend (`.env.local`)

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

Change this URL when deploying to production.

---

## Dependencies

### Python (backend)

| Package | Purpose |
|---------|---------|
| `fastapi` | REST API framework |
| `uvicorn` | ASGI server |
| `python-multipart` | File upload parsing |
| `pydub` | Audio loading & MP3 export |
| `soundfile` | WAV reading/writing |
| `pedalboard` | Reverb effect (Spotify) |
| `numpy` | Audio data manipulation |

### Node.js (frontend)

| Package | Purpose |
|---------|---------|
| `next` | React framework (App Router) |
| `react` | UI library |
| `tailwindcss` | Utility CSS |
| `typescript` | Type safety |

---

## Troubleshooting

**`pydub` can't find FFmpeg**
```
Make sure ffmpeg is installed and accessible in PATH.
Test with: ffmpeg -version
```

**CORS error in browser**
```
Ensure the backend is running on port 8000.
Check NEXT_PUBLIC_BACKEND_URL in frontend/.env.local
```

**`ModuleNotFoundError: No module named 'settings'`**
```
The backend adds the project root to sys.path automatically.
Run uvicorn from inside the backend/ folder.
```

**Port 3000 already in use**
```bash
npm run dev -- --port 3001
```

---

## License

MIT — use freely, credit appreciated.
