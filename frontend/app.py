"""
app.py — She Radiance AI | Main Streamlit PWA
==============================================
Entry point for the She Radiance AI Progressive Web Application.

Application flow (4 screens managed via st.session_state):
    Screen 1  — Consent Gate / Landing
    Screen 2  — Image Upload
    Screen 3  — Processing / Spinner (transient)
    Screen 4A — Results: Successful routine (Acne_Mild / Hyperpigmentation / Clear_Skin)
    Screen 4B — Medical Redirect (Acne_Severe / referral_flag)
    Screen 4C — Inconclusive Fallback (low_certainty / engine_error / unknown)

Ethics & Privacy:
    - Upload is blocked until explicit consent is given.
    - Uploaded images are written to a temp file ONLY during inference,
      transmitted to the Anthropic vision API for analysis, and deleted
      immediately afterwards (ephemeral processing, not retained by this app).
    - DIAGNOSTIC_LOG records only condition label, referral flag, and timestamp.
"""

import sys
import html
import tempfile
import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_APP_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _APP_DIR.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="She Radiance",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Lazy imports of backend modules
# ---------------------------------------------------------------------------
try:
    from vision_client import analyze_selfie
    from logic_router import route_from_vision
    from database import create_connection
    MODEL_AVAILABLE = True
except Exception as _model_err:
    MODEL_AVAILABLE = False
    _MODEL_ERROR_MSG = str(_model_err)

# Session-scoped cap on the number of vision-API analyses per user session.
_MAX_ANALYSES_PER_SESSION = 20


