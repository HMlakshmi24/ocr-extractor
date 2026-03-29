import io
import streamlit as st
import pandas as pd
from PIL import Image

from src.file_parser import parse_single_card
from src.ocr_engine import load_ocr, run_ocr_pipeline
from src.extractor import extract_fields
from src.validator import validate_data
from src.exporter import export_to_excel_bytes, append_to_existing_excel

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_FIELDS = ['Name', 'Company', 'Title', 'Email', 'Mobile', 'Phone',
               'Address', 'City', 'State', 'Zip', 'Country', 'Website']

FIELD_LABELS = {
    'Name':    '👤 Name',
    'Company': '🏢 Company',
    'Title':   '💼 Title',
    'Email':   '📧 Email',
    'Mobile':  '📱 Mobile / Cell',
    'Phone':   '📞 Phone / Tel',
    'Address': '📍 Address',
    'City':    '🌆 City',
    'State':   '🗺️ State',
    'Zip':     '📮 Zip / Pin Code',
    'Country': '🌍 Country',
    'Website': '🌐 Website',
}

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Business Card OCR | Parijat Controlware",
    page_icon="📇",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global ── */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(150deg, #eef2ff 0%, #f5f7ff 45%, #fffbf2 100%);
    min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent !important; }
.block-container { padding-top: 0.6rem !important; max-width: 1240px; }
[data-testid="stVerticalBlock"] { gap: 0.5rem; }

