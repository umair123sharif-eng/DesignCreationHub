"""
DesignCreationHub — Production-Ready AI Image Generation Studio
Author: Special Pixel Studio (Sharif)
Features:
  1. Automatic Prompt Enhancer (rich diffusion prompts)
  2. True Image-to-Image with reference upload + strength slider
  3. Professional UI with sidebar, presets, negative prompt builder
  4. Replicate API (FLUX.1) + Hugging Face Inference API integration
"""

import streamlit as st
import replicate
import requests
import base64
import io
import time
import os
from PIL import Image

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
.profile-avatar {
    font-size: 2.5rem;
    margin-bottom: 8px;
}
.profile-name {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    color: #e8eaf0;
    margin-bottom: 4px;
}
.profile-role {
    font-size: 0.78rem;
    color: #6357ff;
    margin-bottom: 10px;
}
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
.stButton > button:hover {
    opacity: 0.88;
}

/* Image gallery cards */
.gallery-img-wrap {
    background: #13161f;
    border: 1px solid #1e2130;
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.2s;
}
.gallery-img-wrap:hover {
    border-color: #6357ff;
}
.gallery-label {
    font-size: 0.78rem;
    color: #5a6076;
    padding: 8px 12px;
    text-align: center;
}

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

/* Status badge */
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

