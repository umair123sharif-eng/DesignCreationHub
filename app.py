import streamlit as st
from PIL import Image
import urllib.parse
import random

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="DesignCreationHub - VisionForge Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        color: #6C5CE7;
        text-align: center;
        margin-bottom: 5px;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #888888;
        text-align: center;
        margin-bottom: 30px;
    }
    .stButton>button {
        background: linear-gradient(90deg, #6C5CE7 0%, #a29bfe 100%);
        color: white;
        font-size: 1.1rem;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1rem;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SIDEBAR - DEVELOPER PROFILE
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=90)
    st.title("Developer Profile")
    st.markdown("**AI & ML Engineer**")
    st.caption("✨ *Dream it. Generate it.*")
    st.markdown("---")
    model_choice = st.selectbox("Model Engine", ["Flux / Stable Diffusion", "Turbo Fast", "Cyberpunk / Vector Special"])
    st.markdown("---")
    st.caption("Powered by Real AI Diffusion Pipeline")

# ==========================================
# 3. MAIN APP HEADER
# ==========================================
st.markdown("<h1 class='main-header'>DesignCreationHub AI Studio</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Turn your imagination into stunning visuals with Real AI Diffusion</p>", unsafe_allow_html=True)

# ==========================================
# 4. INPUT SECTION
# ==========================================
col_prompt, col_ref = st.columns([1.2, 0.8], gap="large")

with col_prompt:
    st.subheader("1. Describe Your Vision")
    user_prompt = st.text_area(
        "Enter Image Prompt", 
        height=140,
        placeholder="e.g., Vibrant T-shirt graphic design sticker, Santa Claus wearing sunglasses in pumpkin coat..."
    )
    
    style_preset = st.selectbox(
        "Choose Image Style", 
        ["Vector Graphic / Sticker", "3D Render", "Photorealistic", "Anime / Concept Art", "Cyberpunk / Sci-Fi"]
    )
    
    negative_prompt = st.text_input("Negative Prompt", value="blurry, low quality, distorted, extra limbs, bad anatomy")

with col_ref:
    st.subheader("2. Reference Image (Optional)")
    ref_image_file = st.file_uploader("Upload Reference Image", type=["png", "jpg", "jpeg", "webp"])
    
    if ref_image_file is not None:
        ref_image = Image.open(ref_image_file)
        st.image(ref_image, caption="Uploaded Reference Anchor", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. REAL AI GENERATION LOGIC
# ==========================================
if st.button("🚀 Generate AI Image"):
    if not user_prompt:
        st.warning("⚠️ Please enter a prompt first.")
    else:
        with st.spinner("🎨 AI is creating your image... Please wait a few seconds..."):
            
            # Construct enhanced prompt with style
            full_prompt = f"{user_prompt}, style: {style_preset}, high resolution, masterpiece, detailed"
            encoded_prompt = urllib.parse.quote(full_prompt)
            
            # Generate random seeds for variations
            seed1 = random.randint(1, 99999)
            seed2 = random.randint(1, 99999)
            
            # Real AI API Image Endpoints
            img_url_1 = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&seed={seed1}&nologo=true&model=flux"
            img_url_2 = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=768&seed={seed2}&nologo=true&model=flux"

            st.success("✅ AI Image Generated Successfully!")
            
            res_col1, res_col2 = st.columns(2)
            
            with res_col1:
                st.markdown("#### Candidate 1 (AI Output)")
                st.image(img_url_1, caption=f"Generated Result (Seed: {seed1})", use_container_width=True)
                
            with res_col2:
                st.markdown("#### Candidate 2 (Variation)")
                st.image(img_url_2, caption=f"Generated Result (Seed: {seed2})", use_container_width=True)