/* ── Top bar ── */
.topbar {
    display: flex; justify-content: space-between; align-items: center;
    background: linear-gradient(135deg, #08123a 0%, #162f80 55%, #0d47a1 100%);
    padding: 13px 30px; border-radius: 16px; margin-bottom: 20px;
    box-shadow: 0 6px 28px rgba(8, 18, 58, 0.45);
}
.tb-left { display: flex; flex-direction: column; gap: 2px; }
.tb-brand { font-size: 18px; font-weight: 800; color: #FFD700; letter-spacing: 0.3px; }
.tb-tagline { font-size: 11px; color: rgba(255,255,255,0.5); }
.tb-title { font-size: 20px; font-weight: 900; color: #fff; letter-spacing: -0.3px; }
.tb-right { display: flex; gap: 8px; align-items: center; }
.tbadge {
    background: rgba(255,255,255,0.14); color: rgba(255,255,255,0.85);
    font-size: 11px; padding: 4px 11px; border-radius: 20px; font-weight: 600;
}

/* ── Hero ── */
.hero { text-align: center; padding: 10px 0 18px; }
.hero-h1 {
    font-size: 2.3rem; font-weight: 900; margin: 0 0 8px 0;
    background: linear-gradient(130deg, #08123a 0%, #1565c0 50%, #6a1b9a 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    line-height: 1.15;
}
.hero-sub { color: #607d8b; font-size: 0.97rem; letter-spacing: 0.3px; margin: 0; }

/* ── Section labels ── */
.sec-lbl {
    font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1.4px;
    color: #08123a; background: linear-gradient(90deg, #e8ecff, #f0f4ff);
    display: inline-block; padding: 5px 13px; border-radius: 7px;
    margin-bottom: 10px; border-left: 3px solid #3f5bd4;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #08123a 0%, #1565c0 100%) !important;
    color: white !important; border: none !important; border-radius: 11px !important;
    font-weight: 800 !important; font-size: 15px !important; letter-spacing: 0.3px !important;
    box-shadow: 0 4px 18px rgba(21,101,192,0.45) !important;
    transition: transform 0.15s, box-shadow 0.15s !important; padding: 13px 0 !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(21,101,192,0.55) !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%) !important;
    color: white !important; border: none !important; border-radius: 11px !important;
    font-weight: 800 !important; font-size: 14px !important;
    box-shadow: 0 4px 16px rgba(46,125,50,0.42) !important;
    transition: transform 0.15s !important; padding: 12px 0 !important; width: 100% !important;
}
[data-testid="stDownloadButton"] > button:hover { transform: translateY(-2px) !important; }

/* ── Success / info / warning override ── */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ── Expander ── */
.streamlit-expanderHeader { font-weight: 700 !important; color: #08123a !important; }

/* ── Editable text inputs ── */
.stTextInput > div > div > input {
    border-radius: 8px !important;
    border: 1.5px solid #dde3f8 !important;
    background: #fafbff !important;
    color: #1a237e !important;
    font-weight: 500 !important;
}
.stTextInput > div > div > input:focus {
    border-color: #3f5bd4 !important;
    box-shadow: 0 0 0 3px rgba(63,91,212,0.12) !important;
}
.stTextInput > label {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #546e7a !important;
}

/* empty state */
.estate { text-align: center; padding: 60px 24px; color: #b0bec5; }
.estate-icon { font-size: 72px; margin-bottom: 16px; opacity: 0.65; }
.estate-msg  { font-size: 16px; font-weight: 600; color: #90a4ae; }
.estate-sub  { font-size: 12px; margin-top: 8px; color: #cfd8dc; }

/* footer */
.footer {
    text-align: center; font-size: 11px; color: #b0bec5;
    padding: 20px 0 10px; letter-spacing: 0.4px; border-top: 1px solid #e8eaf6; margin-top: 28px;
}

/* divider override */
hr { border-color: #e8ecf8 !important; margin: 14px 0 !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_preview_image(file_bytes, file_name):
    """Return a PIL Image for previewing any supported format."""
    ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
    try:
        if ext in ('jpg', 'jpeg', 'png'):
            return Image.open(io.BytesIO(file_bytes))
        elif ext == 'pdf':
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            pix = doc.load_page(0).get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    except Exception:
        pass
    return None


# ── Main app ──────────────────────────────────────────────────────────────────

def main():
    # Load OCR model (cached across reruns)
    with st.spinner("Loading OCR engine…"):
        try:
            ocr_model = load_ocr()
        except Exception as e:
            st.error(f"Failed to load OCR model: {e}")
            st.stop()

    # ── Top bar ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="topbar">
      <div class="tb-left">
        <div class="tb-brand">🏢 Parijat Controlware</div>
        <div class="tb-tagline">Automation &amp; Control Solutions</div>
      </div>
      <div class="tb-title">📇 Business Card OCR Extractor</div>
      <div class="tb-right">
        <span class="tbadge">🤖 AI-Powered</span>
        <span class="tbadge">⚡ Instant</span>
        <span class="tbadge">📊 Excel Export</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero">
      <p class="hero-h1">Transform Business Cards Into Contacts</p>
      <p class="hero-sub">
        📷 Upload a card &nbsp;·&nbsp;
        🤖 AI extracts all 11 fields &nbsp;·&nbsp;
        📊 Download to Excel — in seconds
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_left, col_right = st.columns([4, 6], gap="large")

    # ── LEFT: Upload & Controls ───────────────────────────────────────────────
    with col_left:
        st.markdown('<div class="sec-lbl">📤 Upload Business Card</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "PNG · JPG · PDF · DOCX — one card at a time",
            type=['png', 'jpg', 'jpeg', 'pdf', 'docx', 'doc'],
            accept_multiple_files=False,
            label_visibility="visible",
        )

        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            st.session_state['file_bytes'] = file_bytes
            st.session_state['file_name']  = uploaded_file.name

            preview = _get_preview_image(file_bytes, uploaded_file.name)
            if preview:
                st.image(preview, caption=f"📄 {uploaded_file.name}", width='stretch')
            else:
                st.info(f"📄 {uploaded_file.name} — preview not available for this format.")

        st.divider()

        st.markdown('<div class="sec-lbl">📁 Existing Excel (Optional)</div>', unsafe_allow_html=True)
        template_file = st.file_uploader(
            "Upload your .xlsx — extracted data will be appended",
            type=['xlsx'],
            key="excel_template",
            help="Leave empty to download a fresh formatted Excel instead.",
        )
        if template_file:
            st.success(f"✅ Template loaded: **{template_file.name}**")
        else:
            st.caption("No template — a new formatted Excel will be created.")

        st.markdown("<br>", unsafe_allow_html=True)

        process_clicked = st.button(
            "▶  Extract Card Data",
            use_container_width=True,
            type="primary",
        )

        # ── Processing logic ──────────────────────────────────────────────────
        if process_clicked:
            fb = st.session_state.get('file_bytes')
            fn = st.session_state.get('file_name', '')
            if not fb:
                st.warning("⚠️ Please upload a business card first.")
            else:
                with st.spinner("🔍 Running OCR + AI extraction…"):
                    result = parse_single_card(fb, fn)
                    if result is None:
                        st.error("❌ Could not read the card file. "
                                 "Please try a clearer image or different format.")
                    else:
                        img_id, pil_img = result
                        try:
                            raw_text, conf = run_ocr_pipeline(pil_img, ocr_model)
                            extracted = extract_fields(raw_text)
                            record    = {'Image_ID': img_id,
                                         'Confidence': round(conf, 2),
                                         **extracted}
                            validated = validate_data(record, conf)
                            st.session_state['result']         = validated
                            st.session_state['conf']           = conf
                            st.session_state['raw_text']       = raw_text
                            st.session_state['template_bytes'] = (
                                template_file.read() if template_file else None
                            )
                            # Seed the editable fields with extracted values
                            for f in DATA_FIELDS:
                                st.session_state[f'edit_{f}'] = validated.get(f, '')
                        except Exception as e:
                            st.error(f"Extraction error: {e}")

        # Raw OCR text (collapsible debug view)
        if 'raw_text' in st.session_state and st.session_state['raw_text']:
            with st.expander("🔬 Raw OCR Text (debug)"):
                st.code(st.session_state['raw_text'], language=None)

    # ── RIGHT: Results ────────────────────────────────────────────────────────
    with col_right:
        if 'result' not in st.session_state:
            st.markdown("""
            <div class="estate">
              <div class="estate-icon">📇</div>
              <div class="estate-msg">Upload a card and click Extract</div>
              <div class="estate-sub">
                Supports&nbsp; PNG &nbsp;·&nbsp; JPG &nbsp;·&nbsp; PDF &nbsp;·&nbsp; DOCX
              </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            # ── Task completed header ─────────────────────────────────────────
            st.success("✅ Task Completed — review the extracted fields below and correct anything if needed.")

            # ── Inline editable fields ────────────────────────────────────────
            c1, c2 = st.columns(2)
            with c1:
                st.text_input(FIELD_LABELS['Name'],    key='edit_Name',
                              placeholder="— possibly missing —")
                st.text_input(FIELD_LABELS['Company'], key='edit_Company',
                              placeholder="— possibly missing —")
                st.text_input(FIELD_LABELS['Title'],   key='edit_Title',
                              placeholder="— possibly missing —")
                st.text_input(FIELD_LABELS['Address'], key='edit_Address',
                              placeholder="— possibly missing —")
                st.text_input(FIELD_LABELS['Mobile'],  key='edit_Mobile',
                              placeholder="— possibly missing —")
            with c2:
                st.text_input(FIELD_LABELS['Email'],   key='edit_Email',
                              placeholder="— possibly missing —")
                st.text_input(FIELD_LABELS['Phone'],   key='edit_Phone',
                              placeholder="— possibly missing —")
                st.text_input(FIELD_LABELS['Website'], key='edit_Website',
                              placeholder="— possibly missing —")
                st.text_input(FIELD_LABELS['Country'], key='edit_Country',
                              placeholder="— possibly missing —")

            c3, c4, c5 = st.columns(3)
            with c3:
                st.text_input(FIELD_LABELS['City'],  key='edit_City',
                              placeholder="— possibly missing —")
            with c4:
                st.text_input(FIELD_LABELS['State'], key='edit_State',
                              placeholder="— possibly missing —")
            with c5:
                st.text_input(FIELD_LABELS['Zip'],   key='edit_Zip',
                              placeholder="— possibly missing —")

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Excel export using current (possibly edited) field values ─────
            base = st.session_state['result']
            export_record = {f: st.session_state.get(f'edit_{f}', '') for f in DATA_FIELDS}
            export_record['Image_ID']   = base.get('Image_ID', 'card_001')
            export_record['Confidence'] = base.get('Confidence', 0)
            # carry status columns for Excel cell colouring
            for f in DATA_FIELDS:
                sk = f'status_{f.lower()}'
                export_record[sk] = base.get(sk, '')

            merged_df = pd.DataFrame([export_record])
            tb = st.session_state.get('template_bytes')

            try:
                if tb:
                    excel_out = append_to_existing_excel(merged_df, tb)
                    dl_label  = "📥 Download Updated Excel (Appended)"
                    dl_fname  = "business_cards_updated.xlsx"
                else:
                    excel_out = export_to_excel_bytes(merged_df)
                    dl_label  = "📥 Download Excel"
                    dl_fname  = "business_cards.xlsx"

                st.download_button(
                    label=dl_label,
                    data=excel_out,
                    file_name=dl_fname,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Excel export error: {e}")

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="footer">'
        '© 2026 Parijat Controlware &nbsp;·&nbsp; Business Card OCR &nbsp;·&nbsp;'
        ' Powered by EasyOCR + AI'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
