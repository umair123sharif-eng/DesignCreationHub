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

# ==============================================================================
# PAGE CONFIGURATION & CUSTOM STYLING
# ==============================================================================
st.set_page_config(
    page_title="DesignCreationHub — FLUX Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #6C5CE7, #a29bfe, #fd79a8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 5px;
    }
    .sub-header {
        font-size: 1rem;
        color: #a0a0a0;
        text-align: center;
        margin-bottom: 25px;
    }
    .stButton>button {
        background: linear-gradient(90deg, #6C5CE7 0%, #fd79a8 100%);
        color: white;
        font-size: 1.1rem;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        padding: 0.65rem 1rem;
        width: 100%;
        box-shadow: 0 4px 15px rgba(108, 92, 231, 0.3);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(108, 92, 231, 0.5);
    }
    .status-line {
        padding: 10px 15px;
        background: #1e1e2e;
        border-radius: 8px;
        border-left: 4px solid #6C5CE7;
        margin-bottom: 15px;
        color: #e0e0e0;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CONSTANTS & PRESETS
# ==============================================================================
REPLICATE_TXT2IMG_MODEL = "black-forest-labs/flux-1.1-pro"
REPLICATE_IMG2IMG_MODEL = "black-forest-labs/flux-dev"
HF_TXT2IMG_MODEL = "black-forest-labs/FLUX.1-schnell"
HF_IMG2IMG_MODEL = "black-forest-labs/FLUX.1-Kontext-dev"

POLLINATIONS_ANON_URL = "https://image.pollinations.ai/prompt/"
POLLINATIONS_KEY_URL = "https://gen.pollinations.ai/image/"
HORDE_API = "https://aihorde.net/api/v2"
HORDE_ANON_KEY = "0000000000"
HORDE_TIMEOUT_S = 35  # Reduced from 300s to avoid long blocking delays

STYLE_PRESETS = {
    "None": "",
    "🎨 Vector / T-Shirt Graphic": "vibrant T-shirt vector graphic sticker design, clean background, sharp outlines, bold typography, 8k sticker",
    "📸 Photorealistic": "photorealistic, hyperrealistic, DSLR photography, sharp focus, 85mm lens, studio lighting",
    "🖼️ Oil Painting": "oil painting, classical art, textured brushstrokes, museum quality",
    "🌆 Cyberpunk": "cyberpunk aesthetic, neon lights, rain-soaked streets, futuristic city",
    "🌿 Studio Ghibli": "Studio Ghibli style, soft watercolor, whimsical, serene, hand-drawn anime",
    "⚡ Anime": "anime style, cel shading, vibrant, detailed illustration",
    "🏺 3D Render": "3D render, octane render, ray tracing, subsurface scattering, blender",
    "✨ Fantasy": "fantasy art, magical, ethereal glow, epic fantasy illustration",
}

NEGATIVE_PRESETS = {
    "General Quality": "blurry, low quality, pixelated, jpeg artifacts, watermark, signature, text",
    "No Humans": "people, human, person, face, hands, body",
    "No Distortion": "distorted, deformed, disfigured, bad anatomy, extra limbs, mutated",
}

CAMERA_ANGLES = ["auto", "eye level", "bird's eye view", "worm's eye view", "close-up", "wide shot", "cinematic perspective"]
LIGHTING_STYLES = ["auto", "golden hour lighting", "studio lighting", "rim lighting", "volumetric light", "cinematic lighting", "neon glow"]

RESOLUTIONS = {
    "1024×1024 (Square)": (1024, 1024, "1:1"),
    "1344×768 (Landscape 16:9)": (1344, 768, "16:9"),
    "768×1344 (Portrait 9:16)": (768, 1344, "9:16"),
    "1280×720 (HD)": (1280, 720, "16:9"),
}

# ==============================================================================
# SESSION STATE & HELPERS
# ==============================================================================
for _k, _v in {"results_t2i": [], "results_i2i": [], "gallery": [], "generation_count": 0}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

class EngineError(RuntimeError): pass

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

def get_secret(name: str) -> str:
    try:
        val = st.secrets.get(name, "")
        if val: return str(val)
    except Exception: pass
    return os.environ.get(name, "")

def enhance_prompt(base_prompt: str, style_preset: str, camera: str, lighting: str, quality_tags: list) -> str:
    parts = [base_prompt.strip().rstrip(",. ")]
    extras = []
    if style_preset: extras.append(style_preset)
    if camera and camera != "auto": extras.append(camera)
    if lighting and lighting != "auto": extras.append(lighting)
    extras.extend(["8K resolution", "ultra-detailed", "sharp focus", "masterpiece", "best quality"])
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
    chunks = [NEGATIVE_PRESETS[k] for k in selected_negatives if k in NEGATIVE_PRESETS]
    if custom_neg.strip(): chunks.append(custom_neg.strip())
    return ", ".join(chunks)

def image_to_bytes(pil_image: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    pil_image.save(buf, format=fmt)
    return buf.getvalue()

def open_image_bytes(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img.convert("RGB")

def prepare_reference(img: Image.Image, max_side: int = 1024) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((max_side, max_side), Image.LANCZOS)
    return img

def short(err: Exception, n: int = 150) -> str:
    msg = " ".join(str(err).split())
    return msg if len(msg) <= n else msg[:n] + "…"

# ==============================================================================
# ENGINE IMPLEMENTATIONS
# ==============================================================================
def generate_replicate(p: GenParams, token: str, on_status: StatusFn) -> List[Image.Image]:
    import replicate
    client = replicate.Client(api_token=token)
    results = []
    for i in range(p.num_images):
        on_status(f"Replicate FLUX — generating image {i + 1}/{p.num_images}")
        if p.ref_image is not None:
            buf = io.BytesIO(image_to_bytes(p.ref_image.convert("RGB"), "JPEG"))
            buf.name = "reference.jpg"
            inputs = {
                "prompt": p.prompt, "image": buf, "prompt_strength": p.strength,
                "aspect_ratio": p.aspect, "num_inference_steps": min(p.steps, 50),
                "guidance": min(p.guidance, 10.0), "output_format": "png"
            }
            model = REPLICATE_IMG2IMG_MODEL
        else:
            inputs = {"prompt": p.prompt, "aspect_ratio": p.aspect, "output_format": "png"}
            model = REPLICATE_TXT2IMG_MODEL

        output = client.run(model, input=inputs)
        items = output if isinstance(output, (list, tuple)) else [output]
        for item in items:
            data = item.read() if hasattr(item, "read") else requests.get(str(item), timeout=90).content
            results.append(open_image_bytes(data))
    return results

def generate_huggingface(p: GenParams, token: str, on_status: StatusFn) -> List[Image.Image]:
    from huggingface_hub import InferenceClient
    client = InferenceClient(api_key=token)
    results = []
    for i in range(p.num_images):
        on_status(f"Hugging Face FLUX — generating image {i + 1}/{p.num_images}")
        if p.ref_image is not None:
            img = client.image_to_image(image_to_bytes(p.ref_image.convert("RGB"), "JPEG"), prompt=p.prompt, model=HF_IMG2IMG_MODEL)
        else:
            img = client.text_to_image(p.prompt, model=HF_TXT2IMG_MODEL, width=p.width, height=p.height)
        results.append(img.convert("RGB"))
    return results

def generate_pollinations(p: GenParams, api_key: str, on_status: StatusFn) -> List[Image.Image]:
    if p.ref_image is not None:
        raise EngineError("Pollinations GET API does not support reference images. Using Horde fallback.")
    
    prompt = p.prompt[:1200]
    if api_key:
        url = POLLINATIONS_KEY_URL + quote(prompt, safe="")
        headers = {"Authorization": f"Bearer {api_key}"}
        base = {"model": "flux"}
    else:
        url = POLLINATIONS_ANON_URL + quote(prompt, safe="")
        headers = {}
        base = {"model": "flux", "nologo": "true"}

    results = []
    for i in range(p.num_images):
        on_status(f"Pollinations FLUX (Instant) — rendering image {i + 1}/{p.num_images}")
        params = {**base, "width": p.width, "height": p.height, "seed": random.randint(1, 2_000_000_000)}
        try:
            r = requests.get(url, params=params, headers=headers, timeout=60)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                results.append(open_image_bytes(r.content))
            else:
                raise EngineError(f"Pollinations returned HTTP {r.status_code}")
        except requests.RequestException as e:
            if results: break
            raise EngineError(f"Pollinations error: {short(e)}")
    return results

def generate_horde(p: GenParams, on_status: StatusFn) -> List[Image.Image]:
    headers = {"apikey": HORDE_ANON_KEY, "Client-Agent": "DesignCreationHub:2.2", "Content-Type": "application/json"}
    ww, hh = min(1024, max(384, int(round(p.width / 64)) * 64)), min(1024, max(384, int(round(p.height / 64)) * 64))
    n = max(1, min(p.num_images, 2))

    payload = {
        "prompt": p.prompt[:800],
        "params": {"sampler_name": "k_euler", "cfg_scale": 3.0, "width": ww, "height": hh, "steps": 20, "n": n},
        "nsfw": False, "censor_nsfw": True, "r2": True
    }
    
    if p.ref_image is not None:
        ref = ImageOps.fit(p.ref_image.convert("RGB"), (ww, hh), Image.LANCZOS)
        buf = io.BytesIO()
        ref.save(buf, format="JPEG", quality=85)
        payload["source_image"] = base64.b64encode(buf.getvalue()).decode("utf-8")
        payload["source_processing"] = "img2img"
        payload["params"]["denoising_strength"] = round(min(max(p.strength, 0.05), 1.0), 2)

    on_status("AI Horde — submitting job...")
    r = requests.post(f"{HORDE_API}/generate/async", json=payload, headers=headers, timeout=30)
    if r.status_code not in (200, 202):
        raise EngineError(f"AI Horde queue busy (HTTP {r.status_code})")
    
    job_id = r.json()["id"]
    deadline = time.time() + HORDE_TIMEOUT_S
    
    while time.time() < deadline:
        try:
            c = requests.get(f"{HORDE_API}/generate/check/{job_id}", headers=headers, timeout=15).json()
            if c.get("done"): break
            on_status(f"AI Horde queue — position {c.get('queue_position', '?')}, ETA ≈ {c.get('wait_time', '?')}s")
            time.sleep(3)
        except Exception:
            time.sleep(3)
    else:
        raise EngineError(f"AI Horde queue timed out ({HORDE_TIMEOUT_S}s limit)")

    status = requests.get(f"{HORDE_API}/generate/status/{job_id}", headers=headers, timeout=20).json()
    results = []
    for g in status.get("generations", []):
        img_data = g.get("img", "")
        if img_data.startswith("http"):
            data = requests.get(img_data, timeout=30).content
        else:
            data = base64.b64decode(img_data)
        results.append(open_image_bytes(data))
    
    if not results: raise EngineError("AI Horde returned no images")
    return results

# ==============================================================================
# ORCHESTRATOR
# ==============================================================================
def run_generation(p: GenParams, replicate_token: str, hf_token: str, pollinations_key: str, on_status: StatusFn):
    attempts = []
    if replicate_token: attempts.append(("Replicate · FLUX (premium)", lambda: generate_replicate(p, replicate_token, on_status)))
    if hf_token: attempts.append(("Hugging Face · FLUX (premium)", lambda: generate_huggingface(p, hf_token, on_status)))
    if p.ref_image is None: attempts.append(("Pollinations · FLUX (free, fast)", lambda: generate_pollinations(p, pollinations_key, on_status)))
    attempts.append(("AI Horde · community GPUs", lambda: generate_horde(p, on_status)))

    warnings = []
    for label, fn in attempts:
        try:
            imgs = fn()
            if imgs: return imgs, label, warnings
        except Exception as e:
            warnings.append(f"{label}: {short(e)}")

    raise EngineError("\n".join(warnings))

# ==============================================================================
# UI LAYOUT
# ==============================================================================
st.markdown("<h1 class='main-header'>DesignCreationHub AI Studio</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Powered by FLUX.1 Engine — Professional High-Res Output</p>", unsafe_allow_html=True)

with st.sidebar:
    st.title("🎨 Studio Engine")
    with st.expander("🔑 Premium Keys (Optional)", expanded=False):
        user_replicate = st.text_input("Replicate Token", type="password", placeholder="r8_...")
        user_hf = st.text_input("Hugging Face Token", type="password", placeholder="hf_...")
        user_poll = st.text_input("Pollinations Key", type="password", placeholder="sk_...")

    replicate_token = user_replicate.strip() or get_secret("REPLICATE_API_TOKEN")
    hf_token = user_hf.strip() or get_secret("HF_TOKEN")
    pollinations_key = user_poll.strip() or get_secret("POLLINATIONS_API_KEY")

    st.markdown("---")
    num_images = st.slider("Variations", 1, 4, 2)
    res_option = st.selectbox("Resolution", list(RESOLUTIONS.keys()))
    out_w, out_h, out_aspect = RESOLUTIONS[res_option]
    inference_steps = st.slider("Inference Steps", 15, 50, 25)
    guidance_scale = st.slider("Guidance Scale (CFG)", 1.0, 12.0, 3.5, 0.5)

tab_txt2img, tab_img2img, tab_gallery = st.tabs(["✍️ Text → Image", "🔄 Image → Image", "🖼️ Gallery"])

def do_generate(p: GenParams, result_key: str, done_msg: str):
    status_box = st.empty()
    def on_status(msg: str): status_box.markdown(f'<div class="status-line">⏳ {msg}</div>', unsafe_allow_html=True)
    
    try:
        imgs, engine, warns = run_generation(p, replicate_token, hf_token, pollinations_key, on_status)
        status_box.empty()
        st.session_state[result_key] = imgs
        st.session_state.gallery = (imgs + st.session_state.gallery)[:12]
        st.session_state.generation_count += len(imgs)
        st.success(f"✅ {done_msg} via {engine}")
    except Exception as e:
        status_box.empty()
        st.error(f"❌ Generation Failed:\n\n{str(e)}")

with tab_txt2img:
    col_l, col_r = st.columns([1.1, 0.9], gap="large")
    with col_l:
        user_prompt = st.text_area("Your Idea / Prompt", placeholder="e.g., Santa Claus wearing sunglasses in pumpkin coat...", height=100)
        style_preset = st.selectbox("Style Preset", list(STYLE_PRESETS.keys()))
        col_c, col_lg = st.columns(2)
        with col_c: camera = st.selectbox("Camera Angle", CAMERA_ANGLES)
        with col_lg: lighting = st.selectbox("Lighting", LIGHTING_STYLES)
        
        auto_enhance = st.checkbox("✨ Auto-Enhance Prompt (8K Quality)", value=True)
        prompt_to_use = enhance_prompt(user_prompt, STYLE_PRESETS.get(style_preset, ""), camera, lighting, []) if (user_prompt and auto_enhance) else user_prompt
        
        if auto_enhance and user_prompt:
            st.caption(f"✨ **Enhanced Prompt:** {prompt_to_use}")

    with col_r:
        if st.button("🚀 Generate Images", key="gen_t2i"):
            if not user_prompt.strip():
                st.error("⚠️ Please enter a prompt first.")
            else:
                do_generate(GenParams(prompt=prompt_to_use, negative="", width=out_w, height=out_h, aspect=out_aspect, num_images=num_images, steps=inference_steps, guidance=guidance_scale), "results_t2i", "Images Rendered")

        if st.session_state.results_t2i:
            cols = st.columns(len(st.session_state.results_t2i))
            for idx, img in enumerate(st.session_state.results_t2i):
                with cols[idx]:
                    st.image(img, use_container_width=True)
                    st.download_button("⬇ Download", data=image_to_bytes(img), file_name=f"design_{idx+1}.png", mime="image/png", key=f"dl_t2i_{idx}")

with tab_img2img:
    col_il, col_ir = st.columns([1.1, 0.9], gap="large")
    with col_il:
        uploaded = st.file_uploader("Upload Reference Image", type=["png", "jpg", "jpeg", "webp"])
        ref_image = prepare_reference(Image.open(uploaded)) if uploaded else None
        if ref_image: st.image(ref_image, caption="Reference Anchor", use_container_width=True)
        
        i2i_prompt = st.text_area("Transform Prompt", placeholder="e.g. Convert into vector sticker graphic style...")
        i2i_style = st.selectbox("Transform Style", list(STYLE_PRESETS.keys()), key="i2i_style")
        img_strength = st.slider("Image Influence", 0.1, 1.0, 0.65, 0.05)

    with col_ir:
        if st.button("🔄 Transform Image", key="gen_i2i"):
            if ref_image is None:
                st.error("⚠️ Please upload a reference image first.")
            elif not i2i_prompt.strip():
                st.error("⚠️ Please describe how to transform the image.")
            else:
                enhanced_i2i = enhance_prompt(i2i_prompt, STYLE_PRESETS.get(i2i_style, ""), "auto", "auto", [])
                do_generate(GenParams(prompt=enhanced_i2i, negative="", width=out_w, height=out_h, aspect=out_aspect, num_images=num_images, steps=inference_steps, guidance=guidance_scale, ref_image=ref_image, strength=img_strength), "results_i2i", "Transform Complete")

        if st.session_state.results_i2i:
            cols = st.columns(len(st.session_state.results_i2i))
            for idx, img in enumerate(st.session_state.results_i2i):
                with cols[idx]:
                    st.image(img, use_container_width=True)
                    st.download_button("⬇ Download", data=image_to_bytes(img), file_name=f"transformed_{idx+1}.png", mime="image/png", key=f"dl_i2i_{idx}")

with tab_gallery:
    if st.session_state.gallery:
        gcols = st.columns(3)
        for idx, img in enumerate(st.session_state.gallery):
            with gcols[idx % 3]:
                st.image(img, use_container_width=True)
