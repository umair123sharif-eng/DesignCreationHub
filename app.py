"""
DesignCreationHub — Production-Ready AI Image Generation Studio
Author: Special Pixel Studio (Sharif)

Features:
  1. Zero-blocking engine chain — works with NO API key:
       premium (Replicate / Hugging Face, only if a key is present)
         → Pollinations FLUX (free, text→image)
         → AI Horde community GPUs (free, text→image AND image→image)
  2. Automatic Prompt Enhancer (rich 8K diffusion prompts, de-duplicated tags)
  3. True Image-to-Image with reference upload + strength slider
  4. Professional UI: sidebar, style presets, negative prompt builder, gallery

Optional secrets (Streamlit Cloud → App settings → Secrets):
    REPLICATE_API_TOKEN = "r8_..."
    HF_TOKEN            = "hf_..."
    POLLINATIONS_API_KEY = "sk_..."   # free key from enter.pollinations.ai
NOTE: server-side secrets are used for EVERY visitor of a public app.
"""

from __future__ import annotations

import base64
import io
import os
import random
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple
from urllib.parse import quote

import requests
import streamlit as st
from PIL import Image, ImageOps

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="DesignCreationHub",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark canvas background */
.stApp {
    background: #0d0f14;
    color: #e8eaf0;
}

/* Header gradient strip */
.app-header {
    background: linear-gradient(135deg, #1a1d2e 0%, #0f1629 50%, #1a1035 100%);
    border: 1px solid #2a2d3e;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.app-header::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(99,87,255,0.18) 0%, transparent 70%);
    pointer-events: none;
}
.app-header h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 6px 0;
    letter-spacing: -0.5px;
}
.app-header p {
    color: #8890a8;
    font-size: 0.95rem;
    margin: 0;
}
.header-badge {
    display: inline-block;
    background: rgba(99,87,255,0.2);
    border: 1px solid rgba(99,87,255,0.4);
    color: #a09bff;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 10px;
    letter-spacing: 0.5px;
}

/* Section cards */
.section-card {
    background: #13161f;
    border: 1px solid #1e2130;
    border-radius: 14px;
    padding: 22px 24px;
    margin-bottom: 18px;
}
.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.8rem;
    font-weight: 600;
    color: #6357ff;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 14px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0b0d14 !important;
    border-right: 1px solid #1a1d2e !important;
}
[data-testid="stSidebar"] .block-container {
    padding: 20px 16px;
}