/* Hide Streamlit default elements */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
REPLICATE_FLUX_MODEL = "black-forest-labs/flux-1.1-pro"
REPLICATE_FLUX_IMG2IMG_MODEL = "black-forest-labs/flux-1.1-pro"  # supports img2img via prompt_strength
HF_API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

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

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
for key, val in {
    "generated_images": [],
    "enhanced_prompt": "",
    "generation_count": 0,
    "api_provider": "Replicate",
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─────────────────────────────────────────────
# HELPER: PROMPT ENHANCER
# ─────────────────────────────────────────────
def enhance_prompt(base_prompt: str, style_preset: str, camera: str, lighting: str, quality_tags: list) -> str:
    """Expand a simple prompt into a rich diffusion prompt."""
    parts = [base_prompt.strip()]
    
    if style_preset:
        parts.append(style_preset)
    if camera and camera != "auto":
        parts.append(camera)
    if lighting and lighting != "auto":
        parts.append(lighting)
    
    # Always inject quality enhancers
    base_quality = [
        "8K resolution", "ultra-detailed", "sharp focus",
        "masterpiece", "best quality", "professional"
    ]
    parts.extend(base_quality)
    parts.extend(quality_tags)
    
    return ", ".join(parts)


def build_negative_prompt(selected_negatives: list, custom_neg: str) -> str:
    """Combine selected negative preset chunks with custom text."""
    chunks = [NEGATIVE_PRESETS[k] for k in selected_negatives if k in NEGATIVE_PRESETS]
    if custom_neg.strip():
        chunks.append(custom_neg.strip())
    return ", ".join(chunks)


# ─────────────────────────────────────────────
# HELPER: IMAGE TO BASE64
# ─────────────────────────────────────────────
def image_to_base64_uri(pil_image: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    pil_image.save(buf, format=fmt)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def image_to_bytes_io(pil_image: Image.Image, fmt: str = "PNG") -> io.BytesIO:
    buf = io.BytesIO()
    pil_image.save(buf, format=fmt)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────
# GENERATION: REPLICATE
# ─────────────────────────────────────────────
def generate_replicate(
    api_token: str,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    num_images: int,
    steps: int,
    guidance: float,
    reference_image: Image.Image | None = None,
    img_strength: float = 0.75,
) -> list:
    """Call Replicate FLUX.1-pro for text2img or img2img."""
    os.environ["REPLICATE_API_TOKEN"] = api_token
    client = replicate.Client(api_token=api_token)

    results = []
    for i in range(num_images):
        input_params = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            "num_outputs": 1,
        }
        if negative_prompt:
            input_params["negative_prompt"] = negative_prompt

        if reference_image is not None:
            # Pass as base64 data URI for img2img
            img_uri = image_to_base64_uri(reference_image)
            input_params["image"] = img_uri
            input_params["prompt_strength"] = img_strength  # 0.0=copy img, 1.0=ignore img

        output = client.run(REPLICATE_FLUX_MODEL, input=input_params)
        
        # Replicate returns a list of URLs or FileOutput objects
        for item in output:
            url = str(item)
            resp = requests.get(url, timeout=60)
            img = Image.open(io.BytesIO(resp.content))
            results.append(img)
    return results


# ─────────────────────────────────────────────
# GENERATION: HUGGING FACE
# ─────────────────────────────────────────────
def generate_huggingface(
    api_token: str,
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    num_images: int,
    steps: int,
    guidance: float,
    reference_image: Image.Image | None = None,
    img_strength: float = 0.75,
) -> list:
    """Call HuggingFace Inference API for SDXL."""
    headers = {"Authorization": f"Bearer {api_token}"}
    results = []

    for _ in range(num_images):
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "num_inference_steps": steps,
                "guidance_scale": guidance,
            },
        }
        if reference_image is not None:
            # For img2img, use the img2img HF endpoint
            img_b64 = image_to_base64_uri(reference_image, "JPEG")
            payload["parameters"]["image"] = img_b64
            payload["parameters"]["strength"] = img_strength
            hf_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-refiner-1.0"
        else:
            hf_url = HF_API_URL

        resp = requests.post(hf_url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            img = Image.open(io.BytesIO(resp.content))
            results.append(img)
        elif resp.status_code == 503:
            # Model loading — wait and retry once
            time.sleep(20)
            resp = requests.post(hf_url, headers=headers, json=payload, timeout=120)
            if resp.status_code == 200:
                results.append(Image.open(io.BytesIO(resp.content)))
            else:
                raise RuntimeError(f"HF API error {resp.status_code}: {resp.text}")
        else:
            raise RuntimeError(f"HF API error {resp.status_code}: {resp.text}")

    return results


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    # Developer profile
    st.markdown("""
    <div class="profile-card">
        <div class="profile-avatar">🎨</div>
        <div class="profile-name">Special Pixel Studio</div>
        <div class="profile-role">AI Design Engineer</div>
        <span class="profile-stat">DesignCreationHub</span>
        <span class="profile-stat">v2.0 Pro</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### ⚙️ API Configuration")
    api_provider = st.selectbox(
        "API Provider",
        ["Replicate (FLUX.1 Pro)", "Hugging Face (SDXL)"],
        help="Replicate gives highest quality; HF is free-tier friendly."
    )
    st.session_state.api_provider = api_provider

    if "Replicate" in api_provider:
        api_token = st.text_input("Replicate API Token", type="password", placeholder="r8_...")
        st.caption("Get token: replicate.com/account/api-tokens")
    else:
        api_token = st.text_input("HF Inference Token", type="password", placeholder="hf_...")
        st.caption("Get token: huggingface.co/settings/tokens")

    st.divider()
    st.markdown("#### 🖼️ Output Settings")
    num_images = st.slider("Variations to generate", 1, 4, 2)
    
    res_option = st.selectbox(
        "Resolution",
        ["1024×1024 (Square)", "1344×768 (Landscape 16:9)", "768×1344 (Portrait 9:16)", "1280×720 (HD)"],
    )
    res_map = {
        "1024×1024 (Square)": (1024, 1024),
        "1344×768 (Landscape 16:9)": (1344, 768),
        "768×1344 (Portrait 9:16)": (768, 1344),
        "1280×720 (HD)": (1280, 720),
    }
    out_w, out_h = res_map[res_option]

    inference_steps = st.slider("Inference Steps", 20, 50, 30,
        help="More steps = better quality, slower generation.")
    guidance_scale = st.slider("Guidance Scale (CFG)", 3.0, 15.0, 7.5, 0.5,
        help="Higher = closer to prompt; lower = more creative.")

    st.divider()
    st.markdown("#### 📊 Session Stats")
    st.metric("Images Generated", st.session_state.generation_count)


# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="header-badge">✦ AI STUDIO</div>
    <h1>DesignCreationHub</h1>
    <p>Professional AI image generation — FLUX.1 Pro · SDXL · Prompt Enhancer · Img2Img</p>
</div>
""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────
tab_txt2img, tab_img2img, tab_gallery = st.tabs(
    ["✍️  Text → Image", "🔄  Image → Image", "🖼️  Gallery"]
)

# ╔═════════════════════════════════════════════╗
# ║  TAB 1: TEXT TO IMAGE                       ║
# ╚═════════════════════════════════════════════╝
with tab_txt2img:
    col_left, col_right = st.columns([1.1, 0.9], gap="large")

    with col_left:
        # ── PROMPT SECTION ──
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

        # Auto-enhance preview
        if user_prompt.strip():
            enhanced = enhance_prompt(
                user_prompt,
                STYLE_PRESETS.get(style_preset, ""),
                camera if camera != "auto" else "",
                lighting if lighting != "auto" else "",
                extra_quality,
            )
            st.session_state.enhanced_prompt = enhanced
            st.markdown(
                f'<div class="enhanced-prompt-box">✨ <strong>Enhanced:</strong> {enhanced}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── NEGATIVE PROMPT ──
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
            st.caption(f"📋 Active: `{final_negative[:120]}{'...' if len(final_negative)>120 else ''}`")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("#### 🚀 Generate")
        generate_btn = st.button("Generate Images", key="gen_t2i", use_container_width=True)

        if generate_btn:
            if not user_prompt.strip():
                st.error("⚠️ Please enter a prompt first.")
            elif not api_token:
                st.error("⚠️ API token missing — add it in the sidebar.")
            else:
                with st.spinner("🎨 Generating your designs..."):
                    try:
                        prompt_to_use = st.session_state.enhanced_prompt or user_prompt

                        if "Replicate" in api_provider:
                            imgs = generate_replicate(
                                api_token, prompt_to_use, final_negative,
                                out_w, out_h, num_images, inference_steps, guidance_scale,
                            )
                        else:
                            imgs = generate_huggingface(
                                api_token, prompt_to_use, final_negative,
                                out_w, out_h, num_images, inference_steps, guidance_scale,
                            )

                        st.session_state.generated_images = imgs
                        st.session_state.generation_count += len(imgs)
                        st.markdown('<span class="status-pill">✓ Generation complete</span>', unsafe_allow_html=True)

                    except Exception as e:
                        st.markdown(f'<span class="status-pill error">✗ Error: {str(e)[:80]}</span>', unsafe_allow_html=True)
                        st.exception(e)

        # Results gallery inline
        if st.session_state.generated_images:
            st.markdown("#### 🖼️ Results")
            cols = st.columns(min(2, len(st.session_state.generated_images)))
            for idx, img in enumerate(st.session_state.generated_images):
                with cols[idx % 2]:
                    st.image(img, use_container_width=True, caption=f"Variation {idx+1}")
                    buf = image_to_bytes_io(img)
                    st.download_button(
                        f"⬇ Download V{idx+1}",
                        data=buf,
                        file_name=f"design_{idx+1}.png",
                        mime="image/png",
                        key=f"dl_t2i_{idx}",
                        use_container_width=True,
                    )


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

        ref_image = None

        if upload_mode == "Single Image":
            uploaded = st.file_uploader(
                "Upload reference image", type=["png", "jpg", "jpeg", "webp"]
            )
            if uploaded:
                ref_image = Image.open(uploaded).convert("RGB")
                st.image(ref_image, caption="Reference Image", use_container_width=True)

        else:
            uploaded_grid = st.file_uploader(
                "Upload up to 4 images for grid reference",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
            )
            if uploaded_grid:
                imgs_grid = [Image.open(f).convert("RGB") for f in uploaded_grid[:4]]
                # Build 2×2 composite
                size = 512
                grid_img = Image.new("RGB", (size * 2, size * 2), (10, 10, 20))
                positions = [(0, 0), (size, 0), (0, size), (size, size)]
                for gi, pos in zip(imgs_grid, positions):
                    thumb = gi.resize((size, size), Image.LANCZOS)
                    grid_img.paste(thumb, pos)
                ref_image = grid_img
                st.image(ref_image, caption="Grid Reference (2×2)", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # Prompt for img2img
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
            help="Low (0.1-0.4) = stays close to reference. High (0.7-1.0) = heavy prompt influence."
        )
        
        # Visual indicator
        if img_strength < 0.35:
            st.caption("🎯 **Conservative** — output closely follows reference")
        elif img_strength < 0.65:
            st.caption("⚖️ **Balanced** — blends reference with prompt")
        else:
            st.caption("💥 **Creative** — prompt dominates, reference as loose guide")

        i2i_negs = st.multiselect(
            "Negative blocks", list(NEGATIVE_PRESETS.keys()),
            default=["General Quality", "No Distortion"], key="i2i_neg"
        )
        i2i_neg_text = build_negative_prompt(i2i_negs, "")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_ir:
        st.markdown("#### 🚀 Transform")
        i2i_btn = st.button("Transform Image", key="gen_i2i", use_container_width=True)

        if i2i_btn:
            if ref_image is None:
                st.error("⚠️ Please upload a reference image.")
            elif not i2i_prompt.strip():
                st.error("⚠️ Please describe how to transform the image.")
            elif not api_token:
                st.error("⚠️ API token missing — add it in the sidebar.")
            else:
                enhanced_i2i = enhance_prompt(
                    i2i_prompt,
                    STYLE_PRESETS.get(i2i_style, ""),
                    "", "", ["HDR", "ultra-detailed"],
                )
                with st.spinner("🔄 Transforming image..."):
                    try:
                        if "Replicate" in api_provider:
                            imgs = generate_replicate(
                                api_token, enhanced_i2i, i2i_neg_text,
                                out_w, out_h, num_images, inference_steps, guidance_scale,
                                reference_image=ref_image, img_strength=img_strength,
                            )
                        else:
                            imgs = generate_huggingface(
                                api_token, enhanced_i2i, i2i_neg_text,
                                out_w, out_h, num_images, inference_steps, guidance_scale,
                                reference_image=ref_image, img_strength=img_strength,
                            )

                        st.session_state.generated_images = imgs
                        st.session_state.generation_count += len(imgs)
                        st.markdown('<span class="status-pill">✓ Transformation complete</span>', unsafe_allow_html=True)

                    except Exception as e:
                        st.markdown(f'<span class="status-pill error">✗ {str(e)[:80]}</span>', unsafe_allow_html=True)
                        st.exception(e)

        if st.session_state.generated_images:
            st.markdown("#### 🖼️ Transformed Results")
            cols = st.columns(min(2, len(st.session_state.generated_images)))
            for idx, img in enumerate(st.session_state.generated_images):
                with cols[idx % 2]:
                    st.image(img, use_container_width=True, caption=f"Result {idx+1}")
                    buf = image_to_bytes_io(img)
                    st.download_button(
                        f"⬇ Download {idx+1}",
                        data=buf,
                        file_name=f"transformed_{idx+1}.png",
                        mime="image/png",
                        key=f"dl_i2i_{idx}",
                        use_container_width=True,
                    )


# ╔═════════════════════════════════════════════╗
# ║  TAB 3: GALLERY                             ║
# ╚═════════════════════════════════════════════╝
with tab_gallery:
    if not st.session_state.generated_images:
        st.info("🎨 Generate some images first — they'll appear here in your session gallery.")
    else:
        st.markdown(f"#### 🖼️ Session Gallery  ·  {len(st.session_state.generated_images)} images")
        ncols = min(3, len(st.session_state.generated_images))
        gcols = st.columns(ncols)
        for idx, img in enumerate(st.session_state.generated_images):
            with gcols[idx % ncols]:
                st.image(img, use_container_width=True)
                buf = image_to_bytes_io(img)
                st.download_button(
                    "⬇ Download",
                    data=buf,
                    file_name=f"design_gallery_{idx+1}.png",
                    mime="image/png",
                    key=f"dl_gallery_{idx}",
                    use_container_width=True,
                )

        if st.button("🗑️ Clear Gallery", use_container_width=False):
            st.session_state.generated_images = []
            st.rerun()
