"""
DesignCreationHub — Etsy POD Edition  v4.0
Author : Special Pixel Studio (Sharif)

v4 Changelog (Etsy Commercial Fix):
  - REMOVED all aggressive digital quality tags (8K, ultra-detailed, HDR,
    sharp focus, vibrant, vector) that were forcing glossy 3D cartoon renders
  - NEW: Etsy POD preset system with watercolor, distressed screenprint,
    boho, vintage ink styles tuned for apparel/sublimation markets
  - NEW: Single Design Mode toggle — forces one centered graphic with
    legible text instead of garbled multi-panel grid sheets
  - NEW: Style Transfer Mode for img2img — extracts watercolor texture +
    muted palette from reference instead of cartoon-ifying it
  - FIXED: prompt_strength direction (low = close to ref, high = creative)
  - FIXED: negative prompt blocks out glossy/3D/vector/neon artifacts
  - KEPT: secrets → env → sidebar token resolution (v3 fix)
  - KEPT: lazy replicate import, graceful onboarding, HF fallback
"""

import base64
import io
import os
import time

import requests
import streamlit as st
from PIL import Image

# ============================================================================
# 0.  PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="DesignCreationHub — Etsy POD Studio",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# 1.  TOKEN RESOLUTION  (secrets → env → sidebar)
# ============================================================================
def _load_secret(key: str) -> str:
    try:
        val = st.secrets.get(key, "")
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(key, "")

_REPLICATE_TOKEN = _load_secret("REPLICATE_API_TOKEN")
_HF_TOKEN        = _load_secret("HF_API_TOKEN")

# ============================================================================
# 2.  MODEL ENDPOINTS
# ============================================================================
REPLICATE_T2I_MODEL = "black-forest-labs/flux-schnell"
REPLICATE_I2I_MODEL = "black-forest-labs/flux-dev"
HF_T2I_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
HF_I2I_URL = "https://api-inference.huggingface.co/models/diffusers/stable-diffusion-xl-1.0-img2img"

# ============================================================================
# 3.  ETSY POD PRESET SYSTEM
#
#     KEY DESIGN DECISIONS:
#     ─────────────────────
#     • NO "8K", "ultra-detailed", "sharp focus", "vibrant", "HDR" tags
#       These push FLUX into glossy photorealistic / 3D render mode.
#     • USE texture descriptors: "hand-painted", "watercolor wash",
#       "distressed", "screenprint" to get the boutique apparel look.
#     • PALETTE is described in natural language, not color codes.
#     • Each preset ends with "on white background" — critical for
#       POD/sublimation cutouts.
# ============================================================================

