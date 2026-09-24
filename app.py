from __future__ import annotations
import base64
import io
import os
import random
import time
from dataclasses import dataclass
from typing import Callable, List, Optional
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

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"

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

def enhance_prompt(base_prompt: str, style_preset: str, camera: str, lighting: str) -> str:
    parts = [base_prompt.strip().rstrip(",. ")]
    extras = []
    if style_preset: extras.append(style_preset)
    if camera and camera != "auto": extras.append(camera)
    if lighting and lighting != "auto": extras.append(lighting)
    extras.extend(["8K resolution", "ultra-detailed", "sharp focus", "masterpiece", "best quality"])

    seen = set()
    for chunk in extras:
        for tag in (t.strip() for t in chunk.split(",")):
            key = tag.lower()
            if tag and key not in seen:
                seen.add(key)
                parts.append(tag)
    return ", ".join(parts)

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
        img = client.text_to_image(p.prompt, model=HF_TXT2IMG_MODEL, width=p.width, height=p.height)
        results.append(img.convert("RGB"))
    return results

def generate_pollinations(p: GenParams, on_status: StatusFn) -> List[Image.Image]:
    prompt = p.prompt[:1200]
    if p.ref_image is not None:
        prompt = f"reference style composition variation, {prompt}"

    url = POLLINATIONS_URL + quote(prompt, safe="")
    base = {"model": "flux", "nologo": "true"}

    results = []
    for i in range(p.num_images):
        on_status(f"Pollinations FLUX (Instant) — rendering image {i + 1}/{p.num_images}")
        params = {**base, "width": p.width, "height": p.height, "seed": random.randint(1, 2_000_000_000)}
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                results.append(open_image_bytes(r.content))
            else:
                raise EngineError(f"Pollinations HTTP {r.status_code}")
        except requests.RequestException as e:
            if results: break
            raise EngineError(f"Pollinations error: {e}")
    return results

# ==============================================================================
# ORCHESTRATOR
# ==============================================================================
def run_generation(p: GenParams, replicate_token: str, hf_token: str, on_status: StatusFn):
    attempts = []
    if replicate_token: attempts.append(("Replicate · FLUX (premium)", lambda: generate_replicate(p, replicate_token, on_status)))
    if hf_token: attempts.append(("Hugging Face · FLUX (premium)", lambda: generate_huggingface(p, hf_token, on_status)))
    
    # Fast free Pollinations FLUX Engine (Always Active)
    attempts.append(("Pollinations · FLUX (free, instant)", lambda: generate_pollinations(p, on_status)))

    warnings = []
    for label, fn in attempts:
        try:
            imgs = fn()
            if imgs: return imgs, label
        except Exception as e:
            warnings.append(f"{label}: {str(e)}")

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

    replicate_token = user_replicate.strip() or get_secret("REPLICATE_API_TOKEN")
    hf_token = user_hf.strip() or get_secret("HF_TOKEN")

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
        imgs, engine = run_generation(p, replicate_token, hf_token, on_status)
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
        prompt_to_use = enhance_prompt(user_prompt, STYLE_PRESETS.get(style_preset, ""), camera, lighting) if (user_prompt and auto_enhance) else user_prompt
        
        if auto_enhance and user_prompt:
            st.caption(f"✨ **Enhanced Prompt:** {prompt_to_use}")

    with col_r:
        if st.button("🚀 Generate Images", key="gen_t2i"):
            if not user_prompt.strip():
                st.error("⚠️ Please enter a prompt first.")
            else:
                do_generate(GenParams(prompt=prompt_to_use, width=out_w, height=out_h, aspect=out_aspect, num_images=num_images, steps=inference_steps, guidance=guidance_scale), "results_t2i", "Images Rendered")

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

    with col_ir:
        if st.button("🔄 Transform Image", key="gen_i2i"):
            if ref_image is None:
                st.error("⚠️ Please upload a reference image first.")
            elif not i2i_prompt.strip():
                st.error("⚠️ Please describe how to transform the image.")
            else:
                enhanced_i2i = enhance_prompt(i2i_prompt, STYLE_PRESETS.get(i2i_style, ""), "auto", "auto")
                do_generate(GenParams(prompt=enhanced_i2i, width=out_w, height=out_h, aspect=out_aspect, num_images=num_images, steps=inference_steps, guidance=guidance_scale, ref_image=ref_image), "results_i2i", "Transform Complete")

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
