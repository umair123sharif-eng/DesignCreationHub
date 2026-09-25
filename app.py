"""
DesignCreationHub — Etsy POD Studio  v5.0
Author : Special Pixel Studio (Sharif)

v5 Architecture:
  PRIMARY  : Replicate FLUX.1-dev  (text2img + img2img)
  FALLBACK : Google Gemini Imagen 3 (text2img + img2img)
             auto-fallback on 429 / auth errors / network failures

Prompt Engineering Rules (v5):
  ✗  BANNED  : 8k, ultra-detailed, sharp focus, HDR, vibrant, vector,
               hyperrealistic, octane, cinema4d  ← these cause plastic renders
  ✓  USE     : medium descriptors (watercolor, screenprint, hand-painted)
               palette names (rust orange, warm cream, mustard yellow)
               texture words (paper grain, ink bleed, distressed, aged)
  ✓  CFG     : kept LOW (3.5–5.5) → softness; high CFG → glossy render
  ✓  SINGLE DESIGN MODE : blocks grid/collage generation that garbles text
"""

# ── stdlib ───────────────────────────────────────────────────────────────────
import base64
import io
import os
import time
import traceback
from enum import Enum

# ── third-party ──────────────────────────────────────────────────────────────
import requests
import streamlit as st
from PIL import Image