# ── Etsy POD Style Presets ──────────────────────────────────────────────────
ETSY_STYLE_PRESETS: dict[str, dict] = {

    "🌾 Vintage Watercolor (Primary — Etsy #1)": {
        "positive": (
            "hand-painted watercolor illustration, t-shirt graphic art, "
            "cottagecore autumn aesthetic, soft muted fall color palette, "
            "rust orange and warm cream and mustard yellow tones, "
            "subtle paper texture, loose painterly brushstrokes, "
            "boutique Etsy apparel print style, "
            "delicate ink outlines, whimsical folk art quality, "
            "clean white background"
        ),
        "negative": (
            "3D render, glossy, plastic, shiny, photorealistic, photograph, "
            "neon colors, oversaturated, vibrant, electric colors, "
            "sharp focus, hyperdetailed, 8k, HDR, vector art, "
            "flat design, digital art, clipart, cartoon 3D, "
            "busy background, gradient background, blurry, low quality"
        ),
        "guidance": 4.5,   # lower CFG = softer painterly look
        "steps": 30,
    },

    "📜 Distressed Retro Screenprint": {
        "positive": (
            "vintage 1970s distressed t-shirt graphic, hand-drawn ink illustration, "
            "faded retro color palette, warm sepia and rust and sage green tones, "
            "screenprinted texture with ink bleed, aged worn look, "
            "folk art lettering style, retro Americana apparel graphic, "
            "rough hand-inked edges, clean white background"
        ),
        "negative": (
            "3D, glossy, plastic, shiny, photorealistic, CGI, neon, "
            "oversaturated, clean digital art, vector, flat, clipart, "
            "modern, futuristic, hyperrealistic, sharp focus, HDR, 8k, "
            "complex busy background, gradient"
        ),
        "guidance": 5.0,
        "steps": 28,
    },

    "🌸 Boho Floral Sublimation": {
        "positive": (
            "boho watercolor floral design, sublimation t-shirt print, "
            "wildflower botanical illustration, soft dusty rose and sage and ivory palette, "
            "hand-painted loose petals, delicate leaf sprigs, "
            "cottagecore farmhouse aesthetic, feminine apparel graphic, "
            "airy light feel, transparent watercolor washes, white background"
        ),
        "negative": (
            "3D, glossy, shiny, photorealistic, neon, oversaturated, "
            "dark background, busy background, clipart, vector, flat design, "
            "sharp crisp edges, hyperdetailed, 8k, HDR, plastic look"
        ),
        "guidance": 4.0,
        "steps": 28,
    },

    "🎃 Halloween Cottagecore (Seasonal)": {
        "positive": (
            "hand-drawn Halloween watercolor illustration, t-shirt print art, "
            "cottagecore spooky aesthetic, muted autumn palette "
            "(pumpkin orange, charcoal black, warm cream, dusty sage), "
            "cute ghost and pumpkin motifs, plaid and buffalo check accents, "
            "soft ink outlines, whimsical folk art style, "
            "distressed vintage feel, clean white background"
        ),
        "negative": (
            "3D render, CGI, glossy, plastic shiny, neon green, "
            "oversaturated Halloween colors, electric orange, "
            "photorealistic, sharp hyperdetailed, 8k, HDR, "
            "vector clipart, flat cartoon, dark solid background"
        ),
        "guidance": 4.5,
        "steps": 32,
    },

    "☕ Cozy Autumn Illustration": {
        "positive": (
            "cozy autumn watercolor illustration, DTF transfer print art, "
            "warm coffee shop aesthetic, muted earthy palette "
            "(burnt sienna, warm taupe, mustard, forest green), "
            "hand-painted cups and leaves and botanicals, "
            "soft texture like colored pencil over watercolor, "
            "hygge farmhouse style, clean white background"
        ),
        "negative": (
            "3D, glossy, shiny, photorealistic, neon, vibrant saturated, "
            "digital cartoon, clipart, vector, flat, sharp, 8k, HDR, "
            "complex busy background"
        ),
        "guidance": 4.5,
        "steps": 28,
    },

    "🖋️ Vintage Ink Linework": {
        "positive": (
            "vintage hand-drawn ink illustration, fine pen linework, "
            "cross-hatching and stippling texture, single color or two-tone, "
            "aged sepia or black ink on cream paper texture, "
            "etching engraving style, artisan craft aesthetic, "
            "apparel graphic print, clean white background"
        ),
        "negative": (
            "color fill, watercolor, 3D, glossy, photorealistic, "
            "neon colors, digital art, vector, flat design, "
            "sharp focus photography, 8k, HDR, busy background"
        ),
        "guidance": 5.5,
        "steps": 30,
    },

    "🌻 Teacher Appreciation POD": {
        "positive": (
            "cute hand-drawn teacher appreciation t-shirt graphic, "
            "watercolor illustration style, soft classroom motifs "
            "(apple pencil book ruler chalkboard), "
            "warm palette (coral red, golden yellow, sage green, cream), "
            "whimsical folk art lettering, boutique Etsy print quality, "
            "clean white background"
        ),
        "negative": (
            "3D, glossy, clipart, vector, neon, photorealistic, "
            "sharp digital, oversaturated, busy background, 8k, HDR"
        ),
        "guidance": 4.5,
        "steps": 28,
    },

    "✏️ None / Manual (Custom Only)": {
        "positive": "",
        "negative": "",
        "guidance": 7.0,
        "steps": 25,
    },
}

# ── POD-tuned Negative Presets (always block the "digital cartoon" look) ────
NEGATIVE_BLOCKS: dict[str, str] = {
    "🚫 Anti-Glossy/3D (Always On)":
        "3D render, glossy finish, plastic sheen, shiny, CGI, octane render, "
        "blender render, subsurface scattering, photorealistic render",
    "🚫 Anti-Neon/Oversaturated":
        "neon colors, oversaturated, electric colors, vibrant saturated, "
        "fluorescent, garish palette",
    "🚫 Anti-Digital Clipart":
        "vector art, flat design, clipart, digital illustration, "
        "cartoon network style, thick black outlines only",
    "🚫 Anti-Garbled Text":
        "text, letters, words, typography, writing, script, "
        "font, label, inscription, misspelled words",
    "🚫 Anti-Complex Background":
        "busy background, complex background, gradient background, "
        "dark background, solid colored background",
    "🚫 Anti-Low Quality":
        "blurry, low quality, pixelated, jpeg artifacts, "
        "watermark, signature, draft quality",
}

# ── Single Design composition helpers ────────────────────────────────────────
SINGLE_DESIGN_INJECT = (
    "single centered graphic design, isolated on white background, "
    "one cohesive composition, no grid layout, no collage, "
    "no multiple panels, no sheet of designs"
)

# ── Text legibility helper (only used when user wants text in design) ────────
TEXT_LEGIBILITY_INJECT = (
    "clean hand-lettered text, legible vintage typography, "
    "clear readable letters, well-spaced lettering"
)

# ── Style Transfer (img2img) palette extraction ──────────────────────────────
STYLE_TRANSFER_INJECT = (
    "extract and preserve the color palette and texture style from the reference image, "
    "maintain muted earthy tones and painterly texture, "
    "apply the same artistic medium (watercolor/screenprint) to new subject, "
    "do not add neon or saturated colors, preserve vintage aesthetic"
)

