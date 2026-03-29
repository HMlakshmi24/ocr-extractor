# 📇 Business Card OCR Extractor

**By Parijat Controlware** — Automation & Control Solutions

AI-powered business card scanner that extracts contact details and exports them to Excel in seconds.

---

## What it does

Upload a business card image (PNG, JPG, PDF, or DOCX) and the app automatically extracts:

| Field | Field | Field |
|-------|-------|-------|
| Name | Mobile / Cell | Address |
| Company | Phone / Tel | City |
| Title | Email | State / Zip / Country |
| | Website | |

- Results appear on-screen as **editable fields** — correct anything before downloading
- Export to a **fresh Excel file** or **append to your existing Excel**
- Handles Indian and international cards (PIN codes, +91 numbers, Indian states)

---

## Tech Stack

- **Frontend** — [Streamlit](https://streamlit.io)
- **OCR** — [EasyOCR](https://github.com/JaidedAI/EasyOCR) with multi-variant preprocessing + auto-orientation
- **AI Extraction** — NVIDIA NIM API (`gpt-oss-120b`) via OpenAI-compatible client
- **PDF support** — Poppler + PyMuPDF fallback
- **Export** — openpyxl with colour-coded Excel output

---

## Run locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your NVIDIA API key (or it falls back to the default)
export NVIDIA_API_KEY="your_key_here"

# 3. Run
python -m streamlit run app.py
```

Open **http://localhost:8501** in your browser.

> **Windows users:** the `poppler/` folder is bundled for local use. No extra install needed.

---

## Deploy to Streamlit Cloud

1. Push this repo to GitHub (the `poppler/` folder is git-ignored — that's fine)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select repo → `app.py`
3. Under **Advanced settings → Secrets**, add:
   ```toml
   NVIDIA_API_KEY = "your_nvidia_api_key"
   ```
4. Click **Deploy** — first build takes ~5–10 min (EasyOCR model download)

---

## Project structure

```
ocr-extractor/
├── app.py                  # Streamlit UI
├── requirements.txt        # Python dependencies
├── packages.txt            # System packages for Streamlit Cloud (poppler-utils)
└── src/
    ├── file_parser.py      # File loading & single-card parsing
    ├── ocr_engine.py       # EasyOCR pipeline (orientation detection, preprocessing)
    ├── extractor.py        # LLM-based field extraction + regex fallback
    ├── validator.py        # Field validation & status tagging
    └── exporter.py         # Excel generation (openpyxl)
```

---

*© 2026 Parijat Controlware*
