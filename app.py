"""
DesignCreationHub v6.0
A production-ready Streamlit app for POD Etsy sellers.
Generates hand-drawn, vintage watercolor, and boutique apparel graphics.
"""

import streamlit as st
import requests
import base64
import io
import time
import re
import urllib.parse
from PIL import Image
from typing import Optional, Tuple

# ─── PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DesignCreationHub v6.0",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap');

  /* Root Variables */
  :root {
    --cream: #FAF7F2;
    --warm-brown: #8B5E3C;
    --dusty-rose: #C4876A;
    --sage: #7A9E7E;
    --muted-gold: #C9A84C;
    --charcoal: #2D2D2D;
    --soft-black: #1A1A1A;
    --paper: #F5F0E8;
    --border-warm: #D4C5A9;
  }

  /* Base */
  .stApp {
    background-color: var(--cream);
    font-family: 'Inter', sans-serif;
  }

  /* Header */
  .hub-header {
    background: linear-gradient(135deg, #2D2D2D 0%, #4A3728 50%, #2D2D2D 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    text-align: center;
    border: 1px solid #8B5E3C40;
    position: relative;
    overflow: hidden;
  }
  .hub-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23C9A84C' fill-opacity='0.04'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    opacity: 0.5;
  }
  .hub-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.6rem;
    font-weight: 700;
    color: #FAF7F2;
    letter-spacing: 0.5px;
    margin: 0;
    position: relative;
  }
  .hub-title span {
    color: #C9A84C;
  }
  .hub-subtitle {
    font-size: 0.95rem;
    color: #C4876A;
    margin-top: 0.4rem;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-weight: 300;
    position: relative;
  }
  .hub-badge {
    display: inline-block;
    background: #C9A84C20;
    border: 1px solid #C9A84C60;
    color: #C9A84C;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.72rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-top: 0.6rem;
    position: relative;
  }

  /* Provider Status Badges */
  .provider-grid {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin: 0.75rem 0;
  }
  .provider-badge {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 500;
    border: 1px solid;
  }
  .provider-connected {
    background: #7A9E7E18;
    border-color: #7A9E7E60;
    color: #4A7A4E;
  }
  .provider-disconnected {
    background: #C4876A18;
    border-color: #C4876A60;
    color: #8B4513;
  }
  .provider-free {
    background: #C9A84C18;
    border-color: #C9A84C60;
    color: #8B6914;
  }
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .dot-green { background: #7A9E7E; }
  .dot-red { background: #C4876A; }
  .dot-gold { background: #C9A84C; }

  /* Preset Cards */
  .preset-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.6rem;
    margin: 0.5rem 0;
  }
  .preset-card {
    padding: 0.75rem;
    border-radius: 10px;
    border: 2px solid var(--border-warm);
    background: var(--paper);
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: center;
  }
  .preset-card:hover {
    border-color: var(--warm-brown);
    background: #F0E8DC;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(139,94,60,0.15);
  }
  .preset-card.active {
    border-color: var(--warm-brown);
    background: #E8DDD0;
  }
  .preset-emoji { font-size: 1.6rem; display: block; }
  .preset-name { font-size: 0.75rem; font-weight: 600; color: var(--charcoal); margin-top: 0.3rem; }
  .preset-desc { font-size: 0.65rem; color: #8B7355; margin-top: 0.1rem; line-height: 1.3; }

  /* Result Card */
  .result-card {
    background: var(--paper);
    border: 1px solid var(--border-warm);
    border-radius: 14px;
    padding: 1rem;
    margin-bottom: 1rem;
  }
  .render-badge {
    display: inline-block;
    padding: 0.25rem 0.7rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;
  }
  .badge-replicate { background: #7A9E7E20; color: #4A7A4E; border: 1px solid #7A9E7E50; }
  .badge-gemini { background: #4285F420; color: #1A56BF; border: 1px solid #4285F450; }
  .badge-pollinations { background: #C9A84C20; color: #8B6914; border: 1px solid #C9A84C50; }

  /* Generation Progress */
  .gen-status {
    background: var(--paper);
    border: 1px solid var(--border-warm);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin: 1rem 0;
    font-size: 0.9rem;
    color: var(--charcoal);
  }

  /* Info Panel */
  .info-panel {
    background: #F0E8DC;
    border: 1px solid var(--border-warm);
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin: 0.75rem 0;
    font-size: 0.82rem;
    color: #5C4A35;
    line-height: 1.5;
  }
  .info-panel strong { color: var(--warm-brown); }

  /* Prompt Tips */
  .prompt-tip {
    font-size: 0.75rem;
    color: #8B7355;
    margin-top: 0.3rem;
    line-height: 1.4;
  }

  /* Sidebar Styles */
  [data-testid="stSidebar"] {
    background: #F5F0E8;
    border-right: 1px solid var(--border-warm);
  }
  [data-testid="stSidebar"] .block-container {
    padding: 1.5rem 1rem;
  }

  /* Tabs */
  [data-testid="stTabs"] [role="tab"] {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    font-size: 0.9rem;
    color: #8B7355;
  }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--warm-brown);
    border-bottom-color: var(--warm-brown) !important;
  }

  /* Buttons */
  .stButton > button {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    letter-spacing: 0.3px;
  }

  /* Divider */
  .section-divider {
    border: none;
    border-top: 1px solid var(--border-warm);
    margin: 1rem 0;
  }

  /* Watermark strip */
  .watermark-strip {
    text-align: center;
    font-size: 0.72rem;
    color: #B8A88A;
    padding: 0.5rem;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
</style>
""", unsafe_allow_html=True)


# ─── CONSTANTS & PRESETS ────────────────────────────────────────────────────

BANNED_TERMS = [
    "8k", "ultra-detailed", "ultra detailed", "sharp focus", "hdr",
    "vibrant colors", "vibrant colour", "photorealistic", "photo realistic",
    "3d render", "3d rendering", "unreal engine", "octane render",
    "hyperrealistic", "hyper realistic", "cgi", "vray", "ray tracing",
    "subsurface scattering", "global illumination"
]

WATERCOLOR_MODIFIERS = (
    "hand-painted watercolor illustration, loose gestural brushstrokes, "
    "soft muted palette, subtle paper grain texture, transparent pigment washes, "
    "delicate ink linework, painterly style, artisan crafted"
)

VINTAGE_MODIFIERS = (
    "distressed vintage screenprint texture, aged letterpress aesthetic, "
    "worn halftone dots, faded ink texture, retro Americana style, "
    "muted earthy tones, hand-stamped quality"
)

SINGLE_DESIGN_NEGATIVES = (
    "collage, grid, multiple designs, mockups, product mockup, "
    "tshirt mockup, flat lay, multiple views, repeated pattern, "
    "border frame, shadow, background clutter, watermark"
)

PRESETS = {
    "Etsy Vintage Watercolor": {
        "emoji": "🌸",
        "desc": "Soft botanical illustrations",
        "modifiers": WATERCOLOR_MODIFIERS,
        "negative": SINGLE_DESIGN_NEGATIVES + ", digital art, vector art",
        "cfg_scale": 4.0,
        "style_hint": "loose watercolor botanical art on white background, florist sketchbook style",
    },
    "Cottagecore Fall": {
        "emoji": "🍂",
        "desc": "Warm harvest aesthetics",
        "modifiers": (
            "warm autumn watercolor palette, cottagecore illustration, "
            "rustic handmade quality, golden hour tones, cozy farmhouse aesthetic, "
            "dried flowers and foliage, soft ink sketching"
        ),
        "negative": SINGLE_DESIGN_NEGATIVES + ", modern, digital, clean lines",
        "cfg_scale": 3.8,
        "style_hint": "cottagecore fall harvest watercolor on cream paper",
    },
    "Distressed Screenprint": {
        "emoji": "👕",
        "desc": "Vintage tee graphics",
        "modifiers": VINTAGE_MODIFIERS,
        "negative": SINGLE_DESIGN_NEGATIVES + ", watercolor, soft, pastel",
        "cfg_scale": 4.5,
        "style_hint": "vintage distressed screenprint graphic for apparel, 2-color print",
    },
    "Retro 70s Floral": {
        "emoji": "🌻",
        "desc": "Groovy botanical vibes",
        "modifiers": (
            "retro 1970s poster illustration, bold botanical line art, "
            "muted earth tones and burnt sienna, vintage hippie aesthetic, "
            "folk art inspired, hand-lettered feel, psychedelic botanical"
        ),
        "negative": SINGLE_DESIGN_NEGATIVES + ", modern minimalism, flat design",
        "cfg_scale": 4.2,
        "style_hint": "70s retro botanical poster art, earthy groovy palette",
    },
}

ASPECT_RATIOS = {
    "1:1 Square (POD Universal)": {"w": 1024, "h": 1024, "ratio": "1:1"},
    "4:5 Apparel (T-Shirt Ready)": {"w": 896, "h": 1120, "ratio": "4:5"},
    "3:4 Poster (Wall Art)": {"w": 768, "h": 1024, "ratio": "3:4"},
}


# ─── UTILITY FUNCTIONS ──────────────────────────────────────────────────────

def sanitize_prompt(prompt: str) -> str:
    """Strip banned glossy/3D buzzwords from prompt."""
    cleaned = prompt
    for term in BANNED_TERMS:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        cleaned = pattern.sub("", cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def build_pod_prompt(user_prompt: str, preset: dict, extra_modifiers: str = "") -> str:
    """Build a fully-engineered POD-optimized prompt."""
    base = sanitize_prompt(user_prompt)
    parts = [base, preset["style_hint"], preset["modifiers"]]
    if extra_modifiers:
        parts.append(extra_modifiers)
    parts.append("isolated on clean white background, POD ready artwork, no background")
    return ", ".join(filter(None, parts))


def image_to_base64(img: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def base64_to_image(b64_str: str) -> Image.Image:
    """Convert base64 string to PIL Image."""
    img_bytes = base64.b64decode(b64_str)
    return Image.open(io.BytesIO(img_bytes)).convert("RGB")


def url_to_image(url: str) -> Image.Image:
    """Fetch image from URL and return PIL Image."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")


def image_to_download_bytes(img: Image.Image) -> bytes:
    """Convert PIL Image to PNG bytes for download."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", dpi=(300, 300))
    return buf.getvalue()


def get_secret(key: str, default: str = "") -> str:
    """Safely retrieve Streamlit secret."""
    try:
        val = st.secrets.get(key, default)
        return val if val else default
    except Exception:
        return default


# ─── API CLIENTS ────────────────────────────────────────────────────────────

def generate_with_replicate(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    cfg_scale: float,
    api_token: str,
    num_outputs: int = 1,
) -> list[Image.Image]:
    """Tier 1: Replicate FLUX.1-dev generation."""
    import replicate
    
    client = replicate.Client(api_token=api_token)
    
    # Try flux-dev first, fall back to schnell
    try:
        output = client.run(
            "black-forest-labs/flux-dev",
            input={
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_outputs": num_outputs,
                "guidance": cfg_scale,
                "num_inference_steps": 28,
                "output_format": "png",
                "output_quality": 95,
            },
        )
    except Exception:
        output = client.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_outputs": num_outputs,
                "output_format": "png",
                "output_quality": 95,
            },
        )
    
    images = []
    for item in output:
        if hasattr(item, "read"):
            img = Image.open(io.BytesIO(item.read())).convert("RGB")
        elif isinstance(item, str):
            img = url_to_image(item)
        else:
            img = url_to_image(str(item))
        images.append(img)
    
    return images


def generate_with_gemini(
    prompt: str,
    api_key: str,
    aspect_ratio: str,
    num_images: int = 1,
) -> list[Image.Image]:
    """Tier 2: Google Gemini Imagen 3 generation."""
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=api_key)
    
    response = client.models.generate_images(
        model="imagen-3.0-generate-001",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=min(num_images, 4),
            aspect_ratio=aspect_ratio,
            safety_filter_level="block_only_high",
            person_generation="allow_adult",
        ),
    )
    
    images = []
    for gen_image in response.generated_images:
        img_bytes = gen_image.image.image_bytes
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        images.append(img)
    
    return images


def generate_with_pollinations(
    prompt: str,
    width: int,
    height: int,
    num_outputs: int = 1,
    seed: Optional[int] = None,
) -> list[Image.Image]:
    """Tier 3: Pollinations.ai free fallback generation."""
    images = []
    
    for i in range(num_outputs):
        current_seed = (seed or int(time.time())) + i
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Add watercolor/artistic model hint via nologo param
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&seed={current_seed}"
            f"&nologo=true&enhance=false&model=flux"
        )
        
        try:
            resp = requests.get(url, timeout=90)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            images.append(img)
            time.sleep(0.5)  # Be kind to free API
        except Exception as e:
            # If individual image fails, try once more with different seed
            try:
                alt_url = (
                    f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                    f"?width={width}&height={height}&seed={current_seed + 1000}"
                    f"&nologo=true&model=turbo"
                )
                resp = requests.get(alt_url, timeout=90)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                images.append(img)
            except Exception:
                raise RuntimeError(f"Pollinations fallback failed: {e}")
    
    return images


def generate_image_to_image_replicate(
    prompt: str,
    source_image: Image.Image,
    strength: float,
    api_token: str,
    num_outputs: int = 1,
) -> list[Image.Image]:
    """Tier 1 Img2Img: Replicate FLUX img2img style transfer."""
    import replicate
    
    client = replicate.Client(api_token=api_token)
    
    buf = io.BytesIO()
    source_image.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    
    output = client.run(
        "black-forest-labs/flux-dev",
        input={
            "prompt": prompt,
            "image": buf,
            "strength": strength,
            "num_outputs": num_outputs,
            "guidance": 4.0,
            "num_inference_steps": 28,
            "output_format": "png",
        },
    )
    
    images = []
    for item in output:
        if hasattr(item, "read"):
            img = Image.open(io.BytesIO(item.read())).convert("RGB")
        elif isinstance(item, str):
            img = url_to_image(item)
        else:
            img = url_to_image(str(item))
        images.append(img)
    
    return images


# ─── TRIPLE-TIER FALLBACK ENGINE ────────────────────────────────────────────

PAYMENT_ERRORS = ["402", "payment required", "insufficient credits", "quota"]
AUTH_ERRORS = ["401", "authentication", "unauthorized", "invalid api key", "api key"]
RATE_ERRORS = ["429", "rate limit", "too many requests"]


def is_payment_or_rate_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in PAYMENT_ERRORS + RATE_ERRORS)


def is_auth_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in AUTH_ERRORS)


def run_triple_tier_generation(
    prompt: str,
    negative_prompt: str,
    preset: dict,
    aspect_ratio_key: str,
    num_outputs: int,
    replicate_token: str,
    gemini_key: str,
    status_container,
) -> Tuple[list[Image.Image], str]:
    """
    Execute triple-tier silent fallback generation.
    Returns (images, provider_name).
    """
    ar = ASPECT_RATIOS[aspect_ratio_key]
    width, height = ar["w"], ar["h"]
    ratio_str = ar["ratio"]
    cfg = preset["cfg_scale"]
    
    # ── TIER 1: Replicate ──────────────────────────────────────────────────
    if replicate_token and replicate_token.strip():
        try:
            status_container.markdown(
                '<div class="gen-status">⚡ Generating via <strong>Replicate FLUX.1-dev</strong>… '
                'This usually takes 15–30 seconds.</div>',
                unsafe_allow_html=True,
            )
            images = generate_with_replicate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                cfg_scale=cfg,
                api_token=replicate_token,
                num_outputs=num_outputs,
            )
            return images, "replicate"
        except Exception as e:
            err = str(e)
            if is_payment_or_rate_error(e) or is_auth_error(e) or "replicate" in err.lower():
                status_container.markdown(
                    '<div class="gen-status">⚠️ Replicate unavailable — switching to '
                    '<strong>Gemini Imagen 3</strong>…</div>',
                    unsafe_allow_html=True,
                )
            else:
                raise  # Unexpected error — propagate
    
    # ── TIER 2: Google Gemini Imagen 3 ────────────────────────────────────
    if gemini_key and gemini_key.strip():
        try:
            status_container.markdown(
                '<div class="gen-status">🔵 Generating via <strong>Google Gemini Imagen 3</strong>…</div>',
                unsafe_allow_html=True,
            )
            images = generate_with_gemini(
                prompt=prompt,
                api_key=gemini_key,
                aspect_ratio=ratio_str,
                num_images=num_outputs,
            )
            return images, "gemini"
        except Exception:
            status_container.markdown(
                '<div class="gen-status">⚠️ Gemini quota reached — switching to '
                '<strong>Free Fallback Engine</strong>…</div>',
                unsafe_allow_html=True,
            )
    
    # ── TIER 3: Pollinations.ai (Always Free) ─────────────────────────────
    status_container.markdown(
        '<div class="gen-status">✨ Generating via <strong>Free Fallback Engine</strong> '
        '(Pollinations.ai)… May take 20–60 seconds.</div>',
        unsafe_allow_html=True,
    )
    images = generate_with_pollinations(
        prompt=prompt,
        width=width,
        height=height,
        num_outputs=num_outputs,
    )
    return images, "pollinations"


def run_img2img_generation(
    prompt: str,
    source_image: Image.Image,
    strength: float,
    preset: dict,
    aspect_ratio_key: str,
    num_outputs: int,
    replicate_token: str,
    gemini_key: str,
    status_container,
) -> Tuple[list[Image.Image], str]:
    """Triple-tier Image-to-Image generation with style transfer."""
    ar = ASPECT_RATIOS[aspect_ratio_key]
    width, height = ar["w"], ar["h"]
    ratio_str = ar["ratio"]
    
    # Resize source image to target dimensions
    resized = source_image.resize((width, height), Image.LANCZOS)
    
    # ── TIER 1: Replicate Img2Img ─────────────────────────────────────────
    if replicate_token and replicate_token.strip():
        try:
            status_container.markdown(
                '<div class="gen-status">⚡ Applying style transfer via '
                '<strong>Replicate FLUX.1-dev</strong>…</div>',
                unsafe_allow_html=True,
            )
            images = generate_image_to_image_replicate(
                prompt=prompt,
                source_image=resized,
                strength=strength,
                api_token=replicate_token,
                num_outputs=num_outputs,
            )
            return images, "replicate"
        except Exception as e:
            if is_payment_or_rate_error(e) or is_auth_error(e):
                status_container.markdown(
                    '<div class="gen-status">⚠️ Replicate unavailable — falling back to '
                    '<strong>Gemini + style context injection</strong>…</div>',
                    unsafe_allow_html=True,
                )
            else:
                raise
    
    # ── TIER 2: Gemini (style context in prompt) ───────────────────────────
    if gemini_key and gemini_key.strip():
        try:
            style_prompt = (
                f"Transform this image reference into: {prompt}. "
                f"Maintain the composition but apply {preset['style_hint']} treatment. "
                f"{preset['modifiers']}"
            )
            status_container.markdown(
                '<div class="gen-status">🔵 Applying style via '
                '<strong>Gemini Imagen 3</strong>…</div>',
                unsafe_allow_html=True,
            )
            images = generate_with_gemini(
                prompt=style_prompt,
                api_key=gemini_key,
                aspect_ratio=ratio_str,
                num_images=num_outputs,
            )
            return images, "gemini"
        except Exception:
            status_container.markdown(
                '<div class="gen-status">⚠️ Gemini unavailable — using '
                '<strong>Free Fallback Engine</strong>…</div>',
                unsafe_allow_html=True,
            )
    
    # ── TIER 3: Pollinations style-injected prompt ────────────────────────
    status_container.markdown(
        '<div class="gen-status">✨ Applying style via <strong>Free Fallback Engine</strong>…</div>',
        unsafe_allow_html=True,
    )
    images = generate_with_pollinations(
        prompt=prompt,
        width=width,
        height=height,
        num_outputs=num_outputs,
    )
    return images, "pollinations"


# ─── UI COMPONENTS ──────────────────────────────────────────────────────────

def render_provider_badge(provider: str) -> str:
    badges = {
        "replicate": '<span class="render-badge badge-replicate">⚡ Rendered via Replicate FLUX.1-dev</span>',
        "gemini": '<span class="render-badge badge-gemini">🔵 Rendered via Gemini Imagen 3</span>',
        "pollinations": '<span class="render-badge badge-pollinations">✨ Rendered via Free Fallback Engine</span>',
    }
    return badges.get(provider, "")


def render_image_results(images: list[Image.Image], provider: str, prefix: str = "design"):
    """Render generated images with download buttons."""
    cols = st.columns(min(len(images), 2))
    
    for i, img in enumerate(images):
        col = cols[i % len(cols)]
        with col:
            st.markdown(
                f'<div class="result-card">'
                f'{render_provider_badge(provider)}'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.image(img, use_container_width=True)
            
            dl_bytes = image_to_download_bytes(img)
            filename = f"DCH_{prefix}_{i+1}_{int(time.time())}.png"
            st.download_button(
                label=f"⬇️ Download Design {i+1} (PNG 300dpi)",
                data=dl_bytes,
                file_name=filename,
                mime="image/png",
                key=f"dl_{prefix}_{i}_{int(time.time())}",
                use_container_width=True,
            )


# ─── SIDEBAR ────────────────────────────────────────────────────────────────

def render_sidebar() -> Tuple[str, str, str, int, str, float]:
    """Render sidebar and return (replicate_token, gemini_key, aspect_ratio, variations, preset_name, image_influence)."""
    
    with st.sidebar:
        # Logo & Title
        st.markdown("""
        <div style="text-align:center; padding: 0.5rem 0 1rem;">
          <div style="font-family: 'Playfair Display', serif; font-size: 1.4rem; color: #2D2D2D; font-weight: 700;">
            🎨 DesignCreationHub
          </div>
          <div style="font-size: 0.7rem; color: #C4876A; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 0.2rem;">
            v6.0 · POD Edition
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        
        # ── API Configuration ──────────────────────────────────────────────
        st.markdown("**🔑 API Configuration**")
        
        default_replicate = get_secret("REPLICATE_API_TOKEN")
        default_gemini = get_secret("GEMINI_API_KEY")
        
        replicate_token = st.text_input(
            "Replicate API Token",
            value=default_replicate,
            type="password",
            placeholder="r8_xxxxxxxxxxxxxxxx",
            help="Get free token at replicate.com · Tier 1 provider",
        )
        
        gemini_key = st.text_input(
            "Gemini API Key",
            value=default_gemini,
            type="password",
            placeholder="AIzaSy...",
            help="Get free key at aistudio.google.com · Tier 2 provider",
        )
        
        # Provider Status Panel
        rep_connected = bool(replicate_token and replicate_token.strip())
        gem_connected = bool(gemini_key and gemini_key.strip())
        
        rep_class = "provider-connected" if rep_connected else "provider-disconnected"
        rep_dot = "dot-green" if rep_connected else "dot-red"
        rep_status = "Connected" if rep_connected else "Not configured"
        
        gem_class = "provider-connected" if gem_connected else "provider-disconnected"
        gem_dot = "dot-green" if gem_connected else "dot-red"
        gem_status = "Connected" if gem_connected else "Not configured"
        
        st.markdown(f"""
        <div class="provider-grid" style="margin-top:0.75rem;">
          <div class="provider-badge {rep_class}">
            <span class="status-dot {rep_dot}"></span>
            <span><strong>Tier 1</strong> Replicate FLUX</span>
            <span style="margin-left:auto; font-size:0.7rem;">{rep_status}</span>
          </div>
          <div class="provider-badge {gem_class}">
            <span class="status-dot {gem_dot}"></span>
            <span><strong>Tier 2</strong> Gemini Imagen 3</span>
            <span style="margin-left:auto; font-size:0.7rem;">{gem_status}</span>
          </div>
          <div class="provider-badge provider-free">
            <span class="status-dot dot-gold"></span>
            <span><strong>Tier 3</strong> Pollinations.ai</span>
            <span style="margin-left:auto; font-size:0.7rem;">Always Free ✓</span>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        
        # ── Style Preset Selector ──────────────────────────────────────────
        st.markdown("**🎨 Style Preset**")
        
        preset_names = list(PRESETS.keys())
        
        if "selected_preset" not in st.session_state:
            st.session_state.selected_preset = preset_names[0]
        
        # Preset Cards
        card_cols = st.columns(2)
        for idx, name in enumerate(preset_names):
            p = PRESETS[name]
            col = card_cols[idx % 2]
            with col:
                is_active = st.session_state.selected_preset == name
                border_color = "#8B5E3C" if is_active else "#D4C5A9"
                bg_color = "#E8DDD0" if is_active else "#F5F0E8"
                if st.button(
                    f"{p['emoji']} {name}",
                    key=f"preset_{idx}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.selected_preset = name
                    st.rerun()
        
        selected_preset = st.session_state.selected_preset
        preset_data = PRESETS[selected_preset]
        
        st.markdown(
            f'<div class="info-panel" style="margin-top:0.5rem;">'
            f'<strong>{preset_data["emoji"]} {selected_preset}</strong><br>'
            f'<span style="font-size:0.78rem; color:#6B5540;">{preset_data["desc"]}</span><br>'
            f'<span style="font-size:0.72rem; color:#8B7355; margin-top:0.3rem; display:block;">'
            f'CFG: {preset_data["cfg_scale"]} · Watercolor-optimized</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        
        # ── Output Settings ────────────────────────────────────────────────
        st.markdown("**📐 Output Settings**")
        
        aspect_ratio = st.selectbox(
            "Aspect Ratio",
            options=list(ASPECT_RATIOS.keys()),
            index=0,
            help="Choose based on your POD product type",
        )
        
        variations = st.slider(
            "Number of Variations",
            min_value=1,
            max_value=4,
            value=1,
            step=1,
            help="Generate multiple design variations at once",
        )
        
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        
        # ── Image Influence (for Img2Img) ──────────────────────────────────
        st.markdown("**🔄 Style Transfer Strength**")
        st.markdown(
            '<div class="prompt-tip">Used in Image → Image tab. '
            'Higher = more style applied, lower = closer to original.</div>',
            unsafe_allow_html=True,
        )
        
        image_influence = st.slider(
            "Image Influence",
            min_value=0.30,
            max_value=0.70,
            value=0.55,
            step=0.05,
            format="%.2f",
        )
        
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        
        # ── Tips ───────────────────────────────────────────────────────────
        with st.expander("💡 POD Prompt Tips"):
            st.markdown("""
            **Best Practices:**
            - Describe the **subject** clearly (e.g. "wildflower bouquet", "sleeping fox")
            - Mention **placement** if needed (e.g. "centered chest graphic")
            - Add **mood words** (cozy, whimsical, rustic, enchanted)
            - Specify **color direction** (autumn tones, dusty pastels, earth tones)
            
            **Avoid These Words:**
            - ~~photorealistic, 8k, HDR, sharp focus~~
            - ~~3D render, Unreal Engine~~
            - ~~vibrant, ultra-detailed~~
            
            The app auto-removes these for you! ✓
            """)
        
        st.markdown(
            '<div class="watermark-strip">DesignCreationHub v6.0 · POD Edition</div>',
            unsafe_allow_html=True,
        )
    
    return replicate_token, gemini_key, aspect_ratio, variations, selected_preset, image_influence


# ─── TAB 1: TEXT → IMAGE ────────────────────────────────────────────────────

def render_text_to_image_tab(
    replicate_token: str,
    gemini_key: str,
    aspect_ratio: str,
    variations: int,
    preset_name: str,
):
    st.markdown("""
    <div class="info-panel">
      <strong>🎨 POD Graphic Generator</strong><br>
      Describe your design concept and let the triple-tier AI engine render it 
      as print-ready artwork. Prompts are automatically engineered for Etsy POD aesthetics.
    </div>
    """, unsafe_allow_html=True)
    
    preset = PRESETS[preset_name]
    
    # Example prompts per preset
    examples = {
        "Etsy Vintage Watercolor": [
            "A delicate wildflower bouquet with lavender, chamomile and baby's breath",
            "A sleeping hedgehog curled among autumn leaves and acorns",
            "A mason jar filled with sunflowers and eucalyptus stems",
        ],
        "Cottagecore Fall": [
            "Cozy pumpkin patch with dried herbs and wheat stalks",
            "A warm farmhouse kitchen scene with apple pie and candles",
            "Mushrooms and ferns in a misty forest clearing",
        ],
        "Distressed Screenprint": [
            "A vintage mountain range with rising sun and pine trees",
            "A classic American eagle with banner and stars",
            "Retro surfboard with tropical palm and sunset",
        ],
        "Retro 70s Floral": [
            "Bold daisy and sunflower arrangement in a ceramic pot",
            "Groovy butterfly surrounded by psychedelic flowers",
            "Peace sign wreathed in bold botanical florals",
        ],
    }
    
    # Prompt Input
    col_main, col_hint = st.columns([2, 1])
    
    with col_main:
        user_prompt = st.text_area(
            "✍️ Describe Your Design",
            placeholder=f"e.g. {examples[preset_name][0]}",
            height=100,
            help="Be descriptive about subject, mood, and composition. Avoid glossy/3D terms — the engine handles that!",
        )
    
    with col_hint:
        st.markdown("**💬 Try These:**")
        for ex in examples[preset_name]:
            if st.button(f"↗ {ex[:35]}…" if len(ex) > 35 else f"↗ {ex}", key=f"ex_{ex[:20]}", use_container_width=True):
                st.session_state.user_prompt_t2i = ex
                st.rerun()
    
    # Use session state to hold prompt from example clicks
    if "user_prompt_t2i" in st.session_state and not user_prompt:
        user_prompt = st.session_state.user_prompt_t2i
    
    # Advanced Options
    with st.expander("⚙️ Advanced Prompt Options"):
        extra_modifiers = st.text_input(
            "Additional Style Modifiers",
            placeholder="e.g. sage green color palette, minimalist composition",
            help="These are appended to your prompt alongside the preset modifiers",
        )
        
        show_engineered = st.checkbox("Preview Engineered Prompt", value=False)
        
        if show_engineered and user_prompt:
            engineered = build_pod_prompt(user_prompt, preset, extra_modifiers)
            st.markdown("**🔧 Auto-Engineered Prompt:**")
            st.code(engineered, language=None)
            
            cleaned = sanitize_prompt(user_prompt)
            if cleaned != user_prompt:
                st.warning(f"🔇 Removed glossy terms. Cleaned: _{cleaned}_")
    
    # Generate Button
    st.markdown("<br>", unsafe_allow_html=True)
    
    ar_info = ASPECT_RATIOS[aspect_ratio]
    generate_label = (
        f"🎨 Generate {variations} Design{'s' if variations > 1 else ''} "
        f"({ar_info['w']}×{ar_info['h']} · {preset_name})"
    )
    
    generate_btn = st.button(
        generate_label,
        type="primary",
        use_container_width=True,
        disabled=not user_prompt.strip(),
    )
    
    if not user_prompt.strip():
        st.markdown(
            '<div class="prompt-tip" style="text-align:center; margin-top:0.3rem;">'
            '👆 Enter a design description above to enable generation</div>',
            unsafe_allow_html=True,
        )
    
    # Generation
    if generate_btn and user_prompt.strip():
        engineered_prompt = build_pod_prompt(
            user_prompt,
            preset,
            extra_modifiers if "extra_modifiers" in dir() else "",
        )
        negative = preset["negative"]
        
        status_container = st.empty()
        
        try:
            with st.spinner(""):
                images, provider = run_triple_tier_generation(
                    prompt=engineered_prompt,
                    negative_prompt=negative,
                    preset=preset,
                    aspect_ratio_key=aspect_ratio,
                    num_outputs=variations,
                    replicate_token=replicate_token,
                    gemini_key=gemini_key,
                    status_container=status_container,
                )
            
            status_container.empty()
            
            st.success(f"✅ Generated {len(images)} design{'s' if len(images) > 1 else ''} successfully!")
            
            # Store in session for persistence
            st.session_state.t2i_results = {"images": images, "provider": provider}
        
        except Exception as e:
            status_container.empty()
            st.error(f"❌ Generation failed across all providers. Error: {str(e)[:200]}")
            st.markdown("""
            <div class="info-panel">
              <strong>Troubleshooting:</strong><br>
              • Check your internet connection<br>
              • Verify your API keys are valid<br>
              • The free tier (Tier 3) should always work — if it fails, try again in 30 seconds<br>
              • Try a simpler, shorter prompt
            </div>
            """, unsafe_allow_html=True)
    
    # Display Results (persistent across reruns)
    if "t2i_results" in st.session_state:
        results = st.session_state.t2i_results
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown("### 🖼️ Your Designs")
        render_image_results(results["images"], results["provider"], prefix="t2i")


# ─── TAB 2: IMAGE → IMAGE / STYLE TRANSFER ──────────────────────────────────

def render_image_to_image_tab(
    replicate_token: str,
    gemini_key: str,
    aspect_ratio: str,
    variations: int,
    preset_name: str,
    image_influence: float,
):
    st.markdown("""
    <div class="info-panel">
      <strong>🔄 Style Transfer & Moodboard Engine</strong><br>
      Upload a reference image (competitor design, moodboard, or inspiration photo) 
      and describe the style you want applied. The engine preserves composition while 
      transforming it into your chosen POD aesthetic.
    </div>
    """, unsafe_allow_html=True)
    
    preset = PRESETS[preset_name]
    
    col_upload, col_settings = st.columns([1, 1])
    
    with col_upload:
        st.markdown("**📁 Reference Image**")
        uploaded_file = st.file_uploader(
            "Upload moodboard or competitor design",
            type=["png", "jpg", "jpeg", "webp"],
            help="Upload any inspiration image. Supports PNG, JPG, WEBP.",
            label_visibility="collapsed",
        )
        
        if uploaded_file:
            source_img = Image.open(uploaded_file).convert("RGB")
            st.image(source_img, caption="📌 Reference Image", use_container_width=True)
            
            # Image info
            w, h = source_img.size
            st.markdown(
                f'<div class="prompt-tip">Original size: {w}×{h}px · '
                f'Will be resized to {ASPECT_RATIOS[aspect_ratio]["w"]}×'
                f'{ASPECT_RATIOS[aspect_ratio]["h"]}px</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown("""
            <div style="border: 2px dashed #D4C5A9; border-radius: 10px; padding: 2rem; 
                        text-align: center; color: #8B7355; background: #FAF7F2;">
              <div style="font-size: 2rem; margin-bottom: 0.5rem;">🖼️</div>
              <div style="font-size: 0.85rem;">Drop your reference image here</div>
              <div style="font-size: 0.72rem; margin-top: 0.3rem; color: #B8A88A;">
                PNG · JPG · WEBP supported
              </div>
            </div>
            """, unsafe_allow_html=True)
            source_img = None
    
    with col_settings:
        st.markdown("**✍️ Style Direction**")
        
        style_prompt = st.text_area(
            "Describe the style transformation",
            placeholder=(
                "e.g. Convert this into a hand-painted watercolor botanical "
                "illustration with soft muted autumn tones"
            ),
            height=110,
            help="Describe how you want the reference image transformed",
        )
        
        # Style preset quick-apply
        st.markdown("**⚡ Quick Style Apply:**")
        quick_cols = st.columns(2)
        
        style_templates = [
            ("🌸 Watercolor", "Transform into soft hand-painted watercolor botanical illustration, delicate ink linework, muted pastel tones"),
            ("🍂 Cottagecore", "Apply warm cottagecore autumn aesthetic, rustic handmade quality, golden harvest palette"),
            ("👕 Screenprint", "Convert to distressed vintage screenprint, 2-color print style, aged halftone texture"),
            ("🌻 Retro 70s", "Transform into bold 70s retro poster illustration, earthy groovy palette, folk art style"),
        ]
        
        for idx, (label, template) in enumerate(style_templates):
            col = quick_cols[idx % 2]
            with col:
                if st.button(label, key=f"style_tmpl_{idx}", use_container_width=True):
                    st.session_state.style_prompt_i2i = template
                    st.rerun()
        
        if "style_prompt_i2i" in st.session_state and not style_prompt:
            style_prompt = st.session_state.style_prompt_i2i
        
        # Strength Info
        strength_val = 1.0 - image_influence
        st.markdown(
            f'<div class="info-panel" style="margin-top:0.75rem;">'
            f'<strong>Influence Strength:</strong> {image_influence:.0%}<br>'
            f'<span style="font-size:0.75rem;">'
            f'{"🎨 High style application — creative transformation" if image_influence > 0.55 else "🔒 Conservative — closer to reference composition"}'
            f'</span></div>',
            unsafe_allow_html=True,
        )
    
    # Generate Button
    st.markdown("<br>", unsafe_allow_html=True)
    
    can_generate = source_img is not None and bool(style_prompt.strip() if style_prompt else False)
    
    transfer_label = (
        f"🔄 Apply Style Transfer · {variations} Variation{'s' if variations > 1 else ''} "
        f"· {image_influence:.0%} Influence"
    )
    
    transfer_btn = st.button(
        transfer_label,
        type="primary",
        use_container_width=True,
        disabled=not can_generate,
    )
    
    if not source_img:
        st.markdown(
            '<div class="prompt-tip" style="text-align:center;">👆 Upload a reference image to enable style transfer</div>',
            unsafe_allow_html=True,
        )
    elif not (style_prompt and style_prompt.strip()):
        st.markdown(
            '<div class="prompt-tip" style="text-align:center;">✍️ Add a style direction description above</div>',
            unsafe_allow_html=True,
        )
    
    # Execute Style Transfer
    if transfer_btn and can_generate:
        # Build full engineered prompt
        full_prompt = build_pod_prompt(style_prompt, preset)
        
        status_container = st.empty()
        
        try:
            with st.spinner(""):
                images, provider = run_img2img_generation(
                    prompt=full_prompt,
                    source_image=source_img,
                    strength=image_influence,
                    preset=preset,
                    aspect_ratio_key=aspect_ratio,
                    num_outputs=variations,
                    replicate_token=replicate_token,
                    gemini_key=gemini_key,
                    status_container=status_container,
                )
            
            status_container.empty()
            st.success(f"✅ Style transfer complete! {len(images)} variation{'s' if len(images) > 1 else ''} generated.")
            
            st.session_state.i2i_results = {"images": images, "provider": provider}
        
        except Exception as e:
            status_container.empty()
            st.error(f"❌ Style transfer failed: {str(e)[:200]}")
    
    # Display Results
    if "i2i_results" in st.session_state:
        results = st.session_state.i2i_results
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        
        # Side-by-side comparison if source available
        if source_img:
            st.markdown("### 🔄 Before → After")
            comp_cols = st.columns([1, 2])
            with comp_cols[0]:
                st.markdown("**Original Reference**")
                st.image(source_img, use_container_width=True)
            with comp_cols[1]:
                st.markdown("**Styled Variations**")
                render_image_results(results["images"], results["provider"], prefix="i2i")
        else:
            render_image_results(results["images"], results["provider"], prefix="i2i")


# ─── MAIN APP ────────────────────────────────────────────────────────────────

def main():
    # Header
    st.markdown("""
    <div class="hub-header">
      <div class="hub-title">Design<span>Creation</span>Hub</div>
      <div class="hub-subtitle">Professional POD Graphics Studio</div>
      <div class="hub-badge">v6.0 · Etsy Seller Edition · Triple-Tier AI Engine</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar — returns all global settings
    replicate_token, gemini_key, aspect_ratio, variations, preset_name, image_influence = render_sidebar()
    
    # Main Tabs
    tab1, tab2 = st.tabs(["🎨 Text → Image", "🔄 Image → Image / Style Transfer"])
    
    with tab1:
        render_text_to_image_tab(
            replicate_token=replicate_token,
            gemini_key=gemini_key,
            aspect_ratio=aspect_ratio,
            variations=variations,
            preset_name=preset_name,
        )
    
    with tab2:
        render_image_to_image_tab(
            replicate_token=replicate_token,
            gemini_key=gemini_key,
            aspect_ratio=aspect_ratio,
            variations=variations,
            preset_name=preset_name,
            image_influence=image_influence,
        )


if __name__ == "__main__":
    main()