/* Profile card in sidebar */
.profile-card {
    background: linear-gradient(160deg, #1a1d2e, #12151f);
    border: 1px solid #2a2d3e;
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    margin-bottom: 20px;
}
.profile-avatar { font-size: 2.5rem; margin-bottom: 8px; }
.profile-name {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    color: #e8eaf0;
    margin-bottom: 4px;
}
.profile-role { font-size: 0.78rem; color: #6357ff; margin-bottom: 10px; }
.profile-stat {
    display: inline-block;
    background: rgba(99,87,255,0.1);
    border: 1px solid rgba(99,87,255,0.2);
    color: #a09bff;
    font-size: 0.72rem;
    padding: 3px 8px;
    border-radius: 8px;
    margin: 2px;
}

/* Generate button */
.stButton > button {
    background: linear-gradient(135deg, #6357ff, #9b4dca);
    color: white;
    border: none;
    border-radius: 10px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    padding: 14px 32px;
    width: 100%;
    transition: opacity 0.2s;
    letter-spacing: 0.3px;
}
.stButton > button:hover { opacity: 0.88; }

/* Prompt textarea */
.stTextArea textarea {
    background: #0d0f14 !important;
    border: 1px solid #2a2d3e !important;
    border-radius: 10px !important;
    color: #e8eaf0 !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextArea textarea:focus {
    border-color: #6357ff !important;
    box-shadow: 0 0 0 2px rgba(99,87,255,0.15) !important;
}

/* Selectbox & sliders */
.stSelectbox > div > div {
    background: #13161f !important;
    border: 1px solid #2a2d3e !important;
    border-radius: 8px !important;
    color: #e8eaf0 !important;
}

/* Enhanced prompt display */
.enhanced-prompt-box {
    background: #0d1020;
    border: 1px solid #2a3060;
    border-left: 3px solid #6357ff;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: #b0b8d0;
    line-height: 1.6;
    font-style: italic;
    margin-top: 10px;
}

/* Status badges */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(16,185,129,0.12);
    border: 1px solid rgba(16,185,129,0.3);
    color: #34d399;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
}
.status-pill.error {
    background: rgba(239,68,68,0.12);
    border-color: rgba(239,68,68,0.3);
    color: #f87171;
}
.status-line {
    color: #8890a8;
    font-size: 0.85rem;
    padding: 6px 0;
}
.engine-note {
    background: rgba(99,87,255,0.08);
    border: 1px solid rgba(99,87,255,0.25);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 0.78rem;
    color: #a09bff;
    margin-bottom: 8px;
}

/* Hide Streamlit default elements */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
# Premium engines (used only when a key is available)
REPLICATE_TXT2IMG_MODEL = "black-forest-labs/flux-1.1-pro"   # text → image only
REPLICATE_IMG2IMG_MODEL = "black-forest-labs/flux-dev"       # supports image + prompt_strength
HF_TXT2IMG_MODEL = "black-forest-labs/FLUX.1-schnell"
HF_IMG2IMG_MODEL = "black-forest-labs/FLUX.1-Kontext-dev"

# Free engines
POLLINATIONS_ANON_URL = "https://image.pollinations.ai/prompt/"   # keyless (legacy) endpoint
POLLINATIONS_KEY_URL = "https://gen.pollinations.ai/image/"        # keyed endpoint
POLLINATIONS_KEY_MODEL = "black-forest-labs/flux.1-schnell"
HORDE_API = "https://aihorde.net/api/v2"
HORDE_ANON_KEY = "0000000000"
HORDE_TIMEOUT_S = 300

STYLE_PRESETS = {
    "None": "",
    "🎨 Digital Art": "digital art style, concept art, vibrant colors, artstation trending",
    "📸 Photorealistic": "photorealistic, hyperrealistic, DSLR photography, sharp focus, studio lighting",
    "🖼️ Oil Painting": "oil painting, classical art, textured brushstrokes, museum quality, old masters style",
    "🌆 Cyberpunk": "cyberpunk aesthetic, neon lights, rain-soaked streets, futuristic city, blade runner style",
    "🌿 Studio Ghibli": "Studio Ghibli style, soft watercolor, whimsical, serene, hand-drawn anime",
    "⚡ Anime": "anime style, cel shading, vibrant, detailed anime illustration, manga-inspired",
    "🏺 3D Render": "3D render, octane render, ray tracing, subsurface scattering, blender, cinema 4d",
    "🖋️ Ink Sketch": "ink sketch, pen and ink, cross-hatching, black and white illustration, detailed linework",
    "✨ Fantasy": "fantasy art, magical, ethereal glow, epic fantasy illustration, concept art",
}

NEGATIVE_PRESETS = {
    "General Quality": "blurry, low quality, pixelated, jpeg artifacts, watermark, signature, text",
    "No Humans": "people, human, person, face, hands, body",
    "No Distortion": "distorted, deformed, disfigured, bad anatomy, extra limbs, mutated",
    "Clean Background": "cluttered background, busy background, distracting elements, noise",
    "No AI Tells": "ai artifacts, uncanny valley, plastic look, oversaturated, unnatural lighting",
}

CAMERA_ANGLES = [
    "eye level", "bird's eye view", "worm's eye view", "dutch angle",
    "close-up", "extreme close-up", "wide shot", "medium shot",
    "over the shoulder", "aerial perspective",
]

LIGHTING_STYLES = [
    "golden hour lighting", "studio lighting", "rim lighting", "volumetric light",
    "cinematic lighting", "dramatic shadows", "soft diffused light",
    "neon glow", "moonlight", "backlit silhouette",
]

# label -> (width, height, aspect_ratio string for Replicate)
RESOLUTIONS = {
    "1024×1024 (Square)": (1024, 1024, "1:1"),
    "1344×768 (Landscape 16:9)": (1344, 768, "16:9"),
    "768×1344 (Portrait 9:16)": (768, 1344, "9:16"),
    "1280×720 (HD)": (1280, 720, "16:9"),
}

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
for _k, _v in {
    "results_t2i": [],
    "results_i2i": [],
    "gallery": [],
    "generation_count": 0,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────
# DATA CLASSES / ERRORS
# ─────────────────────────────────────────────
class EngineError(RuntimeError):
    """Raised when a single engine fails (the chain then tries the next one)."""


@dataclass
class GenParams:
    prompt: str
    negative: str
    width: int
    height: int
    aspect: str
    num_images: int
    steps: int
    guidance: float
    ref_image: Optional[Image.Image] = None
    strength: float = 0.65


StatusFn = Callable[[str], None]


# ─────────────────────────────────────────────
# HELPERS: SECRETS, PROMPTS, IMAGES
# ─────────────────────────────────────────────
def get_secret(name: str) -> str:
    """Read a server-side secret (Streamlit secrets or env var). Never sent to the browser."""
    try:
        val = st.secrets.get(name, "")
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(name, "")


def enhance_prompt(base_prompt: str, style_preset: str, camera: str, lighting: str, quality_tags: list) -> str:
    """Expand a simple prompt into a rich, de-duplicated diffusion prompt."""
    parts = [base_prompt.strip().rstrip(",. ")]

    extras: List[str] = []
    if style_preset:
        extras.append(style_preset)
    if camera and camera != "auto":
        extras.append(camera)
    if lighting and lighting != "auto":
        extras.append(lighting)
    extras.extend([
        "8K resolution", "ultra-detailed", "sharp focus",
        "masterpiece", "best quality", "professional",
    ])
    extras.extend(quality_tags)

    seen = set()
    for chunk in extras:
        for tag in (t.strip() for t in chunk.split(",")):
            key = tag.lower()
            if tag and key not in seen:
                seen.add(key)
                parts.append(tag)
    return ", ".join(parts)


def build_negative_prompt(selected_negatives: list, custom_neg: str) -> str:
    """Combine selected negative preset chunks with custom text."""
    chunks = [NEGATIVE_PRESETS[k] for k in selected_negatives if k in NEGATIVE_PRESETS]
    if custom_neg.strip():
        chunks.append(custom_neg.strip())
    return ", ".join(chunks)


def image_to_bytes(pil_image: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    pil_image.save(buf, format=fmt)
    return buf.getvalue()


def image_to_b64(pil_image: Image.Image, fmt: str = "JPEG", quality: int = 90) -> str:
    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        pil_image.convert("RGB").save(buf, format="JPEG", quality=quality)
    else:
        pil_image.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def open_image_bytes(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img.convert("RGB")


def prepare_reference(img: Image.Image, max_side: int = 1536) -> Image.Image:
    """Fix EXIF rotation and cap size so uploads stay light."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    return img


def short(err: Exception, n: int = 220) -> str:
    msg = " ".join(str(err).split())
    return msg if len(msg) <= n else msg[:n] + "…"


# ─────────────────────────────────────────────
# ENGINE 1 — REPLICATE (premium)
# ─────────────────────────────────────────────
def generate_replicate(p: GenParams, token: str, on_status: StatusFn) -> List[Image.Image]:
    """FLUX 1.1 Pro for text→image, FLUX Dev for image→image (the only one with prompt_strength)."""
    import replicate  # lazy import: the free engines work even if this package is missing

    client = replicate.Client(api_token=token)  # token stays scoped to this client (no os.environ leak)
    results: List[Image.Image] = []

    for i in range(p.num_images):
        on_status(f"Replicate FLUX — image {i + 1}/{p.num_images}")
        if p.ref_image is not None:
            buf = io.BytesIO(image_to_bytes(p.ref_image.convert("RGB"), "JPEG"))
            buf.name = "reference.jpg"
            model = REPLICATE_IMG2IMG_MODEL
            inputs = {
                "prompt": p.prompt,
                "image": buf,
                "prompt_strength": p.strength,          # 0 = copy image, 1 = ignore image
                "aspect_ratio": p.aspect,
                "num_inference_steps": min(p.steps, 50),
                "guidance": min(p.guidance, 10.0),
                "output_format": "png",
                "num_outputs": 1,
            }
        else:
            model = REPLICATE_TXT2IMG_MODEL
            inputs = {
                "prompt": p.prompt,
                "aspect_ratio": p.aspect,
                "output_format": "png",
                "safety_tolerance": 2,
                "prompt_upsampling": False,
            }

        output = client.run(model, input=inputs)
        items = output if isinstance(output, (list, tuple)) else [output]
        for item in items:
            data = item.read() if hasattr(item, "read") else requests.get(str(item), timeout=90).content
            results.append(open_image_bytes(data))
    return results


# ─────────────────────────────────────────────
# ENGINE 2 — HUGGING FACE (premium)
# ─────────────────────────────────────────────
def generate_huggingface(p: GenParams, token: str, on_status: StatusFn) -> List[Image.Image]:
    """Hugging Face Inference Providers via huggingface_hub (the old api-inference URL is deprecated)."""
    from huggingface_hub import InferenceClient  # lazy import

    client = InferenceClient(api_key=token)
    results: List[Image.Image] = []

    for i in range(p.num_images):
        on_status(f"Hugging Face FLUX — image {i + 1}/{p.num_images}")
        if p.ref_image is not None:
            # HF's image_to_image API has no strength parameter; the prompt drives the edit.
            img = client.image_to_image(
                image_to_bytes(p.ref_image.convert("RGB"), "JPEG"),
                prompt=p.prompt,
                model=HF_IMG2IMG_MODEL,
            )
        else:
            kwargs = {"model": HF_TXT2IMG_MODEL, "width": p.width, "height": p.height}
            if "schnell" not in HF_TXT2IMG_MODEL.lower():
                kwargs["num_inference_steps"] = p.steps
                kwargs["guidance_scale"] = p.guidance
            if p.negative and "flux" not in HF_TXT2IMG_MODEL.lower():
                kwargs["negative_prompt"] = p.negative
            img = client.text_to_image(p.prompt, **kwargs)
        results.append(img.convert("RGB"))
    return results


# ─────────────────────────────────────────────
# ENGINE 3 — POLLINATIONS FLUX (free, text→image)
# ─────────────────────────────────────────────
def generate_pollinations(p: GenParams, api_key: str, on_status: StatusFn) -> List[Image.Image]:
    if p.ref_image is not None:
        raise EngineError("Pollinations GET API cannot take an uploaded reference image")

    prompt = p.prompt[:1200]
    if api_key:
        url = POLLINATIONS_KEY_URL + quote(prompt, safe="")
        headers = {"Authorization": f"Bearer {api_key}"}
        base = {"model": POLLINATIONS_KEY_MODEL}
    else:
        url = POLLINATIONS_ANON_URL + quote(prompt, safe="")
        headers = {}
        base = {"model": "flux", "nologo": "true", "enhance": "false"}

    results: List[Image.Image] = []
    for i in range(p.num_images):
        on_status(f"Pollinations FLUX — image {i + 1}/{p.num_images}")
        params = {**base, "width": p.width, "height": p.height, "seed": random.randint(1, 2_000_000_000)}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=120)
        except requests.RequestException as e:
            if results:
                break
            raise EngineError(f"Pollinations unreachable ({short(e, 100)})")

        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            results.append(open_image_bytes(r.content))
        else:
            if results:
                break
            raise EngineError(f"Pollinations returned HTTP {r.status_code}")
    return results


# ─────────────────────────────────────────────
# ENGINE 4 — AI HORDE (free, community GPUs, text→image AND image→image)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def horde_models() -> list:
    r = requests.get(f"{HORDE_API}/status/models", params={"type": "image"}, timeout=20)
    r.raise_for_status()
    return r.json()


def pick_horde_model(models: list, img2img: bool) -> Optional[str]:
    live = [m for m in models if m.get("count", 0) > 0 and m.get("name")]
    if not live:
        return None
    live.sort(key=lambda m: m["count"], reverse=True)

    def first(*needles: str) -> Optional[str]:
        for needle in needles:
            for m in live:
                if needle in m["name"].lower():
                    return m["name"]
        return None

    if img2img:
        return first("sdxl", "juggernaut", "xl") or live[0]["name"]
    return first("schnell", "flux", "sdxl", "xl") or live[0]["name"]


def horde_dims(w: int, h: int) -> Tuple[int, int]:
    """Horde needs multiples of 64; anonymous users are capped at ~1024 px per side."""
    scale = min(1.0, 1024 / max(w, h))
    ww = min(1024, max(384, int(round(w * scale / 64)) * 64))
    hh = min(1024, max(384, int(round(h * scale / 64)) * 64))
    return ww, hh


def generate_horde(p: GenParams, on_status: StatusFn) -> List[Image.Image]:
    headers = {
        "apikey": HORDE_ANON_KEY,
        "Client-Agent": "DesignCreationHub:2.1:specialpixelstudio",
        "Content-Type": "application/json",
    }
    try:
        model = pick_horde_model(horde_models(), p.ref_image is not None)
    except Exception:
        model = None  # let the Horde route to any available worker

    is_flux = bool(model and "flux" in model.lower())
    ww, hh = horde_dims(p.width, p.height)
    n = max(1, min(p.num_images, 4))

    if is_flux:
        schnell = "schnell" in model.lower()
        steps = 8 if schnell else min(max(p.steps, 20), 28)
        cfg = 1.0 if schnell else min(p.guidance, 4.0)
        sampler = "k_euler"
        text = p.prompt[:900]                       # FLUX has no negative prompt
    else:
        steps = min(p.steps, 40)
        cfg = min(p.guidance, 12.0)
        sampler = "k_euler_a"
        text = p.prompt[:800] + (f" ### {p.negative[:150]}" if p.negative else "")

    payload = {
        "prompt": text,
        "params": {
            "sampler_name": sampler,
            "cfg_scale": cfg,
            "width": ww,
            "height": hh,
            "steps": steps,
            "n": n,
        },
        "nsfw": False,
        "censor_nsfw": True,
        "trusted_workers": False,
        "slow_workers": True,
        "r2": True,
    }
    if model:
        payload["models"] = [model]
    if p.ref_image is not None:
        ref = ImageOps.fit(p.ref_image.convert("RGB"), (ww, hh), Image.LANCZOS)
        payload["source_image"] = image_to_b64(ref, "JPEG", 90)
        payload["source_processing"] = "img2img"
        payload["params"]["denoising_strength"] = round(min(max(p.strength, 0.05), 1.0), 2)

    on_status("AI Horde — submitting job to community GPUs…")
    r = requests.post(f"{HORDE_API}/generate/async", json=payload, headers=headers, timeout=60)
    if r.status_code not in (200, 202):
        try:
            msg = r.json().get("message", r.text)
        except Exception:
            msg = r.text
        raise EngineError(f"AI Horde rejected the job (HTTP {r.status_code}): {short(Exception(msg), 160)}")
    job_id = r.json()["id"]

    deadline = time.time() + HORDE_TIMEOUT_S
    errors = 0
    while True:
        try:
            c = requests.get(f"{HORDE_API}/generate/check/{job_id}", headers=headers, timeout=30).json()
            errors = 0
        except Exception:
            errors += 1
            if errors >= 5:
                raise EngineError("Lost connection to AI Horde while waiting")
            time.sleep(3)
            continue

        if c.get("faulted"):
            raise EngineError("AI Horde job faulted")
        if c.get("done"):
            break
        if time.time() > deadline:
            try:
                requests.delete(f"{HORDE_API}/generate/status/{job_id}", headers=headers, timeout=15)
            except Exception:
                pass
            raise EngineError(f"AI Horde queue timed out after {HORDE_TIMEOUT_S}s")

        on_status(
            f"AI Horde queue — position {c.get('queue_position', '?')}, "
            f"ETA ≈ {c.get('wait_time', '?')}s · {c.get('finished', 0)}/{n} finished"
        )
        time.sleep(3)

    status = requests.get(f"{HORDE_API}/generate/status/{job_id}", headers=headers, timeout=30).json()
    results: List[Image.Image] = []
    for g in status.get("generations", []):
        if g.get("censored"):
            continue
        img = g.get("img", "")
        if img.startswith("http"):
            data = requests.get(img, timeout=60).content
        else:
            data = base64.b64decode(img)
        results.append(open_image_bytes(data))
    if not results:
        raise EngineError("AI Horde returned no images")
    return results


# ─────────────────────────────────────────────
# ENGINE ORCHESTRATOR — never blocks on a missing key
# ─────────────────────────────────────────────
def run_generation(
    p: GenParams,
    replicate_token: str,
    hf_token: str,
    pollinations_key: str,
    on_status: StatusFn,
) -> Tuple[List[Image.Image], str, List[str]]:
    attempts: List[Tuple[str, Callable[[], List[Image.Image]]]] = []
    if replicate_token:
        attempts.append(("Replicate · FLUX (premium)", lambda: generate_replicate(p, replicate_token, on_status)))
    if hf_token:
        attempts.append(("Hugging Face · FLUX (premium)", lambda: generate_huggingface(p, hf_token, on_status)))
    if p.ref_image is None:
        attempts.append(("Pollinations · FLUX (free)", lambda: generate_pollinations(p, pollinations_key, on_status)))
    attempts.append(("AI Horde · community GPUs (free)", lambda: generate_horde(p, on_status)))

    warnings: List[str] = []
    for label, fn in attempts:
        try:
            imgs = fn()
            if imgs:
                if label.startswith("Hugging Face") and p.ref_image is not None:
                    warnings.append("Hugging Face image-to-image ignores the strength slider.")
                return imgs, label, warnings
            warnings.append(f"{label}: no images returned")
        except Exception as e:  # noqa: BLE001 — any failure just moves us to the next engine
            warnings.append(f"{label} failed — {short(e)}")
            on_status(f"{label} unavailable, trying next engine…")

    raise EngineError("\n\n".join(warnings))


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="profile-card">
        <div class="profile-avatar">🎨</div>
        <div class="profile-name">Special Pixel Studio</div>
        <div class="profile-role">AI Design Engineer</div>
        <span class="profile-stat">DesignCreationHub</span>
        <span class="profile-stat">v2.1 Pro</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### ⚙️ Engine")
    with st.expander("🔑 Premium keys (optional)", expanded=False):
        st.caption("Leave empty to use the free engines. If a key is present it is used first, "
                   "and the app falls back to free engines if that call fails.")
        user_replicate = st.text_input("Replicate API Token", type="password", placeholder="r8_...")
        user_hf = st.text_input("Hugging Face Token", type="password", placeholder="hf_...")
        user_poll = st.text_input("Pollinations API Key (free)", type="password", placeholder="sk_...")
        st.caption("Replicate: replicate.com/account/api-tokens · HF: huggingface.co/settings/tokens · "
                   "Pollinations: enter.pollinations.ai")

    # Sidebar input wins; otherwise fall back to server-side secrets (never rendered to the browser)
    replicate_token = user_replicate.strip() or get_secret("REPLICATE_API_TOKEN")
    hf_token = user_hf.strip() or get_secret("HF_TOKEN")
    pollinations_key = user_poll.strip() or get_secret("POLLINATIONS_API_KEY")

    if replicate_token:
        engine_txt = "Replicate · FLUX (premium)"
    elif hf_token:
        engine_txt = "Hugging Face · FLUX (premium)"
    else:
        engine_txt = "Free · Pollinations FLUX → AI Horde"
    st.markdown(f'<div class="engine-note">Active engine: <strong>{engine_txt}</strong></div>',
                unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🖼️ Output Settings")
    num_images = st.slider("Variations to generate", 1, 4, 2)

    res_option = st.selectbox("Resolution", list(RESOLUTIONS.keys()))
    out_w, out_h, out_aspect = RESOLUTIONS[res_option]

    inference_steps = st.slider(
        "Inference Steps", 20, 50, 30,
        help="More steps = better quality, slower. Ignored by FLUX schnell / Pollinations.",
    )
    guidance_scale = st.slider(
        "Guidance Scale (CFG)", 1.0, 12.0, 3.5, 0.5,
        help="FLUX works best around 2–5; SDXL around 6–9. Higher = closer to prompt, lower = more creative.",
    )

    st.divider()
    st.markdown("#### 📊 Session Stats")
    st.metric("Images Generated", st.session_state.generation_count)


# ─────────────────────────────────────────────
# SHARED UI HELPERS
# ─────────────────────────────────────────────
def do_generate(p: GenParams, result_key: str, done_msg: str) -> None:
    """Run the engine chain, update session state and show status."""
    status_box = st.empty()

    def on_status(msg: str) -> None:
        status_box.markdown(f'<div class="status-line">⏳ {msg}</div>', unsafe_allow_html=True)

    on_status("Starting…")
    try:
        imgs, engine, warns = run_generation(p, replicate_token, hf_token, pollinations_key, on_status)
    except Exception as e:  # noqa: BLE001
        status_box.empty()
        st.markdown('<span class="status-pill error">✗ All engines failed</span>', unsafe_allow_html=True)
        st.error(str(e))
        st.caption("Free engines are shared and can be busy — try again in a minute, or add a "
                   "Pollinations / Replicate key in the sidebar.")
        return

    status_box.empty()
    st.session_state[result_key] = imgs
    st.session_state.gallery = (imgs + st.session_state.gallery)[:12]
    st.session_state.generation_count += len(imgs)
    st.markdown(f'<span class="status-pill">✓ {done_msg} · {engine}</span>', unsafe_allow_html=True)
    for w in warns:
        st.caption(f"⚠️ {w}")


def render_results(images: list, title: str, label: str, key_prefix: str, file_prefix: str) -> None:
    if not images:
        return
    st.markdown(f"#### {title}")
    cols = st.columns(min(2, len(images)))
    for idx, img in enumerate(images):
        with cols[idx % len(cols)]:
            st.image(img, use_container_width=True, caption=f"{label} {idx + 1}")
            st.download_button(
                f"⬇ Download {idx + 1}",
                data=image_to_bytes(img),
                file_name=f"{file_prefix}_{idx + 1}.png",
                mime="image/png",
                key=f"{key_prefix}_{idx}",
                use_container_width=True,
            )


# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="header-badge">✦ AI STUDIO</div>
    <h1>DesignCreationHub</h1>
    <p>Free FLUX out of the box · Replicate &amp; Hugging Face premium · Prompt Enhancer · Img2Img</p>
</div>
""", unsafe_allow_html=True)

tab_txt2img, tab_img2img, tab_gallery = st.tabs(
    ["✍️  Text → Image", "🔄  Image → Image", "🖼️  Gallery"]
)

# ╔═════════════════════════════════════════════╗
# ║  TAB 1: TEXT TO IMAGE                       ║
# ╚═════════════════════════════════════════════╝
with tab_txt2img:
    col_left, col_right = st.columns([1.1, 0.9], gap="large")

    with col_left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">✦ Prompt Studio</div>', unsafe_allow_html=True)

        user_prompt = st.text_area(
            "Your idea",
            placeholder="e.g. a futuristic Tokyo street at night with cherry blossoms...",
            height=100,
            label_visibility="collapsed",
        )

        style_preset = st.selectbox("Style Preset", list(STYLE_PRESETS.keys()))

        col_cam, col_light = st.columns(2)
        with col_cam:
            camera = st.selectbox("Camera Angle", ["auto"] + CAMERA_ANGLES)
        with col_light:
            lighting = st.selectbox("Lighting", ["auto"] + LIGHTING_STYLES)

        extra_quality = st.multiselect(
            "Extra Quality Tags",
            ["HDR", "RAW photo", "intricate details", "highly detailed", "award-winning",
             "trending on artstation", "unreal engine 5", "depth of field", "bokeh"],
            default=["HDR", "intricate details"],
        )

        auto_enhance = st.checkbox("✨ Auto-enhance prompt (8K detail)", value=True)

        prompt_to_use = user_prompt.strip()
        if user_prompt.strip() and auto_enhance:
            prompt_to_use = enhance_prompt(
                user_prompt,
                STYLE_PRESETS.get(style_preset, ""),
                camera,
                lighting,
                extra_quality,
            )
            st.markdown(
                f'<div class="enhanced-prompt-box">✨ <strong>Enhanced:</strong> {prompt_to_use}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🚫 Negative Prompt Builder</div>', unsafe_allow_html=True)
        selected_negs = st.multiselect(
            "Quick negative blocks",
            list(NEGATIVE_PRESETS.keys()),
            default=["General Quality", "No Distortion"],
        )
        custom_neg = st.text_input(
            "Additional negatives",
            placeholder="cartoon, sketch, low resolution...",
        )
        final_negative = build_negative_prompt(selected_negs, custom_neg)
        if final_negative:
            st.caption(f"📋 Active: `{final_negative[:120]}{'...' if len(final_negative) > 120 else ''}`")
        st.caption("FLUX models don't support negative prompts by design; they are applied on "
                   "SDXL-based engines (e.g. AI Horde SDXL workers).")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("#### 🚀 Generate")
        generate_btn = st.button("Generate Images", key="gen_t2i", use_container_width=True)

        if generate_btn:
            if not user_prompt.strip():
                st.error("⚠️ Please enter a prompt first.")
            else:
                do_generate(
                    GenParams(
                        prompt=prompt_to_use,
                        negative=final_negative,
                        width=out_w,
                        height=out_h,
                        aspect=out_aspect,
                        num_images=num_images,
                        steps=inference_steps,
                        guidance=guidance_scale,
                    ),
                    "results_t2i",
                    "Generation complete",
                )

        render_results(st.session_state.results_t2i, "🖼️ Results", "Variation", "dl_t2i", "design")


# ╔═════════════════════════════════════════════╗
# ║  TAB 2: IMAGE TO IMAGE                      ║
# ╚═════════════════════════════════════════════╝
with tab_img2img:
    col_il, col_ir = st.columns([1.1, 0.9], gap="large")

    with col_il:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📎 Reference Image Upload</div>', unsafe_allow_html=True)

        upload_mode = st.radio(
            "Upload mode",
            ["Single Image", "Grid (2×2 from 4 images)"],
            horizontal=True,
        )

        ref_image: Optional[Image.Image] = None

        if upload_mode == "Single Image":
            uploaded = st.file_uploader("Upload reference image", type=["png", "jpg", "jpeg", "webp"])
            if uploaded:
                ref_image = prepare_reference(Image.open(uploaded))
                st.image(ref_image, caption="Reference Image", use_container_width=True)
        else:
            uploaded_grid = st.file_uploader(
                "Upload up to 4 images for grid reference",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
            )
            if uploaded_grid:
                imgs_grid = [prepare_reference(Image.open(f), 1024) for f in uploaded_grid[:4]]
                size = 512
                grid_img = Image.new("RGB", (size * 2, size * 2), (10, 10, 20))
                positions = [(0, 0), (size, 0), (0, size), (size, size)]
                for gi, pos in zip(imgs_grid, positions):
                    grid_img.paste(ImageOps.fit(gi, (size, size), Image.LANCZOS), pos)
                ref_image = grid_img
                st.image(ref_image, caption="Grid Reference (2×2)", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">✦ Transform Prompt</div>', unsafe_allow_html=True)

        i2i_prompt = st.text_area(
            "How to transform the image",
            placeholder="e.g. convert to cyberpunk style with neon lights and rain...",
            height=90,
            label_visibility="collapsed",
        )
        i2i_style = st.selectbox("Style", list(STYLE_PRESETS.keys()), key="i2i_style")

        img_strength = st.slider(
            "Image Influence (strength)",
            min_value=0.1, max_value=1.0, value=0.65, step=0.05,
            help="Low (0.1-0.4) = stays close to reference. High (0.7-1.0) = heavy prompt influence.",
        )
        if img_strength < 0.35:
            st.caption("🎯 **Conservative** — output closely follows reference")
        elif img_strength < 0.65:
            st.caption("⚖️ **Balanced** — blends reference with prompt")
        else:
            st.caption("💥 **Creative** — prompt dominates, reference as loose guide")

        i2i_negs = st.multiselect(
            "Negative blocks", list(NEGATIVE_PRESETS.keys()),
            default=["General Quality", "No Distortion"], key="i2i_neg",
        )
        i2i_neg_text = build_negative_prompt(i2i_negs, "")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_ir:
        st.markdown("#### 🚀 Transform")
        if not (replicate_token or hf_token):
            st.caption("🆓 Free image-to-image runs on AI Horde community GPUs — it can queue for a minute or two.")
        i2i_btn = st.button("Transform Image", key="gen_i2i", use_container_width=True)

        if i2i_btn:
            if ref_image is None:
                st.error("⚠️ Please upload a reference image.")
            elif not i2i_prompt.strip():
                st.error("⚠️ Please describe how to transform the image.")
            else:
                enhanced_i2i = enhance_prompt(
                    i2i_prompt, STYLE_PRESETS.get(i2i_style, ""), "", "", ["HDR", "ultra-detailed"],
                )
                do_generate(
                    GenParams(
                        prompt=enhanced_i2i,
                        negative=i2i_neg_text,
                        width=out_w,
                        height=out_h,
                        aspect=out_aspect,
                        num_images=num_images,
                        steps=inference_steps,
                        guidance=guidance_scale,
                        ref_image=ref_image,
                        strength=img_strength,
                    ),
                    "results_i2i",
                    "Transformation complete",
                )

        render_results(st.session_state.results_i2i, "🖼️ Transformed Results", "Result", "dl_i2i", "transformed")


# ╔═════════════════════════════════════════════╗
# ║  TAB 3: GALLERY                             ║
# ╚═════════════════════════════════════════════╝
with tab_gallery:
    gallery = st.session_state.gallery
    if not gallery:
        st.info("🎨 Generate some images first — they'll appear here in your session gallery.")
    else:
        st.markdown(f"#### 🖼️ Session Gallery  ·  {len(gallery)} images")
        ncols = min(3, len(gallery))
        gcols = st.columns(ncols)
        for idx, img in enumerate(gallery):
            with gcols[idx % ncols]:
                st.image(img, use_container_width=True)
                st.download_button(
                    "⬇ Download",
                    data=image_to_bytes(img),
                    file_name=f"design_gallery_{idx + 1}.png",
                    mime="image/png",
                    key=f"dl_gallery_{idx}",
                    use_container_width=True,
                )

        if st.button("🗑️ Clear Gallery", use_container_width=False):
            st.session_state.gallery = []
            st.session_state.results_t2i = []
            st.session_state.results_i2i = []
            st.rerun()