# ===========================================================================
# GLOBAL CSS - Premium Skincare Aesthetic
# ===========================================================================
def inject_global_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600&family=Inter:wght@300;400;500;600&display=swap');

        /* Base Theme */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #050505 !important;
            color: #F2F2F2;
        }

        /* Hide Streamlit Chrome */
        #MainMenu, footer, header { visibility: hidden; }
        .block-container {
            max-width: 680px;
            padding: 3rem 1.5rem 5rem 1.5rem;
            margin: auto;
        }

        /* Typography & Branding */
        .brand-header {
            text-align: center;
            padding-bottom: 2rem;
            margin-bottom: 2rem;
        }
        .brand-title {
            font-family: 'Cinzel', serif;
            font-size: clamp(2.2rem, 6vw, 3.2rem);
            font-weight: 500;
            background: linear-gradient(90deg, #EAD7A1, #C9A96E, #EAD7A1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            letter-spacing: 0.08em;
        }
        .brand-tagline {
            font-family: 'Inter', sans-serif;
            font-size: 0.75rem;
            color: #7A7A7A;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            margin-top: 0.5rem;
        }

        /* Glassmorphism Cards */
        .card {
            background: rgba(20, 20, 22, 0.6);
            border: 1px solid rgba(201, 169, 110, 0.15);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            transition: all 0.3s ease;
        }

        .section-heading {
            font-family: 'Cinzel', serif;
            font-size: 1.4rem;
            font-weight: 500;
            color: #EAD7A1;
            margin-bottom: 1rem;
            letter-spacing: 0.05em;
        }

        /* Elegant Banners */
        .banner {
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border-left: 2px solid;
            background: rgba(20, 20, 22, 0.8);
        }
        .banner-acne { border-color: #E8A838; }
        .banner-hyperpigmentation { border-color: #9B59B6; }
        .banner-clear { border-color: #4CAF6F; }
        .banner-severe { border-color: #D64045; }
        .banner-inconclusive { border-color: #7A7A7A; }
        
        .banner-title {
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
            font-weight: 500;
            margin: 0 0 0.3rem 0;
            letter-spacing: 0.02em;
        }
        .banner-sub {
            font-size: 0.85rem;
            color: #A0A0A0;
            margin: 0;
            font-weight: 300;
        }

        /* Refined Tables */
        .routine-table { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 1rem; font-size: 0.9rem; }
        .routine-table th { 
            color: #C9A96E; font-weight: 500; text-transform: uppercase; 
            font-size: 0.7rem; letter-spacing: 0.1em; padding: 1rem 0.75rem; 
            text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); 
        }
        .routine-table td { 
            padding: 1.2rem 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.05); 
            vertical-align: top; color: #D1D1D1; font-weight: 300; line-height: 1.6; 
        }

        /* Minimal Badges */
        .phase-badge { 
            display: inline-block; font-size: 0.65rem; font-weight: 500; 
            letter-spacing: 0.1em; text-transform: uppercase; 
            padding: 0.3rem 0.6rem; border-radius: 4px; border: 1px solid;
        }
        .phase-cleanse   { border-color: rgba(91, 141, 239, 0.3); color: #5B8DEF; background: rgba(91, 141, 239, 0.05); }
        .phase-serum     { border-color: rgba(155, 89, 182, 0.3); color: #9B59B6; background: rgba(155, 89, 182, 0.05); }
        .phase-moisturize{ border-color: rgba(76, 175, 111, 0.3); color: #4CAF6F; background: rgba(76, 175, 111, 0.05); }
        .phase-protect   { border-color: rgba(232, 168, 56, 0.3); color: #E8A838; background: rgba(232, 168, 56, 0.05); }

        /* Sleek Inputs & Buttons */
        div[data-testid="stFileUploader"] {
            background: rgba(255,255,255,0.02);
            border: 1px dashed rgba(201, 169, 110, 0.3);
            border-radius: 12px;
            padding: 2rem;
            transition: all 0.3s;
        }
        div[data-testid="stFileUploader"]:hover {
            border-color: rgba(201, 169, 110, 0.8);
            background: rgba(255,255,255,0.04);
        }
        
        div.stButton > button { 
            background: #C9A96E; 
            color: #050505; 
            font-family: 'Inter', sans-serif;
            font-weight: 500; 
            letter-spacing: 0.05em;
            border-radius: 8px; 
            padding: 0.6rem 2rem; 
            border: none;
            transition: all 0.3s ease;
        }
        div.stButton > button:hover { 
            background: #EAD7A1; 
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(201, 169, 110, 0.2);
        }

        /* Disclaimer & Footer */
        .disclaimer { 
            font-size: 0.75rem; color: #7A7A7A; line-height: 1.5; 
            margin-top: 1rem; font-weight: 300; 
        }
        .app-footer { 
            text-align: center; font-size: 0.7rem; color: #555; 
            margin-top: 4rem; padding-top: 1.5rem; 
            border-top: 1px solid rgba(255,255,255,0.05); 
            letter-spacing: 0.1em; text-transform: uppercase;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ===========================================================================
# HELPERS
# ===========================================================================
def render_brand_header():
    st.markdown(
        """
        <div class="brand-header">
            <p class="brand-title">SHE RADIANCE</p>
            <p class="brand-tagline">Clinical Skincare Intelligence</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_footer():
    st.markdown(
        '<div class="app-footer">Intelligent Dermatological Triage</div>',
        unsafe_allow_html=True,
    )

def init_session_state():
    defaults = {
        "consent_given": False,
        "uploaded_image": None,
        "diagnosis_result": None,
        "vision_result": None,
        "app_stage": "consent",
        "analysis_count": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_session():
    st.session_state["consent_given"] = False
    st.session_state["uploaded_image"] = None
    st.session_state["diagnosis_result"] = None
    st.session_state["vision_result"] = None
    st.session_state["app_stage"] = "consent"
    # analysis_count is intentionally NOT reset: the cap applies per session.

def log_diagnosis_to_db(condition: str, referral_flag: bool):
    try:
        conn = create_connection()
        if conn is None:
            return
        cursor = conn.cursor()
        sql = "INSERT INTO DIAGNOSTIC_LOG (Condition_Detected, Referral_Flag, Created_At) VALUES (%s, %s, %s);"
        cursor.execute(sql, (condition, bool(referral_flag), datetime.datetime.now(datetime.timezone.utc)))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

def run_inference(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = Path(tmp.name)

    try:
        vision_result = analyze_selfie(tmp_path)
        routing_result = route_from_vision(vision_result)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return vision_result, routing_result

def get_phase_badge(phase: str) -> str:
    css_class = {"Cleanse": "phase-cleanse", "Serum": "phase-serum", "Moisturize": "phase-moisturize", "Protect": "phase-protect"}.get(phase, "phase-cleanse")
    return f'<span class="phase-badge {css_class}">{phase}</span>'

def get_condition_display(label: str) -> dict:
    mapping = {
        "Acne_Mild": {"title": "Mild Acne Profile", "banner_class": "banner-acne", "colour": "#E8A838"},
        "Hyperpigmentation": {"title": "Hyperpigmentation Profile", "banner_class": "banner-hyperpigmentation", "colour": "#9B59B6"},
        "Clear_Skin": {"title": "Maintenance Profile", "banner_class": "banner-clear", "colour": "#4CAF6F"},
        "Acne_Severe": {"title": "Severe Profile / Medical Review Recommended", "banner_class": "banner-severe", "colour": "#D64045"},
    }
    return mapping.get(label, {"title": label, "banner_class": "banner-inconclusive", "colour": "#A0A0A0"})

# ===========================================================================
# SCREEN RENDERERS
# ===========================================================================
def render_screen_consent():
    st.markdown(
        """
        <div class="card">
            <p class="section-heading">Welcome</p>
            <p style="color:#D1D1D1; font-weight:300; line-height:1.8; font-size:0.95rem;">
                She Radiance utilizes advanced computer vision to analyze your skin's unique 
                profile. By scanning your portrait, our engine maps your condition to a curated 
                database of active pharmaceutical ingredients, formulating a personalized and 
                chemically-safe regimen.
            </p>
        </div>
        """, unsafe_allow_html=True
    )

    consent = st.checkbox(
        "I understand my photo will be transmitted to Anthropic, a third-party AI processor, for analysis. "
        "It is not retained by this application.",
        value=st.session_state["consent_given"],
    )
    st.session_state["consent_given"] = consent

    st.markdown('<div class="disclaimer">⚕️ <strong>Disclaimer:</strong> This tool provides cosmetic guidance only and is not a medical diagnosis. It does not replace professional dermatological consultation.</div>', unsafe_allow_html=True)
    st.write("")

    if consent:
        if st.button("Begin Analysis"):
            st.session_state["app_stage"] = "upload"
            st.rerun()
    else:
        st.button("Begin Analysis", disabled=True)

def render_screen_upload():
    st.markdown('<p class="section-heading">Skin Analysis</p>', unsafe_allow_html=True)
    st.markdown('<p class="disclaimer" style="margin-top:0; margin-bottom: 1.5rem;">For optimal precision, ensure your face is well-lit and free of filters.</p>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(label="Upload portrait", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Secure Preview", width="stretch")
        st.write("")

        if not MODEL_AVAILABLE:
            st.error("Engine offline. Please verify the inference backend is initialized.")
            return

        limit_reached = st.session_state.get("analysis_count", 0) >= _MAX_ANALYSES_PER_SESSION

        col1, col2 = st.columns([1, 1])
        with col1:
            analyse_clicked = st.button("Process Image", use_container_width=True, disabled=limit_reached)
        with col2:
            if st.button("Reset", use_container_width=True):
                reset_session()
                st.rerun()

        if limit_reached:
            st.markdown(
                '<p class="disclaimer">You\'ve reached the maximum of '
                f'{_MAX_ANALYSES_PER_SESSION} analyses for this session. '
                'Please refresh the page to start a new session.</p>',
                unsafe_allow_html=True,
            )

        if analyse_clicked:
            with st.spinner("Analyzing dermatological markers..."):
                vision_result, routing_result = run_inference(uploaded_file)

            st.session_state["analysis_count"] = st.session_state.get("analysis_count", 0) + 1
            st.session_state["vision_result"] = vision_result
            st.session_state["diagnosis_result"] = routing_result

            log_diagnosis_to_db(
                condition=vision_result.get("condition", "Unknown"),
                referral_flag=vision_result.get("referral_flag", False),
            )

            st.session_state["app_stage"] = "results"
            st.rerun()

def render_routine_table(routine: list) -> str:
    rows_html = ""
    for item in routine:
        phase_badge = get_phase_badge(item.get("treatment_phase", ""))
        rows_html += f'<tr><td>{phase_badge}</td><td><strong>{item.get("active_compound", "")}</strong></td><td>{item.get("dermatological_logic", "")}</td></tr>'

    return f'<table class="routine-table"><thead><tr><th>Phase</th><th>Active Compound</th><th>Mechanism of Action</th></tr></thead><tbody>{rows_html}</tbody></table>'

def render_visible_features(features: list):
    if not features:
        return
    items_html = "".join(f"<li>{html.escape(str(f))}</li>" for f in features)
    st.markdown(
        f'<ul style="color:#A0A0A0; font-size:0.85rem; font-weight:300; '
        f'line-height:1.6; margin-top:0.5rem; padding-left:1.2rem;">{items_html}</ul>',
        unsafe_allow_html=True,
    )

def render_screen_results():
    vision_result = st.session_state.get("vision_result") or {}
    routing_result = st.session_state.get("diagnosis_result") or {}
    condition = vision_result.get("condition", "Unknown")
    visible_features = vision_result.get("visible_features", [])
    display = get_condition_display(condition)
    status = routing_result.get("status")

    if status == "success":
        st.markdown(f'<div class="banner {display["banner_class"]}"><p class="banner-title" style="color:{display["colour"]};">{display["title"]}</p></div>', unsafe_allow_html=True)
        render_visible_features(visible_features)

        table_html = render_routine_table(routing_result["routine"]) if routing_result.get("routine") else ""
        st.markdown(
            '<div class="card">'
            '<p class="section-heading" style="font-size: 1.1rem;">Formulated Regimen</p>'
            '<p class="disclaimer" style="margin-top:0;">'
            'The compounds below are active pharmaceutical ingredients, not commercial brand names &mdash; '
            'look for over-the-counter products whose ingredient list contains them. '
            'The Mechanism of Action column explains why each compound was selected for your profile.'
            '</p>'
            f'{table_html}'
            '</div>',
            unsafe_allow_html=True,
        )

    elif status == "medical_redirect":
        st.markdown(f'<div class="banner banner-severe"><p class="banner-title" style="color:{display["colour"]};">{display["title"]}</p></div>', unsafe_allow_html=True)
        render_visible_features(visible_features)
        st.markdown(f'<div class="card"><p style="font-weight:300;">{routing_result.get("message", "")}</p></div>', unsafe_allow_html=True)

    elif status == "inconclusive":
        reason = routing_result.get("reason")
        if reason == "low_certainty":
            copy = ("Our engine could not identify visible skin markers with sufficient certainty "
                    "from this image. Please try again with a clearer, well-lit, unfiltered photograph.")
        elif reason == "engine_error":
            copy = ("We were unable to complete this analysis due to a temporary processing issue. "
                    "Please try again shortly, or consult a dermatologist if the issue persists.")
        else:
            copy = ("We could not produce a reliable result for this image. "
                    "Please try again, or consult a dermatologist if the issue persists.")
        st.markdown('<div class="banner banner-inconclusive"><p class="banner-title" style="color:#A0A0A0;">Analysis Inconclusive</p></div>', unsafe_allow_html=True)
        render_visible_features(visible_features)
        st.markdown(f'<div class="card"><p style="font-weight:300;">{copy}</p></div>', unsafe_allow_html=True)

    else:
        st.markdown('<div class="banner banner-inconclusive"><p class="banner-title" style="color:#A0A0A0;">Unable to Complete Analysis</p></div>', unsafe_allow_html=True)
        st.markdown('<div class="card"><p style="font-weight:300;">Something unexpected happened while processing your results. Please consult a licensed dermatological professional for guidance.</p></div>', unsafe_allow_html=True)

    st.write("")
    if st.button("Start New Analysis"):
        reset_session()
        st.rerun()

# ===========================================================================
# MAIN ENTRY
# ===========================================================================
def main():
    inject_global_css()
    init_session_state()
    render_brand_header()
    
    stage = st.session_state.get("app_stage", "consent")
    if stage == "consent": render_screen_consent()
    elif stage == "upload": render_screen_upload()
    elif stage == "results": render_screen_results()
    
    render_footer()

if __name__ == "__main__":
    main()
    