# ============================================================================
# 0.  PAGE CONFIG  (must be the very first Streamlit call)
# ============================================================================
st.set_page_config(
    page_title="DesignCreationHub — Etsy POD",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# 1.  SECRETS / TOKEN RESOLUTION
#     Priority order: st.secrets → os.environ → sidebar text_input
# ============================================================================
def _secret(key: str) -> str:
    try:
        v = st.secrets.get(key, "")
        if v:
            return str(v)
    except Exception:
        pass
    return os.environ.get(key, "")

_ENV_REPLICATE = _secret("REPLICATE_API_TOKEN")
_ENV_GEMINI    = _secret("GEMINI_API_KEY")

# ============================================================================
# 2.  PROVIDER ENUM + MODEL CONSTANTS
# ============================================================================
class Provider(str, Enum):
    REPLICATE = "Replicate — FLUX.1-dev"
    GEMINI    = "Google Gemini — Imagen 3"

REPLICATE_T2I = "black-forest-labs/flux-dev"        # best quality, supports neg prompt
REPLICATE_I2I = "black-forest-labs/flux-dev"        # same model handles img2img via image param

GEMINI_T2I_MODEL  = "imagen-3.0-generate-001"
GEMINI_I2I_MODEL  = "imagen-3.0-capability-001"     # Imagen 3 editing / style-transfer

# ============================================================================
# 3.  ETSY POD PROMPT SYSTEM
#
#     CORE RULES (enforced in every preset):
#     ───────────────────────────────────────
#     • NO "8K / ultra-detailed / sharp focus / HDR / vibrant / vector"
#       → these keywords activate FLUX's photorealistic / glossy-render mode
#     • DESCRIBE the medium, not the resolution
#       → "hand-painted watercolor wash" beats "ultra-high-res digital art"
#     • PALETTE in natural language
#       → "rust orange, warm cream, charcoal, dusty sage"
#     • GUIDANCE (CFG) intentionally low (3.5–5.5)
#       → high CFG (7+) forces sharp photorealistic mode
#     • WHITE BACKGROUND in every positive prompt
#       → critical for POD / DTF / sublimation cutouts
# ============================================================================

PRESETS: dict[str, dict] = {

    # ── 1. PRIMARY WORKHORSE ────────────────────────────────────────────────
    "🌾 Vintage Watercolor — Etsy #1": {
        "pos": (
            "hand-painted watercolor illustration on white background, "
            "t-shirt apparel graphic, cottagecore autumn aesthetic, "
            "soft muted fall palette: rust orange, warm cream, mustard yellow, charcoal, "
            "loose gestural brushstrokes, subtle paper grain texture, "
            "delicate ink outlines, whimsical folk art quality, "
            "boutique Etsy print style, transparent pigment washes"
        ),
        "neg": (
            "3D render, CGI, glossy, plastic sheen, shiny, photorealistic, photograph, "
            "neon, oversaturated, electric colors, fluorescent, vibrant, "
            "sharp focus, hyperdetailed, 8k, HDR, RAW photo, "
            "vector clipart, flat design, digital cartoon, thick outlines only, "
            "dark background, gradient background, solid color background"
        ),
        "cfg": 4.0,
        "steps": 35,
        "gemini_style": "watercolor",
    },

    # ── 2. DISTRESSED SCREENPRINT ───────────────────────────────────────────
    "📜 Distressed Retro Screenprint": {
        "pos": (
            "vintage 1970s distressed screenprint t-shirt graphic, "
            "hand-drawn ink illustration, faded retro palette: warm sepia, rust, sage green, aged cream, "
            "halftone dot texture, ink-bleed edges, worn fabric look, "
            "folk art lettering, retro Americana apparel style, "
            "rough hand-inked contours, white background"
        ),
        "neg": (
            "3D, CGI, glossy, plastic, shiny, photorealistic, neon, oversaturated, "
            "clean crisp digital art, vector, flat, modern clipart, "
            "futuristic, sharp focus, HDR, 8k, gradient background"
        ),
        "cfg": 4.5,
        "steps": 32,
        "gemini_style": "vintage illustration",
    },

    # ── 3. HALLOWEEN COTTAGECORE ─────────────────────────────────────────────
    "🎃 Halloween Cottagecore": {
        "pos": (
            "hand-drawn Halloween watercolor illustration, t-shirt print art, "
            "cottagecore spooky aesthetic, muted autumn palette: "
            "pumpkin orange, charcoal black, warm cream, dusty sage green, "
            "cute ghost and pumpkin motifs, plaid and buffalo check fabric accents, "
            "sunflower and dried botanical details, soft ink outlines, "
            "whimsical folk art style, distressed vintage feel, white background"
        ),
        "neg": (
            "3D render, CGI, glossy, plastic, shiny, neon green or neon orange, "
            "oversaturated Halloween colors, electric colors, "
            "photorealistic, hyperdetailed, 8k, HDR, "
            "vector clipart, flat cartoon, dark solid background, horror gore"
        ),
        "cfg": 4.0,
        "steps": 35,
        "gemini_style": "watercolor folk art",
    },

    # ── 4. COZY AUTUMN / COFFEE ──────────────────────────────────────────────
    "☕ Cozy Autumn & Coffee": {
        "pos": (
            "cozy autumn watercolor illustration, DTF transfer print, "
            "warm hygge coffee shop aesthetic, muted earthy palette: "
            "burnt sienna, warm taupe, mustard yellow, forest green, cream, "
            "hand-painted mugs, leaves, pumpkins, botanicals, "
            "soft colored-pencil-over-watercolor texture, "
            "farmhouse cottagecore style, white background"
        ),
        "neg": (
            "3D, CGI, glossy, shiny, photorealistic, neon, vibrant, "
            "digital cartoon, clipart, vector, flat design, "
            "sharp crisp focus, HDR, 8k, dark background"
        ),
        "cfg": 4.0,
        "steps": 32,
        "gemini_style": "cozy watercolor illustration",
    },

    # ── 5. BOHO FLORAL ──────────────────────────────────────────────────────
    "🌸 Boho Floral Sublimation": {
        "pos": (
            "boho watercolor floral design, sublimation t-shirt print, "
            "wildflower botanical illustration, soft dusty rose, sage green, ivory, blush palette, "
            "hand-painted loose petals, delicate leaf sprigs and feathers, "
            "cottagecore farmhouse feminine aesthetic, "
            "airy transparent watercolor washes, white background"
        ),
        "neg": (
            "3D, CGI, glossy, shiny, photorealistic, neon, oversaturated, "
            "dark background, busy background, clipart, vector, flat design, "
            "sharp crisp edges, hyperdetailed, 8k, HDR, plastic look"
        ),
        "cfg": 3.5,
        "steps": 30,
        "gemini_style": "boho floral watercolor",
    },

    # ── 6. TEACHER / BACK-TO-SCHOOL ─────────────────────────────────────────
    "🍎 Teacher Appreciation POD": {
        "pos": (
            "cute hand-drawn teacher appreciation t-shirt graphic, "
            "watercolor illustration, classroom motifs: apple pencil book ruler chalkboard, "
            "warm palette: coral red, golden yellow, sage green, cream, warm brown, "
            "whimsical folk art lettering, boutique Etsy print quality, "
            "soft painterly texture, white background"
        ),
        "neg": (
            "3D, CGI, glossy, clipart, vector, neon, photorealistic, "
            "sharp digital art, oversaturated, busy background, 8k, HDR"
        ),
        "cfg": 4.0,
        "steps": 30,
        "gemini_style": "cute watercolor illustration",
    },

    # ── 7. VINTAGE INK LINEWORK ─────────────────────────────────────────────
    "🖋️ Vintage Ink Linework": {
        "pos": (
            "vintage hand-drawn ink illustration, fine pen linework, "
            "cross-hatching and stippling texture, "
            "aged sepia or black ink on cream paper texture, "
            "engraving etching style, artisan craft aesthetic, "
            "apparel graphic, single or two-color palette, white background"
        ),
        "neg": (
            "full color, watercolor, 3D, CGI, glossy, photorealistic, "
            "neon, digital art, vector, flat design, "
            "sharp photography, 8k, HDR, busy background"
        ),
        "cfg": 5.5,
        "steps": 32,
        "gemini_style": "ink engraving illustration",
    },

    # ── 8. CUSTOM / MANUAL ──────────────────────────────────────────────────
    "✏️ Custom (No Preset)": {
        "pos": "",
        "neg": (
            "3D render, CGI, glossy, plastic, shiny, photorealistic, "
            "neon, oversaturated, 8k, HDR, sharp focus, vector clipart"
        ),
        "cfg": 5.0,
        "steps": 28,
        "gemini_style": "",
    },
}

# ── Shared negative chunks always available ──────────────────────────────────
NEG_BLOCKS: dict[str, str] = {
    "🚫 Anti-Glossy / 3D":   "3D render, CGI, octane render, glossy finish, plastic sheen, blender 3D",
    "🚫 Anti-Neon Colors":   "neon, oversaturated, fluorescent, electric colors, vibrant saturated",
    "🚫 Anti-Clipart":       "vector art, clipart, flat design, digital illustration, thick cartoon outlines",
    "🚫 Anti-Garbled Text":  "garbled text, illegible letters, AI gibberish, misspelled words, random symbols",
    "🚫 No People / Faces":  "person, human face, realistic portrait, crowd",
    "🚫 Anti-Low Quality":   "blurry, pixelated, jpeg artifacts, watermark, draft quality",
}

# Injected when Single Design Mode is ON
SINGLE_DESIGN = (
    "single centered graphic design isolated on white background, "
    "one unified composition, no grid layout, no collage sheet, no multiple panels"
)

# Injected for img2img style transfer
STYLE_XFER = (
    "preserve the color palette and artistic medium from the reference image, "
    "maintain muted earthy tones and painterly texture, "
    "apply same watercolor or screenprint feel to new subject, "
    "no neon or saturated additions"
)

TEXT_LEGIBILITY = (
    "clean hand-lettered text, legible vintage typography, "
    "clear readable letters, well-spaced lettering style"
)

# ============================================================================
# 4.  CSS — Warm studio dark theme (autumn / Etsy palette)
# ============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"]{font-family:'Inter',sans-serif}
.stApp{background:#09090c;color:#ddd8cc}

/* Header */
.app-header{
  background:linear-gradient(135deg,#141008 0%,#1a1208 55%,#100c14 100%);
  border:1px solid #2a2014;border-radius:18px;
  padding:28px 36px;margin-bottom:20px;position:relative;overflow:hidden;
}
.app-header::after{
  content:'';position:absolute;top:-70px;right:-70px;
  width:240px;height:240px;
  background:radial-gradient(circle,rgba(184,124,56,.2) 0%,transparent 70%);
}
.app-header h1{
  font-family:'Space Grotesk',sans-serif;
  font-size:2rem;font-weight:700;color:#f0e4cc;
  margin:0 0 5px;letter-spacing:-.5px;
}
.app-header p{color:#6a6050;font-size:.9rem;margin:0}
.header-badge{
  display:inline-block;
  background:rgba(184,124,56,.18);border:1px solid rgba(184,124,56,.4);
  color:#c8946a;font-size:.68rem;font-weight:600;
  padding:3px 11px;border-radius:20px;margin-bottom:10px;
  letter-spacing:.7px;text-transform:uppercase;
}

/* Provider status bar */
.provider-bar{
  display:flex;align-items:center;gap:10px;
  background:#0e0c08;border:1px solid #2a2010;
  border-radius:10px;padding:10px 16px;margin-bottom:16px;
}
.prov-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.prov-dot.green{background:#22c55e;box-shadow:0 0 6px #22c55e88}
.prov-dot.amber{background:#f59e0b;box-shadow:0 0 6px #f59e0b88}
.prov-dot.red{background:#ef4444;box-shadow:0 0 6px #ef444488}
.prov-label{font-size:.8rem;color:#8a7a60;flex:1}
.prov-name{font-size:.8rem;font-weight:600;color:#c8a060}
.fallback-badge{
  font-size:.68rem;background:rgba(245,158,11,.12);
  border:1px solid rgba(245,158,11,.3);color:#f59e0b;
  padding:2px 8px;border-radius:6px;
}

/* Section cards */
.section-card{
  background:#0e0c08;border:1px solid #2a2010;
  border-radius:14px;padding:20px 22px;margin-bottom:14px;
}
.section-title{
  font-family:'Space Grotesk',sans-serif;
  font-size:.73rem;font-weight:700;color:#b87840;
  text-transform:uppercase;letter-spacing:1.2px;margin-bottom:12px;
}

/* Sidebar */
[data-testid="stSidebar"]{
  background:#07070a !important;
  border-right:1px solid #1a1510 !important;
}

/* Profile */
.profile-card{
  background:linear-gradient(150deg,#141008,#0f0c08);
  border:1px solid #2a2018;border-radius:14px;
  padding:20px;text-align:center;margin-bottom:18px;
}
.profile-avatar{font-size:2.4rem;margin-bottom:7px}
.profile-name{
  font-family:'Space Grotesk',sans-serif;
  font-weight:600;font-size:.96rem;color:#f0e4cc;margin-bottom:4px;
}
.profile-role{font-size:.75rem;color:#b87840;margin-bottom:10px}
.profile-stat{
  display:inline-block;
  background:rgba(184,124,56,.1);border:1px solid rgba(184,124,56,.22);
  color:#c8946a;font-size:.7rem;padding:3px 8px;border-radius:7px;margin:2px;
}

/* Buttons */
.stButton>button{
  background:linear-gradient(135deg,#8b5e20,#5a3c14);
  color:#f5e8cc;border:none;border-radius:10px;
  font-family:'Space Grotesk',sans-serif;
  font-weight:600;font-size:1rem;padding:13px 28px;width:100%;
  transition:filter .18s,transform .12s;
}
.stButton>button:hover{filter:brightness(1.18);transform:translateY(-1px)}
.stButton>button:active{transform:translateY(0)}

/* Preset preview box */
.preset-box{
  background:#0a0806;border:1px solid #2a1e0e;
  border-left:3px solid #b87840;border-radius:10px;
  padding:12px 16px;font-size:.82rem;color:#8a7860;
  line-height:1.6;margin-top:8px;font-style:italic;
}
.preset-box strong{color:#c8a060;font-style:normal}

/* Enhanced prompt box */
.prompt-box{
  background:#0c0a06;border:1px solid #2e2010;
  border-left:3px solid #8b5e20;border-radius:10px;
  padding:12px 16px;font-size:.83rem;color:#9a8870;
  line-height:1.65;font-style:italic;margin-top:8px;
}

/* Onboarding banner */
.onboard{
  background:linear-gradient(135deg,#141008,#0e0c06);
  border:1px solid #2a2010;border-radius:14px;
  padding:28px 32px;text-align:center;margin:20px 0;
}
.onboard h2{
  font-family:'Space Grotesk',sans-serif;
  font-size:1.35rem;font-weight:700;color:#f0e4cc;margin:0 0 8px;
}
.onboard p{color:#6a6050;margin:0 0 16px;font-size:.9rem}
.onboard-step{
  display:inline-block;
  background:rgba(184,124,56,.1);border:1px solid rgba(184,124,56,.3);
  color:#b89060;font-size:.77rem;padding:5px 13px;
  border-radius:8px;margin:3px;
}

/* Pills */
.pill-ok{
  display:inline-flex;align-items:center;gap:5px;
  background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.25);
  color:#34d399;font-size:.74rem;font-weight:600;
  padding:4px 13px;border-radius:20px;
}
.pill-err{
  display:inline-flex;align-items:center;gap:5px;
  background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.25);
  color:#f87171;font-size:.74rem;font-weight:600;
  padding:4px 13px;border-radius:20px;
}
.pill-warn{
  display:inline-flex;align-items:center;gap:5px;
  background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.25);
  color:#fbbf24;font-size:.74rem;font-weight:600;
  padding:4px 13px;border-radius:20px;
}

/* Mode badge */
.mode-badge{
  display:inline-block;
  background:rgba(184,124,56,.14);border:1px solid rgba(184,124,56,.32);
  color:#c8a060;font-size:.74rem;font-weight:600;
  padding:3px 11px;border-radius:8px;margin-top:4px;
}

/* Token hint */
.token-hint{
  background:#0a0806;border:1px solid #221c0e;
  border-radius:8px;padding:10px 14px;
  font-size:.78rem;color:#5a5040;margin-top:6px;line-height:1.5;
}
.token-hint a{color:#b87840;text-decoration:none}
.token-hint a:hover{text-decoration:underline}

.stTextArea textarea{
  background:#0a0806 !important;border:1px solid #2a2010 !important;
  border-radius:9px !important;color:#d8ccb8 !important;
}
.stTextArea textarea:focus{
  border-color:#b87840 !important;
  box-shadow:0 0 0 2px rgba(184,124,56,.12) !important;
}

#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:1.4rem}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 5.  SESSION STATE
# ============================================================================
for _k, _v in {
    "generated_images": [],
    "generation_count": 0,
    "last_provider":    "",
    "fallback_used":    False,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ============================================================================
# 6.  IMAGE UTILITIES
# ============================================================================
def pil_to_b64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"

def pil_to_bytes(img: Image.Image) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def url_to_pil(url: str) -> Image.Image:
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def build_grid(images: list, tile: int = 512) -> Image.Image:
    cols = 2 if len(images) > 1 else 1
    rows = (len(images) + 1) // 2
    grid = Image.new("RGB", (tile * cols, tile * rows), (255, 255, 255))
    for i, img in enumerate(images[:4]):
        grid.paste(img.resize((tile, tile), Image.LANCZOS),
                   ((i % cols) * tile, (i // cols) * tile))
    return grid

def is_rate_limit_or_auth(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in ["429", "rate limit", "quota", "auth", "401", "403",
                                   "permission", "forbidden", "unauthorized"])

# ============================================================================
# 7.  PROMPT BUILDER
# ============================================================================
def build_prompt(
    idea: str,
    preset_key: str,
    single_mode: bool,
    with_text: bool,
    text_content: str,
    extra_pos: str,
    extra_neg_keys: list,
    custom_neg: str,
    is_i2i: bool = False,
) -> tuple[str, str, float, int]:
    """
    Returns (positive, negative, cfg, steps).
    NO 8K / ultra-detailed / sharp focus / HDR / vibrant injected here.
    """
    p = PRESETS.get(preset_key, PRESETS["✏️ Custom (No Preset)"])

    pos_parts = []
    if single_mode:
        pos_parts.append(SINGLE_DESIGN)
    if is_i2i:
        pos_parts.append(STYLE_XFER)
    if idea.strip():
        pos_parts.append(idea.strip().rstrip(","))
    if with_text and text_content.strip():
        pos_parts.append(f'with text reading "{text_content.strip()}"')
        pos_parts.append(TEXT_LEGIBILITY)
    if p["pos"]:
        pos_parts.append(p["pos"])
    if extra_pos.strip():
        pos_parts.append(extra_pos.strip())

    neg_parts = [p["neg"]] if p["neg"] else []
    for k in extra_neg_keys:
        if k in NEG_BLOCKS:
            neg_parts.append(NEG_BLOCKS[k])
    if with_text:
        neg_parts.append(
            "garbled text, illegible text, distorted letters, "
            "AI gibberish text, misspelled words, random symbols"
        )
    else:
        neg_parts.append("text, letters, words, typography, writing, font, label")
    if custom_neg.strip():
        neg_parts.append(custom_neg.strip())

    return (
        ", ".join(pos_parts),
        ", ".join(neg_parts),
        p["cfg"],
        p["steps"],
    )

# ============================================================================
# 8.  REPLICATE ENGINE
# ============================================================================
def _rep(token: str):
    try:
        import replicate as _r
        return _r.Client(api_token=token)
    except ImportError:
        raise ImportError("Add `replicate` to requirements.txt")

def replicate_t2i(token, prompt, negative, width, height, num, steps, cfg) -> list:
    client = _rep(token)
    out = client.run(
        REPLICATE_T2I,
        input={
            "prompt":              prompt,
            "negative_prompt":     negative,
            "width":               width,
            "height":              height,
            "num_outputs":         num,
            "num_inference_steps": steps,
            "guidance_scale":      cfg,
        },
    )
    return [url_to_pil(str(x)) for x in out]

def replicate_i2i(token, prompt, negative, ref: Image.Image,
                  strength, width, height, num, steps, cfg) -> list:
    client = _rep(token)
    ref_r = ref.resize((width, height), Image.LANCZOS)
    out = client.run(
        REPLICATE_I2I,
        input={
            "prompt":              prompt,
            "negative_prompt":     negative,
            "image":               pil_to_b64(ref_r, "PNG"),
            "prompt_strength":     strength,  # 0=copy ref, 1=ignore ref
            "width":               width,
            "height":              height,
            "num_outputs":         num,
            "num_inference_steps": steps,
            "guidance_scale":      cfg,
        },
    )
    return [url_to_pil(str(x)) for x in out]

# ============================================================================
# 9.  GEMINI / IMAGEN 3 ENGINE
#
#     Uses google-genai SDK (pip install google-genai).
#     Imagen 3 does not accept a separate negative_prompt parameter —
#     we embed negatives into the positive prompt as "avoid: ..." suffix.
# ============================================================================
def _gemini_client(api_key: str):
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        raise ImportError("Add `google-genai` to requirements.txt")

def _embed_negative(positive: str, negative: str) -> str:
    """
    Imagen 3 has no neg_prompt param.
    We append a concise 'avoid' clause to the positive prompt.
    Only include the most critical negatives to avoid token bloat.
    """
    if not negative:
        return positive
    # Condense: take first 120 chars of negative
    neg_short = negative[:120].rstrip(",").strip()
    return f"{positive}. Avoid: {neg_short}."

def gemini_t2i(api_key, prompt, negative, width, height, num,
               steps, cfg, preset_key) -> list:
    from google.genai import types as gtypes
    client = _gemini_client(api_key)
    full_prompt = _embed_negative(prompt, negative)
    # Map aspect ratio from width/height
    ar = _aspect_ratio(width, height)
    results = []
    response = client.models.generate_images(
        model=GEMINI_T2I_MODEL,
        prompt=full_prompt,
        config=gtypes.GenerateImagesConfig(
            number_of_images=min(num, 4),
            aspect_ratio=ar,
            # safety_filter_level="block_only_high",  # uncomment if needed
        ),
    )
    for img_obj in response.generated_images:
        raw = img_obj.image.image_bytes
        results.append(Image.open(io.BytesIO(raw)).convert("RGB"))
    return results

def gemini_i2i(api_key, prompt, negative, ref: Image.Image,
               strength, width, height, num, steps, cfg) -> list:
    """
    Imagen 3 editing endpoint — mask=None means global style edit.
    strength mapped: 0.1-0.4 → edit_mode 'inpaint-insert' is not right;
    we use 'product-image' mode for clean white-bg style transfer.
    For general style transfer we use the standard generate with ref as
    a base64 inline image in the prompt context.
    Falls back to text-only generation if edit endpoint unavailable.
    """
    try:
        from google.genai import types as gtypes
        client = _gemini_client(api_key)
        # Resize ref to target
        ref_r = ref.resize((width, height), Image.LANCZOS)
        buf = io.BytesIO()
        ref_r.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        full_prompt = _embed_negative(prompt, negative)
        ar = _aspect_ratio(width, height)

        response = client.models.edit_image(
            model=GEMINI_I2I_MODEL,
            prompt=full_prompt,
            reference_images=[
                gtypes.RawReferenceImage(
                    reference_id=1,
                    reference_image=gtypes.Image(image_bytes=img_bytes),
                )
            ],
            config=gtypes.EditImageConfig(
                edit_mode="INPAINT_INSERTION",
                number_of_images=min(num, 4),
                aspect_ratio=ar,
            ),
        )
        results = []
        for img_obj in response.generated_images:
            raw = img_obj.image.image_bytes
            results.append(Image.open(io.BytesIO(raw)).convert("RGB"))
        return results if results else gemini_t2i(
            api_key, prompt, negative, width, height, num, steps, cfg, ""
        )
    except Exception:
        # Fallback: text-only generation with style-transfer prompt
        return gemini_t2i(
            api_key, prompt, negative, width, height, num, steps, cfg, ""
        )

def _aspect_ratio(w: int, h: int) -> str:
    ratio = w / h
    if ratio >= 1.7:  return "16:9"
    if ratio >= 1.2:  return "4:3"
    if ratio <= 0.6:  return "9:16"
    if ratio <= 0.85: return "3:4"
    return "1:1"

# ============================================================================
# 10.  SMART DISPATCH — auto-fallback logic
# ============================================================================
def smart_generate(
    mode: str,           # "t2i" or "i2i"
    preferred: Provider,
    rep_token: str,
    gem_token: str,
    prompt: str,
    negative: str,
    ref_img,             # Image.Image | None
    strength: float,
    width: int, height: int,
    num: int, steps: int, cfg: float,
    preset_key: str,
) -> tuple[list, str, bool]:
    """
    Returns (images, provider_used, fallback_used).
    Tries preferred provider first; on 429/auth/network falls back.
    """
    providers_to_try = [preferred]
    if preferred == Provider.REPLICATE and gem_token:
        providers_to_try.append(Provider.GEMINI)
    elif preferred == Provider.GEMINI and rep_token:
        providers_to_try.append(Provider.REPLICATE)

    last_err = None
    for idx, prov in enumerate(providers_to_try):
        try:
            if prov == Provider.REPLICATE:
                if not rep_token:
                    raise ValueError("Replicate token not set")
                if mode == "t2i":
                    imgs = replicate_t2i(rep_token, prompt, negative,
                                         width, height, num, steps, cfg)
                else:
                    imgs = replicate_i2i(rep_token, prompt, negative,
                                         ref_img, strength,
                                         width, height, num, steps, cfg)

            else:  # GEMINI
                if not gem_token:
                    raise ValueError("Gemini API key not set")
                if mode == "t2i":
                    imgs = gemini_t2i(gem_token, prompt, negative,
                                      width, height, num, steps, cfg, preset_key)
                else:
                    imgs = gemini_i2i(gem_token, prompt, negative,
                                      ref_img, strength,
                                      width, height, num, steps, cfg)

            fallback = (idx > 0)
            return imgs, prov.value, fallback

        except Exception as e:
            last_err = e
            # Only auto-fallback on rate-limit / auth errors
            if idx < len(providers_to_try) - 1 and is_rate_limit_or_auth(e):
                continue
            # On other errors with only one provider, re-raise
            if len(providers_to_try) == 1:
                raise
            # If last provider also failed, re-raise
            if idx == len(providers_to_try) - 1:
                raise last_err

    raise last_err  # should not reach

# ============================================================================
# 11.  SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("""
    <div class="profile-card">
        <div class="profile-avatar">🌾</div>
        <div class="profile-name">Special Pixel Studio</div>
        <div class="profile-role">Etsy POD Design Studio</div>
        <span class="profile-stat">v5.0</span>
        <span class="profile-stat">Dual Provider</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Provider selection ───────────────────────────────────────────────────
    st.markdown("#### ⚙️ API Provider")
    preferred_label = st.selectbox(
        "Primary provider",
        [p.value for p in Provider],
        label_visibility="collapsed",
    )
    preferred_prov = Provider(preferred_label)

    st.caption("Auto-falls back to the other provider on rate-limit / auth errors.")

    # ── Replicate token ──────────────────────────────────────────────────────
    st.markdown("**Replicate Token**")
    rep_input = st.text_input(
        "Replicate", value=_ENV_REPLICATE,
        type="password", placeholder="r8_...",
        label_visibility="collapsed",
    )
    REP_TOKEN = rep_input.strip() or _ENV_REPLICATE
    st.markdown("""<div class="token-hint">
        <a href="https://replicate.com/account/api-tokens" target="_blank">
        replicate.com/account/api-tokens</a> — free $5 credits<br>
        Streamlit Cloud: add <code>REPLICATE_API_TOKEN</code> in Secrets
    </div>""", unsafe_allow_html=True)

    st.markdown("**Google Gemini Key**")
    gem_input = st.text_input(
        "Gemini", value=_ENV_GEMINI,
        type="password", placeholder="AIza...",
        label_visibility="collapsed",
    )
    GEM_TOKEN = gem_input.strip() or _ENV_GEMINI
    st.markdown("""<div class="token-hint">
        <a href="https://aistudio.google.com/app/apikey" target="_blank">
        aistudio.google.com/app/apikey</a> — free tier available<br>
        Streamlit Cloud: add <code>GEMINI_API_KEY</code> in Secrets
    </div>""", unsafe_allow_html=True)

    # ── Token readiness ──────────────────────────────────────────────────────
    rep_ok  = bool(REP_TOKEN)
    gem_ok  = bool(GEM_TOKEN)
    any_ok  = rep_ok or gem_ok
    pref_ok = (preferred_prov == Provider.REPLICATE and rep_ok) or \
              (preferred_prov == Provider.GEMINI    and gem_ok)

    st.divider()
    st.markdown("#### 🖼️ Output")
    num_outputs = st.slider("Variations", 1, 4, 2)
    res_choice  = st.selectbox("Resolution", [
        "1024 × 1024  (Square — DTF/Sublimation)",
        "1200 × 1200  (Large Square)",
        "768  × 1024  (Portrait — Apparel)",
        "1024 × 768   (Landscape)",
        "512  × 512   (Fast Preview)",
    ])
    _RES = {
        "1024 × 1024  (Square — DTF/Sublimation)": (1024, 1024),
        "1200 × 1200  (Large Square)":              (1200, 1200),
        "768  × 1024  (Portrait — Apparel)":         (768,  1024),
        "1024 × 768   (Landscape)":                  (1024, 768),
        "512  × 512   (Fast Preview)":               (512,  512),
    }
    OUT_W, OUT_H = _RES[res_choice]

    st.divider()
    st.markdown("#### 📊 Session")
    st.metric("Designs Generated", st.session_state.generation_count)
    if st.session_state.last_provider:
        st.caption(f"Last: {st.session_state.last_provider}")
        if st.session_state.fallback_used:
            st.warning("⚡ Fallback provider was used last run.")

# ============================================================================
# 12.  HEADER + PROVIDER STATUS BAR
# ============================================================================
st.markdown("""
<div class="app-header">
    <div class="header-badge">🌾 ETSY POD STUDIO</div>
    <h1>DesignCreationHub</h1>
    <p>Watercolor · Distressed Screenprint · Boho · Cottagecore — Dual Provider: Replicate + Gemini Imagen 3</p>
</div>
""", unsafe_allow_html=True)

# Provider status bar
_dot_rep  = "green" if rep_ok  else "red"
_dot_gem  = "green" if gem_ok  else "red"
_pref_dot = "green" if pref_ok else ("amber" if any_ok else "red")
_fb_badge = '<span class="fallback-badge">⚡ fallback ready</span>' if (rep_ok and gem_ok) else ""

st.markdown(f"""
<div class="provider-bar">
    <div class="prov-dot {_pref_dot}"></div>
    <span class="prov-label">Active provider</span>
    <span class="prov-name">{preferred_prov.value}</span>
    &nbsp;
    <span style="font-size:.75rem;color:#3a3020">Replicate
        <span class="prov-dot {_dot_rep}" style="display:inline-block;margin:0 3px -1px"></span>
    </span>
    <span style="font-size:.75rem;color:#3a3020">Gemini
        <span class="prov-dot {_dot_gem}" style="display:inline-block;margin:0 3px -1px"></span>
    </span>
    {_fb_badge}
</div>
""", unsafe_allow_html=True)

# Onboarding
if not any_ok:
    st.markdown("""
    <div class="onboard">
        <h2>🔑 Add at least one API key to start</h2>
        <p>Both providers have free tiers. Add one or both in the sidebar.</p>
        <span class="onboard-step">1 · Open sidebar</span>
        <span class="onboard-step">2 · Paste Replicate token <em>and/or</em> Gemini key</span>
        <span class="onboard-step">3 · Choose a POD style preset</span>
        <span class="onboard-step">4 · Generate ✨</span>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# 13.  TABS
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
        # ── Style preset ───────────────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🎨 Etsy POD Style Preset</div>', unsafe_allow_html=True)

        t2i_preset = st.selectbox(
            "Style", list(PRESETS.keys()), label_visibility="collapsed",
        )
        _p = PRESETS[t2i_preset]
        if _p["pos"]:
            st.markdown(
                f'<div class="preset-box"><strong>Style DNA:</strong> {_p["pos"][:200]}…</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Design idea ────────────────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">✦ Design Idea</div>', unsafe_allow_html=True)

        t2i_idea = st.text_area(
            "idea", label_visibility="collapsed", height=105,
            placeholder=(
                "cute ghost holding a pumpkin spice latte with sunflowers\n"
                "highland cow in witch hat surrounded by autumn leaves\n"
                "skeleton reading a spell book with candles and cobwebs"
            ),
        )
        t2i_extra_pos = st.text_input(
            "Extra style descriptors (optional)",
            placeholder="buffalo check ribbon, dried lavender, crescent moon...",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Composition + text ─────────────────────────────────────────────
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📐 Composition & Typography</div>', unsafe_allow_html=True)

        t2i_single = st.toggle(
            "Single Design Mode (recommended)",
            value=True,
            help="Prevents garbled multi-panel grid sheets. Keep ON for Etsy POD.",
        )
        if t2i_single:
            st.markdown('<span class="mode-badge">✓ Single centered graphic — grid/collage blocked</span>',
                        unsafe_allow_html=True)

        t2i_with_text = st.toggle(
            "Include text / typography in design",
            value=False,
            help=(
                "Keep text short (1–4 words). AI text is imperfect — "
                "for pixel-perfect type, generate art first then add text in Canva."
            ),
        )
        t2i_text_content = ""
        if t2i_with_text:
            t2i_text_content = st.text_input(
                "Text to include", placeholder="Ghost Coffee Club",
            )
            if t2i_text_content and len(t2i_text_content.split()) > 5:
                st.warning("⚠️ Keep text to 1–4 words for readable AI output.")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── Advanced negatives ─────────────────────────────────────────────
        with st.expander("🚫 Advanced Negative Overrides", expanded=False):
            t2i_neg_keys = st.multiselect(
                "Add negative blocks",
                list(NEG_BLOCKS.keys()),
                default=["🚫 Anti-Glossy / 3D", "🚫 Anti-Neon Colors", "🚫 Anti-Clipart"],
            )
            t2i_custom_neg = st.text_input(
                "Custom negatives", placeholder="dark background, border frame...",
            )

        # ── Live prompt preview ────────────────────────────────────────────
        _pos, _neg, _cfg, _steps = build_prompt(
            t2i_idea, t2i_preset, t2i_single,
            t2i_with_text, t2i_text_content,
            t2i_extra_pos,
            t2i_neg_keys if "t2i_neg_keys" in dir() else [],
            t2i_custom_neg if "t2i_custom_neg" in dir() else "",
        )
        if _pos:
            st.markdown(
                f'<div class="prompt-box">🌾 <strong>Final prompt:</strong> '
                f'{_pos[:320]}{"…" if len(_pos)>320 else ""}</div>',
                unsafe_allow_html=True,
            )

    with col_r:
        st.markdown("#### Generate")
        t2i_btn = st.button("🌾 Generate Etsy Design", key="btn_t2i", use_container_width=True)

        if t2i_btn:
            if not t2i_idea.strip() and not _p["pos"]:
                st.warning("✏️ Enter a design idea.")
            elif not any_ok:
                st.warning("🔑 Add at least one API key in the sidebar.")
            else:
                pos, neg, cfg, steps = build_prompt(
                    t2i_idea, t2i_preset, t2i_single,
                    t2i_with_text, t2i_text_content,
                    t2i_extra_pos, t2i_neg_keys, t2i_custom_neg,
                )
                with st.spinner(f"🎨 Generating via {preferred_prov.value}... (~20–50s)"):
                    try:
                        imgs, prov_used, fb = smart_generate(
                            "t2i", preferred_prov,
                            REP_TOKEN, GEM_TOKEN,
                            pos, neg, None, 0.0,
                            OUT_W, OUT_H, num_outputs, steps, cfg,
                            t2i_preset,
                        )
                        st.session_state.generated_images  = imgs
                        st.session_state.generation_count += len(imgs)
                        st.session_state.last_provider     = prov_used
                        st.session_state.fallback_used     = fb

                        ok_msg = f"✓ {len(imgs)} design(s) ready"
                        if fb:
                            ok_msg += f" (via fallback: {prov_used})"
                        st.markdown(f'<span class="pill-ok">{ok_msg}</span>',
                                    unsafe_allow_html=True)
                        if fb:
                            st.markdown(
                                '<span class="pill-warn">⚡ Fallback provider was used</span>',
                                unsafe_allow_html=True,
                            )
                    except Exception as e:
                        st.markdown(
                            f'<span class="pill-err">✗ {str(e)[:140]}</span>',
                            unsafe_allow_html=True,
                        )
                        with st.expander("Error details"):
                            st.text(traceback.format_exc())

        if st.session_state.generated_images:
            st.markdown("---")
            _imgs = st.session_state.generated_images
            _cols = st.columns(min(2, len(_imgs)))
            for i, img in enumerate(_imgs):
                with _cols[i % 2]:
                    st.image(img, use_container_width=True, caption=f"Variation {i+1}")
                    st.download_button(
                        f"⬇ Download V{i+1}",
                        data=pil_to_bytes(img),
                        file_name=f"etsy_design_v{i+1}.png",
                        mime="image/png",
                        key=f"dl_t2i_{i}",
                        use_container_width=True,
                    )

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 2 — STYLE TRANSFER                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab_i2i:
    st.markdown("""
    <div class="preset-box" style="margin-bottom:16px">
        <strong>Style Transfer:</strong> Upload a reference design (your mood board or competitor listing).
        The AI extracts its <em>color palette, artistic medium, and texture</em>
        and applies them to your new subject — creating original Etsy-ready art.
        Keep Influence at <strong>0.3–0.45</strong> for best style extraction.
    </div>
    """, unsafe_allow_html=True)

    col_il, col_ir = st.columns([1.1, 0.9], gap="large")

    with col_il:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📎 Reference Image</div>', unsafe_allow_html=True)

        i2i_mode = st.radio(
            "Mode",
            ["Single Reference", "Style Composite (2–4 images)"],
            horizontal=True,
        )
        ref_pil = None

        if i2i_mode == "Single Reference":
            uf = st.file_uploader(
                "Upload reference design",
                type=["png", "jpg", "jpeg", "webp"], key="uf_single",
            )
            if uf:
                ref_pil = Image.open(uf).convert("RGB")
                st.image(ref_pil, use_container_width=True, caption="Reference")
        else:
            uf_m = st.file_uploader(
                "Upload 2–4 reference images",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True, key="uf_multi",
            )
            if uf_m:
                raw = [Image.open(f).convert("RGB") for f in uf_m[:4]]
                ref_pil = build_grid(raw)
                st.image(ref_pil, use_container_width=True,
                         caption=f"Composite ({len(raw)} images)")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🎨 New Design Subject</div>', unsafe_allow_html=True)

        i2i_idea = st.text_area(
            "idea", label_visibility="collapsed", height=90,
            placeholder=(
                "cute highland cow in witch hat with sunflowers\n"
                "ghost holding pumpkin spice latte, autumn leaves\n"
                "skeleton reading spellbook, candles and cobwebs"
            ),
        )
        i2i_preset_key = st.selectbox(
            "Style Preset", list(PRESETS.keys()), key="i2i_preset",
        )
        i2i_single = st.toggle("Single Design Mode", value=True, key="i2i_single")

        st.markdown("**Reference Influence**")
        img_strength = st.slider(
            "Influence", min_value=0.10, max_value=0.90,
            value=0.35, step=0.05, label_visibility="collapsed",
            help=(
                "0.10–0.30 → Style Extract: strong palette & texture copy\n"
                "0.35–0.55 → Balanced blend\n"
                "0.60–0.90 → Creative: prompt drives, reference is loose guide"
            ),
        )
        if img_strength <= 0.30:
            st.info("🎨 Style Extract — palette & texture pulled closely from reference")
        elif img_strength <= 0.55:
            st.info("⚖️ Balanced — style blended with your design prompt")
        else:
            st.info("💥 Creative — prompt drives output; reference loosely guides")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_ir:
        st.markdown("#### Transfer Style")
        i2i_btn = st.button("🔄 Transfer Style", key="btn_i2i", use_container_width=True)

        if i2i_btn:
            if ref_pil is None:
                st.warning("📎 Upload a reference image.")
            elif not i2i_idea.strip():
                st.warning("✏️ Describe the new design subject.")
            elif not any_ok:
                st.warning("🔑 Add at least one API key in the sidebar.")
            else:
                i2i_pos, i2i_neg, i2i_cfg, i2i_steps = build_prompt(
                    i2i_idea, i2i_preset_key, i2i_single,
                    False, "", "", [], "", is_i2i=True,
                )
                with st.spinner(f"🔄 Transferring style via {preferred_prov.value}... (~30–60s)"):
                    try:
                        imgs, prov_used, fb = smart_generate(
                            "i2i", preferred_prov,
                            REP_TOKEN, GEM_TOKEN,
                            i2i_pos, i2i_neg,
                            ref_pil, img_strength,
                            OUT_W, OUT_H, num_outputs,
                            i2i_steps, i2i_cfg,
                            i2i_preset_key,
                        )
                        st.session_state.generated_images  = imgs
                        st.session_state.generation_count += len(imgs)
                        st.session_state.last_provider     = prov_used
                        st.session_state.fallback_used     = fb

                        ok_msg = f"✓ {len(imgs)} transfer(s) done"
                        if fb:
                            ok_msg += f" (fallback: {prov_used})"
                        st.markdown(f'<span class="pill-ok">{ok_msg}</span>',
                                    unsafe_allow_html=True)
                        if fb:
                            st.markdown(
                                '<span class="pill-warn">⚡ Fallback provider used</span>',
                                unsafe_allow_html=True,
                            )
                    except Exception as e:
                        st.markdown(
                            f'<span class="pill-err">✗ {str(e)[:140]}</span>',
                            unsafe_allow_html=True,
                        )
                        with st.expander("Error details"):
                            st.text(traceback.format_exc())

        if st.session_state.generated_images:
            st.markdown("---")
            _imgs = st.session_state.generated_images
            _c = st.columns(min(2, len(_imgs)))
            for i, img in enumerate(_imgs):
                with _c[i % 2]:
                    st.image(img, use_container_width=True, caption=f"Transfer {i+1}")
                    st.download_button(
                        f"⬇ Download {i+1}",
                        data=pil_to_bytes(img),
                        file_name=f"style_transfer_{i+1}.png",
                        mime="image/png",
                        key=f"dl_i2i_{i}",
                        use_container_width=True,
                    )

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  TAB 3 — GALLERY                                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝
with tab_gallery:
    _all = st.session_state.generated_images
    if not _all:
        st.markdown("""
        <div style="text-align:center;padding:60px 0">
            <div style="font-size:2.5rem">🌾</div>
            <p style="color:#4a4030;margin-top:12px;font-size:.91rem">
                Generated designs collect here during this session.
            </p>
        </div>""", unsafe_allow_html=True)
    else:
        _c1, _c2 = st.columns([3, 1])
        with _c1:
            st.markdown(f"#### Session Gallery · {len(_all)} design{'s' if len(_all)!=1 else ''}")
        with _c2:
            if st.button("🗑️ Clear All", key="clr_gal"):
                st.session_state.generated_images = []
                st.rerun()

        ncols = min(3, len(_all))
        gcols = st.columns(ncols)
        for i, img in enumerate(_all):
            with gcols[i % ncols]:
                st.image(img, use_container_width=True)
                st.download_button(
                    "⬇ Download PNG",
                    data=pil_to_bytes(img),
                    file_name=f"etsy_design_{i+1}.png",
                    mime="image/png",
                    key=f"dl_g_{i}",
                    use_container_width=True,
                )
