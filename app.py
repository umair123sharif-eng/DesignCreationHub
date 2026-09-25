"""
DesignCreationHub — Production-Ready AI Image Generation Studio v3.0
Author : Special Pixel Studio (Sharif)
Fix log: v3 — secrets-first token loading, lazy replicate import,
          correct FLUX img2img endpoint, HF SDXL img2img via diffusers
          endpoint, graceful no-token onboarding screen.
"""

# ── stdlib ──────────────────────────────────────────────────────────────────
import base64
import io
import os
import time

# ── third-party ─────────────────────────────────────────────────────────────
import requests
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter

# ============================================================================
# 0.  PAGE CONFIG  (must be first Streamlit call)
# ============================================================================
st.set_page_config(
    page_title="DesignCreationHub",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# 1.  TOKEN RESOLUTION  — secrets → env → sidebar input
#     Priority: st.secrets > os.environ > user input in sidebar
#     This is the fix for the "API token missing" crash on Streamlit Cloud.
# ============================================================================
def _load_secret(key: str) -> str:
    """Read from st.secrets first, then os.environ, return '' if absent."""
    try:
        val = st.secrets.get(key, "")
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(key, "")


_REPLICATE_TOKEN_FROM_ENV = _load_secret("REPLICATE_API_TOKEN")
_HF_TOKEN_FROM_ENV        = _load_secret("HF_API_TOKEN")

# ============================================================================
# 2.  CONSTANTS
# ============================================================================
# Replicate — FLUX.1 Schnell (free, fast) for txt2img
REPLICATE_T2I_MODEL  = "black-forest-labs/flux-schnell"
# Replicate — FLUX.1 Dev img2img (correct endpoint for image input)
REPLICATE_I2I_MODEL  = "black-forest-labs/flux-dev"

# HuggingFace endpoints
HF_T2I_URL   = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
HF_I2I_URL   = "https://api-inference.huggingface.co/models/diffusers/stable-diffusion-xl-1.0-img2img"

STYLE_PRESETS: dict[str, str] = {
    "None / Custom": "",
    "🎨 Concept Art": "concept art, digital painting, vibrant colors, artstation trending, cinematic composition",
    "📸 Hyperrealistic Photo": "hyperrealistic DSLR photograph, 50mm lens, f/1.8, sharp focus, studio lighting, Canon EOS R5",
    "🖼️ Oil Painting": "oil painting on canvas, classical art, textured impasto brushstrokes, museum quality, old masters",
    "🌆 Cyberpunk City": "cyberpunk aesthetic, neon-lit rain-soaked streets, holographic billboards, blade runner 2049 style",
    "🌿 Studio Ghibli": "Studio Ghibli anime style, soft watercolor, whimsical pastoral, Miyazaki, hand-drawn",
    "⚡ Anime Illustration": "anime key visual, cel shading, vibrant saturated colors, detailed linework, manga-inspired",
    "🏺 3D Octane Render": "3D render, Octane render, ray tracing, subsurface scattering, Cinema 4D, volumetric fog",
    "🖋️ Ink & Pen": "ink wash illustration, fine pen linework, cross-hatching, black and white, graphic novel art",
    "✨ Dark Fantasy": "dark fantasy epic, ethereal glow, dramatic fog, intricate filigree armor, concept art",
    "🌸 Soft Pastel": "soft pastel palette, dreamy illustration, watercolor washes, gentle bokeh, cottagecore",
    "🔥 Logo & Brand Mark": "minimalist vector logo, clean geometric shapes, flat design, brand identity, white background",
}

NEGATIVE_PRESETS: dict[str, str] = {
    "Quality Fix":      "blurry, low quality, pixelated, jpeg artifacts, compression artifacts, grainy",
    "No Watermarks":    "watermark, signature, text overlay, logo stamp, copyright mark",
    "No Deformities":   "distorted anatomy, deformed hands, extra fingers, mutated limbs, disfigured face",
    "Clean BG":         "cluttered background, busy background, distracting elements, noise, busy pattern",
    "No AI Glitches":   "uncanny valley, plastic skin, oversaturated, unnatural color, AI artifact",
    "No People":        "person, human, face, hands, crowd, silhouette",
}

CAMERA_ANGLES = [
    "auto-selected", "eye-level shot", "bird's eye view", "worm's eye view",
    "dutch angle", "extreme close-up", "medium shot", "wide establishing shot",
    "over-the-shoulder", "aerial top-down", "three-quarter view",
]

LIGHTING_STYLES = [
    "auto-selected", "golden hour sunlight", "studio softbox lighting", "rim backlight",
    "volumetric god rays", "cinematic three-point lighting", "dramatic chiaroscuro shadows",
    "soft diffused overcast", "neon RGB glow", "moonlit night", "product photography light",
]

QUALITY_TAGS_ALL = [
    "8K resolution", "ultra-detailed", "sharp focus", "HDR", "RAW photo",
    "intricate fine details", "award-winning photography", "professional color grading",
    "trending on artstation", "Unreal Engine 5 render", "depth of field", "bokeh",
    "perfect composition", "golden ratio", "hyper-sharp",
]

# ============================================================================
# 3.  CSS — Dark studio theme
# ============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #080a10; color: #dde1f0; }

/* ── Header ── */
.app-header {
    background: linear-gradient(135deg,#111425 0%,#0c1230 60%,#160d30 100%);
    border: 1px solid #252840;
    border-radius: 18px;
    padding: 30px 38px;
    margin-bottom: 22px;
    position: relative;
    overflow: hidden;
}
.app-header::after {
    content:''; position:absolute; top:-80px; right:-80px;
    width:260px; height:260px;
    background:radial-gradient(circle,rgba(99,87,255,.22) 0%,transparent 70%);
    pointer-events:none;
}
.app-header h1 {
    font-family:'Space Grotesk',sans-serif;
    font-size:2.1rem; font-weight:700; color:#fff;
    margin:0 0 6px; letter-spacing:-0.6px;
}
.app-header p { color:#7a82a0; font-size:.93rem; margin:0; }
.header-badge {
    display:inline-block;
    background:rgba(99,87,255,.18); border:1px solid rgba(99,87,255,.4);
    color:#a09bff; font-size:.7rem; font-weight:600;
    padding:3px 11px; border-radius:20px; margin-bottom:10px;
    letter-spacing:.6px; text-transform:uppercase;
}

/* ── Section cards ── */
.section-card {
    background:#10131e; border:1px solid #1c1f30;
    border-radius:14px; padding:20px 22px; margin-bottom:16px;
}
.section-title {
    font-family:'Space Grotesk',sans-serif;
    font-size:.75rem; font-weight:700; color:#6357ff;
    text-transform:uppercase; letter-spacing:1.1px; margin-bottom:12px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background:#08090f !important;
    border-right:1px solid #181a28 !important;
}

/* ── Profile card ── */
.profile-card {
    background:linear-gradient(150deg,#161928,#0f1120);
    border:1px solid #252840; border-radius:14px;
    padding:20px; text-align:center; margin-bottom:18px;
}
.profile-avatar { font-size:2.6rem; margin-bottom:7px; }
.profile-name {
    font-family:'Space Grotesk',sans-serif;
    font-weight:600; font-size:.98rem; color:#eef0f8; margin-bottom:4px;
}
.profile-role { font-size:.76rem; color:#6357ff; margin-bottom:10px; }
.profile-stat {
    display:inline-block;
    background:rgba(99,87,255,.1); border:1px solid rgba(99,87,255,.22);
    color:#a09bff; font-size:.7rem;
    padding:3px 8px; border-radius:7px; margin:2px;
}

/* ── Buttons ── */
.stButton > button {
    background:linear-gradient(135deg,#5a50ff,#8b3dca);
    color:#fff; border:none; border-radius:10px;
    font-family:'Space Grotesk',sans-serif;
    font-weight:600; font-size:1rem;
    padding:13px 28px; width:100%;
    transition:filter .18s,transform .12s;
    letter-spacing:.3px;
}
.stButton > button:hover { filter:brightness(1.12); transform:translateY(-1px); }
.stButton > button:active { transform:translateY(0); }

/* ── Enhanced prompt box ── */
.enhanced-box {
    background:#090d1c; border:1px solid #252f60;
    border-left:3px solid #6357ff; border-radius:10px;
    padding:13px 17px; font-size:.85rem; color:#a0aac4;
    line-height:1.65; font-style:italic; margin-top:8px;
}

/* ── Onboarding banner ── */
.onboard-banner {
    background:linear-gradient(135deg,#141830,#0e1228);
    border:1px solid #2a2f50; border-radius:14px;
    padding:28px 32px; text-align:center; margin:20px 0;
}
.onboard-banner h2 {
    font-family:'Space Grotesk',sans-serif;
    font-size:1.4rem; font-weight:700; color:#fff; margin:0 0 8px;
}
.onboard-banner p { color:#7a82a0; margin:0 0 18px; font-size:.93rem; }
.onboard-step {
    display:inline-block;
    background:rgba(99,87,255,.1); border:1px solid rgba(99,87,255,.3);
    color:#b0aaff; font-size:.8rem; padding:5px 14px;
    border-radius:8px; margin:4px;
}

/* ── Status pills ── */
.pill-ok {
    display:inline-flex; align-items:center; gap:6px;
    background:rgba(16,185,129,.12); border:1px solid rgba(16,185,129,.3);
    color:#34d399; font-size:.75rem; font-weight:600;
    padding:4px 13px; border-radius:20px;
}
.pill-err {
    display:inline-flex; align-items:center; gap:6px;
    background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.3);
    color:#f87171; font-size:.75rem; font-weight:600;
    padding:4px 13px; border-radius:20px;
}

/* ── Token input hint ── */
.token-hint {
    background:#0d1018; border:1px solid #2a3050;
    border-radius:9px; padding:11px 15px;
    font-size:.8rem; color:#6870a0; margin-top:6px;
    line-height:1.5;
}
.token-hint a { color:#7b72ff; text-decoration:none; }
.token-hint a:hover { text-decoration:underline; }

/* inputs */
.stTextArea textarea {
    background:#0c0e18 !important; border:1px solid #252840 !important;
    border-radius:9px !important; color:#dde1f0 !important;
}
.stTextArea textarea:focus {
    border-color:#6357ff !important;
    box-shadow:0 0 0 2px rgba(99,87,255,.15) !important;
}

/* hide default chrome */
#MainMenu, footer, header { visibility:hidden; }
.block-container { padding-top:1.4rem; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 4.  SESSION STATE
# ============================================================================
_STATE_DEFAULTS = {
    "generated_images":  [],
    "generation_count":  0,
    "last_prompt_used":  "",
    "last_enhanced":     "",
}
for _k, _v in _STATE_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ============================================================================
# 5.  HELPERS — prompt engineering
# ============================================================================
def enhance_prompt(
    base: str,
    style_chunk: str,
    camera: str,
    lighting: str,
    quality_tags: list[str],
) -> str:
    """Expand a simple prompt into a rich diffusion-ready prompt."""
    parts = [base.strip().rstrip(",")]
    if style_chunk:
        parts.append(style_chunk)
    if camera and "auto" not in camera:
        parts.append(camera)
    if lighting and "auto" not in lighting:
        parts.append(lighting)
    # Core quality block — always injected
    core_q = [
        "8K ultra-high resolution", "masterpiece quality", "sharp crisp focus",
        "professional color grading", "highly detailed", "best quality",
    ]
    parts.extend(core_q)
    parts.extend(quality_tags)
    return ", ".join(parts)


def build_negative(selected: list[str], custom: str) -> str:
    chunks = [NEGATIVE_PRESETS[k] for k in selected if k in NEGATIVE_PRESETS]
    if custom.strip():
        chunks.append(custom.strip())
    return ", ".join(chunks)


# ============================================================================
# 6.  HELPERS — image utilities
# ============================================================================
def pil_to_b64_uri(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode()
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def pil_to_bytes_io(img: Image.Image, fmt: str = "PNG") -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf


def build_grid_reference(images: list[Image.Image], tile: int = 512) -> Image.Image:
    """Composite up to 4 images into a 2×2 reference grid."""
    cols = 2 if len(images) > 1 else 1
    rows = (len(images) + 1) // 2
    grid = Image.new("RGB", (tile * cols, tile * rows), (8, 9, 16))
    for i, img in enumerate(images[:4]):
        thumb = img.resize((tile, tile), Image.LANCZOS)
        grid.paste(thumb, ((i % cols) * tile, (i // cols) * tile))
    return grid


def url_to_pil(url: str) -> Image.Image:
    """Download an image URL returned by Replicate into a PIL Image."""
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


# ============================================================================
# 7.  GENERATION — Replicate
#     Uses lazy import so the app loads even if replicate isn't installed yet.
# ============================================================================
def _replicate_client(token: str):
    """Return a replicate.Client; raises ImportError with a clear message."""
    try:
        import replicate as _rep
        return _rep.Client(api_token=token)
    except ImportError:
        raise ImportError(
            "replicate package not found. Add `replicate` to requirements.txt."
        )


def generate_replicate_t2i(
    token: str,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    num_outputs: int,
    steps: int,
    guidance: float,
) -> list[Image.Image]:
    client = _replicate_client(token)
    results = []
    output = client.run(
        REPLICATE_T2I_MODEL,
        input={
            "prompt": prompt,
            "width":  width,
            "height": height,
            "num_outputs": num_outputs,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            # flux-schnell does not accept negative_prompt param; skip silently
        },
    )
    for item in output:
        results.append(url_to_pil(str(item)))
    return results


def generate_replicate_i2i(
    token: str,
    prompt: str,
    ref_image: Image.Image,
    strength: float,       # 0.0 = copy image, 1.0 = ignore image
    width: int,
    height: int,
    num_outputs: int,
    steps: int,
    guidance: float,
) -> list[Image.Image]:
    """
    FLUX.1-dev supports image-to-image via the 'image' param + 'prompt_strength'.
    We resize the reference to target size before passing it.
    """
    client = _replicate_client(token)
    # Resize reference to match output resolution for best alignment
    ref_resized = ref_image.resize((width, height), Image.LANCZOS)
    img_uri = pil_to_b64_uri(ref_resized, "PNG")

    results = []
    output = client.run(
        REPLICATE_I2I_MODEL,
        input={
            "prompt":          prompt,
            "image":           img_uri,
            "prompt_strength": strength,   # FLUX.1-dev correct param name
            "width":           width,
            "height":          height,
            "num_outputs":     num_outputs,
            "num_inference_steps": steps,
            "guidance_scale":  guidance,
        },
    )
    for item in output:
        results.append(url_to_pil(str(item)))
    return results


# ============================================================================
# 8.  GENERATION — Hugging Face Inference API
# ============================================================================
def _hf_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _hf_wait_and_post(url: str, headers: dict, payload: dict, retries: int = 3) -> bytes:
    """Post to HF API, retry on 503 model-loading responses."""
    for attempt in range(retries):
        r = requests.post(url, headers=headers, json=payload, timeout=180)
        if r.status_code == 200:
            return r.content
        if r.status_code == 503:
            est = r.json().get("estimated_time", 30)
            wait = min(float(est), 60)
            time.sleep(wait)
            continue
        raise RuntimeError(f"HF API {r.status_code}: {r.text[:300]}")
    raise RuntimeError("HF model still loading after retries. Try again in ~1 min.")


def generate_hf_t2i(
    token: str,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    num_outputs: int,
    steps: int,
    guidance: float,
) -> list[Image.Image]:
    headers = _hf_headers(token)
    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": negative_prompt,
            "width":  width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            "num_images_per_prompt": 1,
        },
    }
    results = []
    for _ in range(num_outputs):
        raw = _hf_wait_and_post(HF_T2I_URL, headers, payload)
        results.append(Image.open(io.BytesIO(raw)).convert("RGB"))
    return results


def generate_hf_i2i(
    token: str,
    prompt: str,
    negative_prompt: str,
    ref_image: Image.Image,
    strength: float,
    width: int,
    height: int,
    num_outputs: int,
    steps: int,
    guidance: float,
) -> list[Image.Image]:
    headers = _hf_headers(token)
    ref_resized = ref_image.resize((width, height), Image.LANCZOS)
    img_b64 = pil_to_b64_uri(ref_resized, "JPEG")  # HF img2img needs JPEG

    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": negative_prompt,
            "image":    img_b64,
            "strength": strength,
            "width":    width,
            "height":   height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        },
    }
    results = []
    for _ in range(num_outputs):
        raw = _hf_wait_and_post(HF_I2I_URL, headers, payload)
        results.append(Image.open(io.BytesIO(raw)).convert("RGB"))
    return results


# ============================================================================
# 9.  SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("""
    <div class="profile-card">
        <div class="profile-avatar">🎨</div>
        <div class="profile-name">Special Pixel Studio</div>
        <div class="profile-role">AI Design Engineer</div>
        <span class="profile-stat">v3.0 Pro</span>
        <span class="profile-stat">DesignCreationHub</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### ⚙️ API Setup")

    api_provider = st.selectbox(
        "API Provider",
        ["Replicate — FLUX.1 (Best Quality)", "Hugging Face — SDXL (Free Tier)"],
    )
    use_replicate = "Replicate" in api_provider

    # ── Token input — pre-filled from secrets/env if available ──────────────
    if use_replicate:
        rep_token_input = st.text_input(
            "Replicate API Token",
            value=_REPLICATE_TOKEN_FROM_ENV,
            type="password",
            placeholder="r8_xxxxxxxxxxxx",
        )
        # Final resolved token
        ACTIVE_TOKEN = rep_token_input.strip() or _REPLICATE_TOKEN_FROM_ENV
        st.markdown("""
        <div class="token-hint">
            🔑 Get your free token at
            <a href="https://replicate.com/account/api-tokens" target="_blank">
            replicate.com/account/api-tokens</a><br>
            💡 On Streamlit Cloud: add <code>REPLICATE_API_TOKEN</code>
            in <em>Settings → Secrets</em> to avoid re-entering.
        </div>
        """, unsafe_allow_html=True)
    else:
        hf_token_input = st.text_input(
            "Hugging Face Token",
            value=_HF_TOKEN_FROM_ENV,
            type="password",
            placeholder="hf_xxxxxxxxxxxx",
        )
        ACTIVE_TOKEN = hf_token_input.strip() or _HF_TOKEN_FROM_ENV
        st.markdown("""
        <div class="token-hint">
            🔑 Get token at
            <a href="https://huggingface.co/settings/tokens" target="_blank">
            huggingface.co/settings/tokens</a><br>
            💡 Add <code>HF_API_TOKEN</code> in Streamlit Secrets.
        </div>
        """, unsafe_allow_html=True)

    token_ready = bool(ACTIVE_TOKEN)

    st.divider()
    st.markdown("#### 🖼️ Output Settings")

    num_outputs = st.slider("Variations", 1, 4, 2)

    res_choice = st.selectbox(
        "Resolution",
        [
            "1024 × 1024  — Square",
            "1344 × 768   — Landscape 16:9",
            "768  × 1344  — Portrait 9:16",
            "1280 × 720   — HD Landscape",
            "512  × 512   — Fast Preview",
        ],
    )
    _RES = {
        "1024 × 1024  — Square":      (1024, 1024),
        "1344 × 768   — Landscape 16:9": (1344, 768),
        "768  × 1344  — Portrait 9:16":  (768,  1344),
        "1280 × 720   — HD Landscape":   (1280, 720),
        "512  × 512   — Fast Preview":   (512,  512),
    }
    OUT_W, OUT_H = _RES[res_choice]

    inf_steps = st.slider("Inference Steps", 15, 50, 28,
        help="More steps = sharper but slower.")
    guidance  = st.slider("Guidance Scale (CFG)", 2.0, 15.0, 7.5, 0.5,
        help="Higher = follows prompt more strictly.")

    st.divider()
    st.markdown("#### 📊 Session")
    st.metric("Images Generated", st.session_state.generation_count)
    if st.session_state.last_prompt_used:
        st.caption(f"Last: _{st.session_state.last_prompt_used[:60]}..._")


# ============================================================================
# 10.  HEADER
# ============================================================================
st.markdown("""
<div class="app-header">
    <div class="header-badge">✦ AI STUDIO</div>
    <h1>DesignCreationHub</h1>
    <p>FLUX.1 · SDXL · Auto Prompt Enhancer · Image-to-Image Reference</p>
</div>
""", unsafe_allow_html=True)

# ── Onboarding banner when no token is set ──────────────────────────────────
if not token_ready:
    st.markdown("""
    <div class="onboard-banner">
        <h2>🔑 One step to start generating</h2>
        <p>Add your API token in the sidebar — it takes 30 seconds and is free.</p>
        <span class="onboard-step">1 · Open sidebar →</span>
        <span class="onboard-step">2 · Choose API provider</span>
        <span class="onboard-step">3 · Paste your token</span>
        <span class="onboard-step">4 · Generate ✨</span>
        <br><br>
        <p style="font-size:.8rem;color:#555e7a;">
            Replicate free tier gives you $5 credits (~500 images).
            HF Inference API is free for non-commercial use.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# 11.  TABS
# ============================================================================
tab_t2i, tab_i2i, tab_gallery = st.tabs(
    ["✍️  Text → Image", "🔄  Image → Image (Img2Img)", "🖼️  Session Gallery"]
)

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 1 — TEXT TO IMAGE                                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab_t2i:
    col_left, col_right = st.columns([1.15, 0.85], gap="large")

    with col_left:
        # ── Prompt Studio ──────────────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">✦ Prompt Studio</div>', unsafe_allow_html=True)

        user_prompt = st.text_area(
            "Describe your image",
            placeholder="e.g.  a cozy Tokyo café in the rain at night...",
            height=100,
            label_visibility="collapsed",
        )

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            style_pick = st.selectbox("Style Preset", list(STYLE_PRESETS.keys()))
        with col_s2:
            camera_pick = st.selectbox("Camera Angle", CAMERA_ANGLES)

        lighting_pick = st.selectbox("Lighting", LIGHTING_STYLES)

        extra_q = st.multiselect(
            "Extra Quality Boosters",
            QUALITY_TAGS_ALL,
            default=["8K resolution", "ultra-detailed", "HDR", "perfect composition"],
        )

        # Live enhanced-prompt preview
        if user_prompt.strip():
            _enh = enhance_prompt(
                user_prompt,
                STYLE_PRESETS.get(style_pick, ""),
                camera_pick, lighting_pick, extra_q,
            )
            st.session_state.last_enhanced = _enh
            st.markdown(
                f'<div class="enhanced-box">✨ <strong>Auto-enhanced:</strong> {_enh}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Negative Prompt Builder ─────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🚫 Negative Prompt Builder</div>', unsafe_allow_html=True)

        sel_negs = st.multiselect(
            "Quick-add blocks",
            list(NEGATIVE_PRESETS.keys()),
            default=["Quality Fix", "No Deformities"],
        )
        custom_neg = st.text_input("Custom negatives", placeholder="cartoon, sketch, flat colors...")
        final_neg  = build_negative(sel_negs, custom_neg)
        if final_neg:
            st.caption(f"Active: `{final_neg[:130]}{'…' if len(final_neg)>130 else ''}`")

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Generate panel ───────────────────────────────────────────────────────
    with col_right:
        st.markdown("#### Generate")
        gen_btn = st.button("🚀 Generate Images", key="btn_t2i", use_container_width=True)

        if gen_btn:
            if not user_prompt.strip():
                st.warning("✏️ Enter a prompt to get started.")
            elif not token_ready:
                st.warning("🔑 Add your API token in the sidebar first.")
            else:
                final_prompt = st.session_state.last_enhanced or user_prompt
                st.session_state.last_prompt_used = user_prompt[:80]

                with st.spinner("🎨 Generating your designs — this takes ~20–45s..."):
                    try:
                        if use_replicate:
                            imgs = generate_replicate_t2i(
                                ACTIVE_TOKEN, final_prompt, final_neg,
                                OUT_W, OUT_H, num_outputs, inf_steps, guidance,
                            )
                        else:
                            imgs = generate_hf_t2i(
                                ACTIVE_TOKEN, final_prompt, final_neg,
                                OUT_W, OUT_H, num_outputs, inf_steps, guidance,
                            )

                        st.session_state.generated_images = imgs
                        st.session_state.generation_count += len(imgs)
                        st.markdown('<span class="pill-ok">✓ Done!</span>', unsafe_allow_html=True)

                    except Exception as e:
                        st.markdown(f'<span class="pill-err">✗ {str(e)[:120]}</span>', unsafe_allow_html=True)
                        with st.expander("Error details"):
                            st.exception(e)

        # Inline results
        if st.session_state.generated_images:
            st.markdown("---")
            st.markdown("**Results**")
            _imgs = st.session_state.generated_images
            _cols = st.columns(min(2, len(_imgs)))
            for i, img in enumerate(_imgs):
                with _cols[i % 2]:
                    st.image(img, use_container_width=True, caption=f"Variation {i+1}")
                    st.download_button(
                        f"⬇ Download V{i+1}", data=pil_to_bytes_io(img),
                        file_name=f"design_v{i+1}.png", mime="image/png",
                        key=f"dl_t2i_{i}", use_container_width=True,
                    )


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 2 — IMAGE TO IMAGE                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab_i2i:
    col_il, col_ir = st.columns([1.1, 0.9], gap="large")

    with col_il:
        # ── Reference upload ───────────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📎 Reference Image</div>', unsafe_allow_html=True)

        upload_mode = st.radio(
            "Upload mode",
            ["Single Reference", "Style Grid (2–4 images → composite)"],
            horizontal=True,
        )

        ref_pil: Image.Image | None = None

        if upload_mode == "Single Reference":
            uf = st.file_uploader(
                "Upload your reference design / photo",
                type=["png", "jpg", "jpeg", "webp"],
                key="uf_single",
            )
            if uf:
                ref_pil = Image.open(uf).convert("RGB")
                st.image(ref_pil, caption="Reference Image", use_container_width=True)
                st.caption(f"Size: {ref_pil.size[0]}×{ref_pil.size[1]} px")

        else:
            uf_multi = st.file_uploader(
                "Upload 2–4 images to blend into a style grid",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="uf_grid",
            )
            if uf_multi:
                imgs_raw = [Image.open(f).convert("RGB") for f in uf_multi[:4]]
                ref_pil = build_grid_reference(imgs_raw, tile=512)
                st.image(ref_pil, caption=f"Grid Reference ({len(imgs_raw)} images → composite)", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Transform settings ──────────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔄 Transform Settings</div>', unsafe_allow_html=True)

        i2i_prompt = st.text_area(
            "How should the AI transform it?",
            placeholder="e.g.  convert to watercolor painting with soft pastel tones...",
            height=90,
            label_visibility="collapsed",
        )

        i2i_style = st.selectbox("Style", list(STYLE_PRESETS.keys()), key="i2i_style_sel")

        img_strength = st.slider(
            "Reference Influence",
            min_value=0.1, max_value=1.0, value=0.60, step=0.05,
            help=(
                "0.1–0.35 = stays very close to reference composition & colors\n"
                "0.40–0.65 = balanced blend of reference + prompt\n"
                "0.70–1.0  = prompt takes over, reference is a loose guide"
            ),
        )

        # Influence label
        if img_strength <= 0.35:
            st.info("🎯 **Conservative** — output closely mirrors reference style & layout")
        elif img_strength <= 0.65:
            st.info("⚖️ **Balanced** — smart blend of reference composition + prompt style")
        else:
            st.info("💥 **Creative** — prompt drives output; reference used loosely")

        i2i_negs = st.multiselect(
            "Negative blocks",
            list(NEGATIVE_PRESETS.keys()),
            default=["Quality Fix", "No Deformities"],
            key="i2i_neg_sel",
        )
        i2i_neg_str = build_negative(i2i_negs, "")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_ir:
        st.markdown("#### Transform")
        i2i_btn = st.button("🔄 Transform Reference", key="btn_i2i", use_container_width=True)

        if i2i_btn:
            if ref_pil is None:
                st.warning("📎 Upload a reference image first.")
            elif not i2i_prompt.strip():
                st.warning("✏️ Describe how to transform the image.")
            elif not token_ready:
                st.warning("🔑 Add your API token in the sidebar first.")
            else:
                enh_i2i = enhance_prompt(
                    i2i_prompt,
                    STYLE_PRESETS.get(i2i_style, ""),
                    "", "",
                    ["ultra-detailed", "HDR", "8K resolution"],
                )

                with st.spinner("🔄 Transforming — ~30–60s..."):
                    try:
                        if use_replicate:
                            imgs = generate_replicate_i2i(
                                ACTIVE_TOKEN, enh_i2i, ref_pil,
                                img_strength, OUT_W, OUT_H,
                                num_outputs, inf_steps, guidance,
                            )
                        else:
                            imgs = generate_hf_i2i(
                                ACTIVE_TOKEN, enh_i2i, i2i_neg_str,
                                ref_pil, img_strength,
                                OUT_W, OUT_H, num_outputs, inf_steps, guidance,
                            )

                        st.session_state.generated_images = imgs
                        st.session_state.generation_count += len(imgs)
                        st.markdown('<span class="pill-ok">✓ Transform complete!</span>', unsafe_allow_html=True)

                    except Exception as e:
                        st.markdown(f'<span class="pill-err">✗ {str(e)[:120]}</span>', unsafe_allow_html=True)
                        with st.expander("Error details"):
                            st.exception(e)

        if st.session_state.generated_images:
            st.markdown("---")
            st.markdown("**Results**")
            _imgs = st.session_state.generated_images
            _cols = st.columns(min(2, len(_imgs)))
            for i, img in enumerate(_imgs):
                with _cols[i % 2]:
                    st.image(img, use_container_width=True, caption=f"Result {i+1}")
                    st.download_button(
                        f"⬇ Download {i+1}", data=pil_to_bytes_io(img),
                        file_name=f"transform_{i+1}.png", mime="image/png",
                        key=f"dl_i2i_{i}", use_container_width=True,
                    )


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 3 — SESSION GALLERY                                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab_gallery:
    _all = st.session_state.generated_images
    if not _all:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;color:#404560">
            <div style="font-size:2.5rem">🖼️</div>
            <p style="margin-top:12px;font-size:.95rem">
                Generate images in the other tabs — they'll collect here.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"#### Session Gallery  ·  {len(_all)} image{'s' if len(_all)!=1 else ''}")
        with c2:
            if st.button("🗑️ Clear All", key="clear_gallery"):
                st.session_state.generated_images = []
                st.rerun()

        ncols = min(3, len(_all))
        gcols  = st.columns(ncols)
        for i, img in enumerate(_all):
            with gcols[i % ncols]:
                st.image(img, use_container_width=True)
                st.download_button(
                    "⬇ Download",
                    data=pil_to_bytes_io(img),
                    file_name=f"design_gallery_{i+1}.png",
                    mime="image/png",
                    key=f"dl_gal_{i}",
                    use_container_width=True,
                )