# ============================================================================
# 4.  CSS
# ============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #09090e; color: #dde1f0; }

.app-header {
    background: linear-gradient(135deg,#14100a 0%,#1a120d 50%,#0f1008 100%);
    border: 1px solid #2e2218;
    border-radius: 18px; padding: 28px 36px; margin-bottom: 20px;
    position: relative; overflow: hidden;
}
.app-header::after {
    content:''; position:absolute; top:-60px; right:-60px;
    width:220px; height:220px;
    background:radial-gradient(circle,rgba(180,120,60,.18) 0%,transparent 70%);
}
.app-header h1 {
    font-family:'Space Grotesk',sans-serif;
    font-size:2rem; font-weight:700; color:#f0e8d8;
    margin:0 0 6px; letter-spacing:-0.5px;
}
.app-header p { color:#7a6e5a; font-size:.91rem; margin:0; }
.header-badge {
    display:inline-block;
    background:rgba(180,120,60,.18); border:1px solid rgba(180,120,60,.4);
    color:#c8956a; font-size:.7rem; font-weight:600;
    padding:3px 11px; border-radius:20px; margin-bottom:10px;
    letter-spacing:.7px; text-transform:uppercase;
}

.section-card {
    background:#10100c; border:1px solid #221e14;
    border-radius:14px; padding:20px 22px; margin-bottom:14px;
}
.section-title {
    font-family:'Space Grotesk',sans-serif;
    font-size:.74rem; font-weight:700; color:#b87840;
    text-transform:uppercase; letter-spacing:1.2px; margin-bottom:12px;
}

[data-testid="stSidebar"] {
    background:#07070a !important;
    border-right:1px solid #1a1712 !important;
}

.profile-card {
    background:linear-gradient(150deg,#14100a,#0f0c08);
    border:1px solid #2a2018; border-radius:14px;
    padding:20px; text-align:center; margin-bottom:18px;
}
.profile-avatar { font-size:2.4rem; margin-bottom:7px; }
.profile-name {
    font-family:'Space Grotesk',sans-serif;
    font-weight:600; font-size:.96rem; color:#f0e8d8; margin-bottom:4px;
}
.profile-role { font-size:.75rem; color:#b87840; margin-bottom:10px; }
.profile-stat {
    display:inline-block;
    background:rgba(180,120,60,.1); border:1px solid rgba(180,120,60,.22);
    color:#c8956a; font-size:.7rem;
    padding:3px 8px; border-radius:7px; margin:2px;
}

.stButton > button {
    background:linear-gradient(135deg,#8b5e28,#5c3a18);
    color:#f5ead8; border:none; border-radius:10px;
    font-family:'Space Grotesk',sans-serif;
    font-weight:600; font-size:1rem;
    padding:13px 28px; width:100%;
    transition:filter .18s, transform .12s;
}
.stButton > button:hover { filter:brightness(1.15); transform:translateY(-1px); }

.enhanced-box {
    background:#0c0a06; border:1px solid #2e2010;
    border-left:3px solid #b87840; border-radius:10px;
    padding:13px 17px; font-size:.84rem; color:#9a8870;
    line-height:1.65; font-style:italic; margin-top:8px;
}

.preset-info-box {
    background:#0e0c08; border:1px solid #2a2010;
    border-radius:9px; padding:12px 15px; margin-top:8px;
    font-size:.81rem; color:#8a7a60; line-height:1.6;
}
.preset-info-box strong { color:#c8956a; }

.mode-badge {
    display:inline-block;
    background:rgba(180,120,60,.15); border:1px solid rgba(180,120,60,.35);
    color:#c8a060; font-size:.76rem; font-weight:600;
    padding:4px 12px; border-radius:8px; margin-bottom:8px;
}

.onboard-banner {
    background:linear-gradient(135deg,#141008,#0e0c06);
    border:1px solid #2a2010; border-radius:14px;
    padding:28px 32px; text-align:center; margin:20px 0;
}
.onboard-banner h2 {
    font-family:'Space Grotesk',sans-serif;
    font-size:1.35rem; font-weight:700; color:#f0e8d8; margin:0 0 8px;
}
.onboard-banner p { color:#6a6050; margin:0 0 16px; font-size:.91rem; }
.onboard-step {
    display:inline-block;
    background:rgba(180,120,60,.1); border:1px solid rgba(180,120,60,.3);
    color:#b89060; font-size:.78rem; padding:5px 13px;
    border-radius:8px; margin:3px;
}

.pill-ok {
    display:inline-flex; align-items:center; gap:5px;
    background:rgba(16,185,129,.1); border:1px solid rgba(16,185,129,.25);
    color:#34d399; font-size:.74rem; font-weight:600;
    padding:4px 13px; border-radius:20px;
}
.pill-err {
    display:inline-flex; align-items:center; gap:5px;
    background:rgba(239,68,68,.1); border:1px solid rgba(239,68,68,.25);
    color:#f87171; font-size:.74rem; font-weight:600;
    padding:4px 13px; border-radius:20px;
}

.token-hint {
    background:#0a0906; border:1px solid #221c0e;
    border-radius:8px; padding:10px 14px;
    font-size:.79rem; color:#5a5040; margin-top:6px; line-height:1.5;
}
.token-hint a { color:#b87840; text-decoration:none; }
.token-hint a:hover { text-decoration:underline; }

.stTextArea textarea {
    background:#0a0906 !important; border:1px solid #2a2010 !important;
    border-radius:9px !important; color:#d8ceb8 !important;
}
.stTextArea textarea:focus {
    border-color:#b87840 !important;
    box-shadow:0 0 0 2px rgba(180,120,60,.12) !important;
}

#MainMenu, footer, header { visibility:hidden; }
.block-container { padding-top:1.4rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 5.  SESSION STATE
# ============================================================================
for _k, _v in {
    "generated_images": [],
    "generation_count": 0,
    "last_prompt_used": "",
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ============================================================================
# 6.  PROMPT BUILDER — Etsy POD focused
# ============================================================================
def build_etsy_prompt(
    user_idea: str,
    preset_key: str,
    single_design_mode: bool,
    include_text_hint: bool,
    text_content: str,
    extra_descriptors: str,
) -> tuple[str, str, float, int]:
    """
    Returns (positive_prompt, negative_prompt, guidance_scale, steps).

    CORE RULE: We do NOT inject 8K, ultra-detailed, sharp, HDR, vibrant.
    Instead we describe the medium, texture, palette, and feel.
    """
    preset = ETSY_STYLE_PRESETS.get(preset_key, ETSY_STYLE_PRESETS["✏️ None / Manual (Custom Only)"])
    preset_pos = preset["positive"]
    preset_neg = preset["negative"]
    guidance   = preset["guidance"]
    steps      = preset["steps"]

    # ── Positive prompt assembly ──────────────────────────────────────────
    parts = []

    # 1. Single design composition lock (prevents grid garble)
    if single_design_mode:
        parts.append(SINGLE_DESIGN_INJECT)

    # 2. User's core idea
    if user_idea.strip():
        parts.append(user_idea.strip().rstrip(","))

    # 3. Text content (if user wants readable text in design)
    if include_text_hint and text_content.strip():
        parts.append(f'with clean legible text reading "{text_content.strip()}"')
        parts.append(TEXT_LEGIBILITY_INJECT)

    # 4. Style preset (the main visual DNA)
    if preset_pos:
        parts.append(preset_pos)

    # 5. Extra user descriptors
    if extra_descriptors.strip():
        parts.append(extra_descriptors.strip())

    positive = ", ".join(parts)

    # ── Negative prompt assembly ──────────────────────────────────────────
    neg_parts = []
    if preset_neg:
        neg_parts.append(preset_neg)
    # Always add anti-garbled-text block when user wants text
    if include_text_hint:
        # Paradox note: we allow "text" in pos but block "garbled" in neg
        neg_parts.append(
            "garbled text, illegible text, distorted letters, "
            "misspelled words, AI gibberish text, random symbols"
        )
    else:
        # No text at all wanted
        neg_parts.append(
            "text, letters, words, typography, writing, script, font, label"
        )

    negative = ", ".join(neg_parts)
    return positive, negative, guidance, steps


def build_i2i_style_transfer_prompt(
    user_idea: str,
    preset_key: str,
    single_design_mode: bool,
) -> tuple[str, str, float, int]:
    """Specialized prompt for img2img style transfer from reference."""
    preset = ETSY_STYLE_PRESETS.get(preset_key, ETSY_STYLE_PRESETS["✏️ None / Manual (Custom Only)"])

    parts = []
    if single_design_mode:
        parts.append(SINGLE_DESIGN_INJECT)
    parts.append(STYLE_TRANSFER_INJECT)
    if user_idea.strip():
        parts.append(user_idea.strip())
    if preset["positive"]:
        parts.append(preset["positive"])

    neg_parts = [
        "3D render, glossy, plastic, shiny, photorealistic, CGI, neon, "
        "oversaturated, sharp focus, 8k, HDR, vector clipart, "
        "garbled text, illegible letters, AI text artifacts"
    ]
    if preset["negative"]:
        neg_parts.append(preset["negative"])

    return (
        ", ".join(parts),
        ", ".join(neg_parts),
        preset["guidance"],
        preset["steps"],
    )

# ============================================================================
# 7.  IMAGE UTILITIES
# ============================================================================
def pil_to_b64_uri(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return f"data:image/{'png' if fmt=='PNG' else 'jpeg'};base64,{base64.b64encode(buf.getvalue()).decode()}"

def pil_to_bytes_io(img: Image.Image) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def url_to_pil(url: str) -> Image.Image:
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def build_grid_reference(images: list, tile: int = 512) -> Image.Image:
    cols = 2 if len(images) > 1 else 1
    rows = (len(images) + 1) // 2
    grid = Image.new("RGB", (tile * cols, tile * rows), (255, 255, 255))
    for i, img in enumerate(images[:4]):
        grid.paste(img.resize((tile, tile), Image.LANCZOS),
                   ((i % cols) * tile, (i // cols) * tile))
    return grid

# ============================================================================
# 8.  GENERATION — REPLICATE
# ============================================================================
def _rep_client(token: str):
    try:
        import replicate as _r
        return _r.Client(api_token=token)
    except ImportError:
        raise ImportError("Add `replicate` to requirements.txt")

def gen_replicate_t2i(token, prompt, negative, width, height, num, steps, guidance):
    client = _rep_client(token)
    out = client.run(
        REPLICATE_T2I_MODEL,
        input={
            "prompt": prompt,
            "width": width, "height": height,
            "num_outputs": num,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        },
    )
    return [url_to_pil(str(x)) for x in out]

def gen_replicate_i2i(token, prompt, negative, ref_img, strength, width, height, num, steps, guidance):
    client = _rep_client(token)
    ref = ref_img.resize((width, height), Image.LANCZOS)
    out = client.run(
        REPLICATE_I2I_MODEL,
        input={
            "prompt": prompt,
            "image": pil_to_b64_uri(ref, "PNG"),
            "prompt_strength": strength,
            "width": width, "height": height,
            "num_outputs": num,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        },
    )
    return [url_to_pil(str(x)) for x in out]

# ============================================================================
# 9.  GENERATION — HUGGING FACE
# ============================================================================
def _hf_post(url, token, payload, retries=3):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for attempt in range(retries):
        r = requests.post(url, headers=headers, json=payload, timeout=180)
        if r.status_code == 200:
            return r.content
        if r.status_code == 503:
            wait = min(float(r.json().get("estimated_time", 30)), 60)
            time.sleep(wait)
            continue
        raise RuntimeError(f"HF {r.status_code}: {r.text[:250]}")
    raise RuntimeError("HF model still loading — retry in ~1 min.")

def gen_hf_t2i(token, prompt, negative, width, height, num, steps, guidance):
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": negative,
            "width": width, "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        },
    }
    results = []
    for _ in range(num):
        raw = _hf_post(HF_T2I_URL, token, payload)
        results.append(Image.open(io.BytesIO(raw)).convert("RGB"))
    return results

def gen_hf_i2i(token, prompt, negative, ref_img, strength, width, height, num, steps, guidance):
    ref = ref_img.resize((width, height), Image.LANCZOS)
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": negative,
            "image": pil_to_b64_uri(ref, "JPEG"),
            "strength": strength,
            "width": width, "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        },
    }
    results = []
    for _ in range(num):
        raw = _hf_post(HF_I2I_URL, token, payload)
        results.append(Image.open(io.BytesIO(raw)).convert("RGB"))
    return results

# ============================================================================
# 10.  SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("""
    <div class="profile-card">
        <div class="profile-avatar">🌾</div>
        <div class="profile-name">Special Pixel Studio</div>
        <div class="profile-role">Etsy POD Design Studio</div>
        <span class="profile-stat">v4.0 POD</span>
        <span class="profile-stat">Etsy Edition</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### ⚙️ API Setup")
    api_provider = st.selectbox(
        "Provider",
        ["Replicate — FLUX.1 (Recommended)", "Hugging Face — SDXL (Free)"],
    )
    use_replicate = "Replicate" in api_provider

    if use_replicate:
        rep_in = st.text_input("Replicate Token", value=_REPLICATE_TOKEN,
                               type="password", placeholder="r8_...")
        ACTIVE_TOKEN = rep_in.strip() or _REPLICATE_TOKEN
        st.markdown("""<div class="token-hint">
            🔑 <a href="https://replicate.com/account/api-tokens" target="_blank">
            replicate.com/account/api-tokens</a><br>
            💡 Streamlit Cloud: add <code>REPLICATE_API_TOKEN</code> in Secrets.
        </div>""", unsafe_allow_html=True)
    else:
        hf_in = st.text_input("HF Token", value=_HF_TOKEN,
                              type="password", placeholder="hf_...")
        ACTIVE_TOKEN = hf_in.strip() or _HF_TOKEN
        st.markdown("""<div class="token-hint">
            🔑 <a href="https://huggingface.co/settings/tokens" target="_blank">
            huggingface.co/settings/tokens</a><br>
            💡 Add <code>HF_API_TOKEN</code> in Streamlit Secrets.
        </div>""", unsafe_allow_html=True)

    token_ready = bool(ACTIVE_TOKEN)

    st.divider()
    st.markdown("#### 🖼️ Output Settings")
    num_outputs = st.slider("Variations", 1, 4, 2)

    res_choice = st.selectbox("Resolution", [
        "1024 × 1024  (Square — DTF/Sublimation)",
        "1200 × 1200  (Large Square — Print)",
        "768  × 1024  (Portrait — Apparel)",
        "1024 × 768   (Landscape)",
        "512  × 512   (Fast Preview)",
    ])
    _RES = {
        "1024 × 1024  (Square — DTF/Sublimation)": (1024, 1024),
        "1200 × 1200  (Large Square — Print)":     (1200, 1200),
        "768  × 1024  (Portrait — Apparel)":        (768,  1024),
        "1024 × 768   (Landscape)":                 (1024, 768),
        "512  × 512   (Fast Preview)":              (512,  512),
    }
    OUT_W, OUT_H = _RES[res_choice]

    st.divider()
    st.markdown("#### 📊 Session")
    st.metric("Designs Generated", st.session_state.generation_count)


# ============================================================================
# 11.  HEADER
# ============================================================================
st.markdown("""
<div class="app-header">
    <div class="header-badge">🌾 ETSY POD EDITION</div>
    <h1>DesignCreationHub</h1>
    <p>Watercolor · Vintage Screenprint · Boho · Cottagecore — Tuned for Etsy & Print-on-Demand</p>
</div>
""", unsafe_allow_html=True)

if not token_ready:
    st.markdown("""
    <div class="onboard-banner">
        <h2>🔑 One step away from generating</h2>
        <p>Add your API token in the sidebar to start creating Etsy-ready designs.</p>
        <span class="onboard-step">1 · Open sidebar</span>
        <span class="onboard-step">2 · Paste Replicate token (free)</span>
        <span class="onboard-step">3 · Pick a POD preset</span>
        <span class="onboard-step">4 · Generate ✨</span>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# 12.  TABS
# ============================================================================
tab_t2i, tab_i2i, tab_gallery = st.tabs([
    "✍️  Text → Design",
    "🔄  Style Transfer (Img2Img)",
    "🖼️  Gallery",
])

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 1 — TEXT TO DESIGN                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab_t2i:
    col_l, col_r = st.columns([1.2, 0.8], gap="large")

    with col_l:
        # ── Preset selector ────────────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🎨 Etsy POD Style Preset</div>', unsafe_allow_html=True)

        preset_key = st.selectbox(
            "Choose your market style",
            list(ETSY_STYLE_PRESETS.keys()),
            label_visibility="collapsed",
        )
        sel_preset = ETSY_STYLE_PRESETS[preset_key]

        # Show preset info box
        if sel_preset["positive"]:
            preview = sel_preset["positive"][:180] + "…"
            st.markdown(f"""
            <div class="preset-info-box">
                <strong>Style DNA injected:</strong><br>{preview}
            </div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Design idea input ──────────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">✦ Your Design Idea</div>', unsafe_allow_html=True)

        user_idea = st.text_area(
            "Design idea",
            placeholder=(
                "e.g.  cute ghost holding a coffee cup surrounded by sunflowers and pumpkins\n"
                "e.g.  highland cow wearing a witch hat with autumn leaves\n"
                "e.g.  skeleton reading a book with candles and cobwebs"
            ),
            height=110,
            label_visibility="collapsed",
        )

        extra_desc = st.text_input(
            "Extra style descriptors (optional)",
            placeholder="e.g. buffalo check ribbon, dried botanicals, stars...",
        )

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Single Design Mode + Text ──────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📐 Composition & Text Options</div>', unsafe_allow_html=True)

        single_mode = st.toggle(
            "Single Design Mode",
            value=True,
            help=(
                "ON (recommended): generates ONE centered design — prevents the "
                "garbled multi-panel grid sheet that breaks text legibility.\n"
                "OFF: lets FLUX freely compose (may produce grid layouts)."
            ),
        )
        if single_mode:
            st.markdown('<span class="mode-badge">✓ Single centered design — no grid collage</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="mode-badge" style="opacity:.6">⚠ Free composition — may produce grid</span>', unsafe_allow_html=True)

        include_text = st.toggle(
            "Include readable text in design",
            value=False,
            help=(
                "When ON, type the exact text you want (e.g. 'Ghost Coffee Club'). "
                "The prompt is engineered to maximise legibility. "
                "Note: FLUX.1 text generation is imperfect — "
                "for perfect typography use your design software on top of the AI art."
            ),
        )

        design_text = ""
        if include_text:
            design_text = st.text_input(
                "Text to include in design",
                placeholder="e.g.  Ghost Coffee Club",
                help="Keep it short (1–4 words) for best legibility with AI models.",
            )
            if design_text and len(design_text.split()) > 5:
                st.warning("⚠️ AI models struggle with long text. Keep to 1–4 words for best results. Add longer text in Canva/Photoshop after.")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Additional negative overrides ──────────────────────────────────
        with st.expander("🚫 Advanced Negative Overrides", expanded=False):
            extra_neg_blocks = st.multiselect(
                "Add more negative blocks",
                list(NEGATIVE_BLOCKS.keys()),
                default=["🚫 Anti-Glossy/3D (Always On)", "🚫 Anti-Neon/Oversaturated"],
            )
            custom_extra_neg = st.text_input(
                "Custom negatives",
                placeholder="e.g.  dark background, border frame...",
            )

        # ── Live prompt preview ────────────────────────────────────────────
        if user_idea.strip() or preset_key != "✏️ None / Manual (Custom Only)":
            pos, neg, guidance_val, steps_val = build_etsy_prompt(
                user_idea, preset_key, single_mode, include_text, design_text, extra_desc
            )
            # Merge extra negatives
            extra_neg_str = ", ".join([NEGATIVE_BLOCKS[k] for k in extra_neg_blocks])
            if custom_extra_neg:
                extra_neg_str += ", " + custom_extra_neg
            if extra_neg_str:
                neg = neg + ", " + extra_neg_str

            st.markdown(f"""
            <div class="enhanced-box">
                🌾 <strong>Final prompt:</strong> {pos[:300]}{'…' if len(pos)>300 else ''}
            </div>""", unsafe_allow_html=True)
        else:
            pos, neg, guidance_val, steps_val = "", "", 7.0, 25

    with col_r:
        st.markdown("#### Generate")
        gen_btn = st.button("🌾 Generate Etsy Design", key="btn_t2i", use_container_width=True)

        if gen_btn:
            if not user_idea.strip() and not sel_preset["positive"]:
                st.warning("✏️ Enter a design idea to get started.")
            elif not token_ready:
                st.warning("🔑 Add your API token in the sidebar first.")
            else:
                # Build final prompts now
                pos, neg, guidance_val, steps_val = build_etsy_prompt(
                    user_idea, preset_key, single_mode, include_text, design_text, extra_desc
                )
                extra_neg_str = ", ".join([NEGATIVE_BLOCKS.get(k,"") for k in extra_neg_blocks])
                if custom_extra_neg:
                    extra_neg_str += ", " + custom_extra_neg
                if extra_neg_str:
                    neg = neg + ", " + extra_neg_str

                st.session_state.last_prompt_used = (user_idea or preset_key)[:80]

                with st.spinner("🎨 Creating your design — ~20–45s..."):
                    try:
                        if use_replicate:
                            imgs = gen_replicate_t2i(
                                ACTIVE_TOKEN, pos, neg,
                                OUT_W, OUT_H, num_outputs,
                                steps_val, guidance_val,
                            )
                        else:
                            imgs = gen_hf_t2i(
                                ACTIVE_TOKEN, pos, neg,
                                OUT_W, OUT_H, num_outputs,
                                steps_val, guidance_val,
                            )

                        st.session_state.generated_images = imgs
                        st.session_state.generation_count += len(imgs)
                        st.markdown('<span class="pill-ok">✓ Design ready!</span>', unsafe_allow_html=True)

                    except Exception as e:
                        st.markdown(f'<span class="pill-err">✗ {str(e)[:120]}</span>', unsafe_allow_html=True)
                        with st.expander("Error details"):
                            st.exception(e)

        if st.session_state.generated_images:
            st.markdown("---")
            _imgs = st.session_state.generated_images
            _c = st.columns(min(2, len(_imgs)))
            for i, img in enumerate(_imgs):
                with _c[i % 2]:
                    st.image(img, use_container_width=True, caption=f"Variation {i+1}")
                    st.download_button(
                        f"⬇ PNG V{i+1}", data=pil_to_bytes_io(img),
                        file_name=f"etsy_design_v{i+1}.png", mime="image/png",
                        key=f"dl_t2i_{i}", use_container_width=True,
                    )


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 2 — STYLE TRANSFER (IMG2IMG)                                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab_i2i:
    st.markdown("""
    <div class="preset-info-box" style="margin-bottom:16px">
        <strong>How Style Transfer works here:</strong>
        Upload a reference design (like your competitor's Etsy listing).
        The AI extracts its <em>color palette, texture, and artistic medium</em>
        and applies them to your new subject — without copying the original art.
        Keep <strong>Reference Influence low (0.3–0.5)</strong> for best style transfer.
    </div>
    """, unsafe_allow_html=True)

    col_il, col_ir = st.columns([1.1, 0.9], gap="large")

    with col_il:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📎 Reference Upload</div>', unsafe_allow_html=True)

        upload_mode = st.radio(
            "Mode", ["Single Reference Image", "Style Composite (2–4 images)"],
            horizontal=True,
        )
        ref_pil = None

        if upload_mode == "Single Reference Image":
            uf = st.file_uploader(
                "Upload reference (competitor design, mood board, etc.)",
                type=["png","jpg","jpeg","webp"], key="uf_s",
            )
            if uf:
                ref_pil = Image.open(uf).convert("RGB")
                st.image(ref_pil, caption="Reference", use_container_width=True)
        else:
            uf_m = st.file_uploader(
                "Upload 2–4 reference images",
                type=["png","jpg","jpeg","webp"],
                accept_multiple_files=True, key="uf_m",
            )
            if uf_m:
                raw = [Image.open(f).convert("RGB") for f in uf_m[:4]]
                ref_pil = build_grid_reference(raw)
                st.image(ref_pil, caption=f"Style Composite ({len(raw)} imgs)", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🎨 Your New Design Idea</div>', unsafe_allow_html=True)

        i2i_idea = st.text_area(
            "What new design should be created in the reference style?",
            placeholder=(
                "e.g.  highland cow wearing a witch hat with sunflowers\n"
                "e.g.  cute skeleton reading spellbook surrounded by candles"
            ),
            height=90, label_visibility="collapsed",
        )

        i2i_preset = st.selectbox(
            "Style Preset",
            list(ETSY_STYLE_PRESETS.keys()), key="i2i_preset_sel",
        )

        i2i_single = st.toggle("Single Design Mode", value=True, key="i2i_single")

        st.markdown("---")
        st.markdown("**Reference Influence Slider**")
        img_strength = st.slider(
            "Reference Influence",
            min_value=0.1, max_value=0.9, value=0.35, step=0.05,
            label_visibility="collapsed",
            help=(
                "0.1–0.3 = strong style copy (palette + texture extracted)\n"
                "0.35–0.55 = balanced blend\n"
                "0.6–0.9 = loose reference, prompt dominates"
            ),
        )

        # Influence guide
        if img_strength <= 0.30:
            st.info("🎨 **Style Extract** — Pulls palette & texture closely from reference")
        elif img_strength <= 0.55:
            st.info("⚖️ **Balanced** — Blends reference style with your design idea")
        else:
            st.info("💥 **Creative** — Reference loosely guides; preset style drives output")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_ir:
        st.markdown("#### Style Transfer")
        i2i_btn = st.button("🔄 Transfer Style", key="btn_i2i", use_container_width=True)

        if i2i_btn:
            if ref_pil is None:
                st.warning("📎 Upload a reference image first.")
            elif not i2i_idea.strip():
                st.warning("✏️ Describe the new design subject.")
            elif not token_ready:
                st.warning("🔑 Add your API token in the sidebar.")
            else:
                i2i_pos, i2i_neg, i2i_guid, i2i_steps = build_i2i_style_transfer_prompt(
                    i2i_idea, i2i_preset, i2i_single
                )

                with st.spinner("🔄 Extracting style and generating — ~30–60s..."):
                    try:
                        if use_replicate:
                            imgs = gen_replicate_i2i(
                                ACTIVE_TOKEN, i2i_pos, i2i_neg,
                                ref_pil, img_strength,
                                OUT_W, OUT_H, num_outputs,
                                i2i_steps, i2i_guid,
                            )
                        else:
                            imgs = gen_hf_i2i(
                                ACTIVE_TOKEN, i2i_pos, i2i_neg,
                                ref_pil, img_strength,
                                OUT_W, OUT_H, num_outputs,
                                i2i_steps, i2i_guid,
                            )

                        st.session_state.generated_images = imgs
                        st.session_state.generation_count += len(imgs)
                        st.markdown('<span class="pill-ok">✓ Style transfer done!</span>', unsafe_allow_html=True)

                    except Exception as e:
                        st.markdown(f'<span class="pill-err">✗ {str(e)[:120]}</span>', unsafe_allow_html=True)
                        with st.expander("Error details"):
                            st.exception(e)

        if st.session_state.generated_images:
            st.markdown("---")
            _imgs = st.session_state.generated_images
            _c = st.columns(min(2, len(_imgs)))
            for i, img in enumerate(_imgs):
                with _c[i % 2]:
                    st.image(img, use_container_width=True, caption=f"Transfer {i+1}")
                    st.download_button(
                        f"⬇ PNG {i+1}", data=pil_to_bytes_io(img),
                        file_name=f"style_transfer_{i+1}.png", mime="image/png",
                        key=f"dl_i2i_{i}", use_container_width=True,
                    )

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 3 — GALLERY                                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab_gallery:
    _all = st.session_state.generated_images
    if not _all:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;color:#3a3020">
            <div style="font-size:2.5rem">🌾</div>
            <p style="margin-top:12px;font-size:.92rem;color:#4a4030">
                Your generated designs will collect here during this session.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        c1, c2 = st.columns([3,1])
        with c1:
            st.markdown(f"#### Session Gallery · {len(_all)} design{'s' if len(_all)!=1 else ''}")
        with c2:
            if st.button("🗑️ Clear", key="clr"):
                st.session_state.generated_images = []
                st.rerun()

        ncols = min(3, len(_all))
        gcols = st.columns(ncols)
        for i, img in enumerate(_all):
            with gcols[i % ncols]:
                st.image(img, use_container_width=True)
                st.download_button(
                    "⬇ Download PNG", data=pil_to_bytes_io(img),
                    file_name=f"etsy_design_{i+1}.png", mime="image/png",
                    key=f"dl_g_{i}", use_container_width=True,
                )
