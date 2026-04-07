# OCR Web Application

A hybrid C++/Python web application for extracting editable text from images using Tesseract OCR. Users can upload images, get OCR results with confidence highlighting, edit the extracted text, and export to PDF, DOCX, or TXT. Corrections are collected to fine-tune the model over time.

## Architecture

- **C++ OCR Engine** — Tesseract API wrapper with image preprocessing (deskew, denoise, threshold), exposed to Python via pybind11
- **Python Backend** — FastAPI server handling image upload, OCR, document export, and correction storage
- **React Frontend** — Modern SPA with drag-and-drop upload, side-by-side editor with confidence-coded overlays, and export controls
- **Fine-Tuning Pipeline** — Scripts to convert user corrections into Tesseract LSTM training data and retrain the model

## Prerequisites

```bash
sudo apt install libtesseract-dev libleptonica-dev pybind11-dev cmake python3-dev python3-pip
```

Node.js 18+ is required for the frontend.

## Build & Run

### 1. Build the C++ Engine

```bash
cd engine
mkdir -p build && cd build
cmake .. -DPYTHON_EXECUTABLE=$(which python3)
make -j$(nproc)
```

### 2. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the Backend

```bash
cd backend
PYTHONPATH=../engine/build uvicorn app.main:app --reload --port 8000
```

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## API Endpoints

| Method | Endpoint           | Description                     |
|--------|--------------------|---------------------------------|
| POST   | `/api/ocr`         | Upload image, get OCR result    |
| POST   | `/api/export`      | Export text as PDF/DOCX/TXT     |
| POST   | `/api/corrections` | Submit text corrections         |
| GET    | `/api/corrections` | List all stored corrections     |
| GET    | `/api/health`      | Health check                    |

## Fine-Tuning the Model

After collecting corrections through the web UI:

```bash
cd finetune

# Step 1: Prepare training data from corrections
python prepare_training_data.py

# Step 2: Fine-tune the LSTM model
./train.sh eng 400

# Step 3: Evaluate improvement
python evaluate.py eng
```

The fine-tuned model will be saved to `finetune/model/eng_finetuned.traineddata`.
