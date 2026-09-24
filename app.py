import streamlit as st
from PIL import Image
import time

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# ==========================================
st.set_page_config(
    page_title="DesignCreationHub - VisionForge Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI styling
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
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #5b4bc4 0%, #8c7ae6 100%);
        transform: translateY(-2px);
    }
    .feature-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #6C5CE7;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SIDEBAR - DEVELOPER PROFILE & SETTINGS
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=90)
    st.title("Developer Profile")
    st.markdown("**AI & ML Engineer**")
    st.caption("✨ *Dream it. Generate it.*")
    
    st.markdown("---")
    st.subheader("⚙️ Generation Engine")
    model_preset = st.selectbox("Select Model Preset", ["SD 1.5 Quality", "SD Turbo Fast", "Flux.1 Dev"])
    inference_steps = st.slider("Inference Steps", 10, 50, 30)
    guidance_scale = st.slider("Guidance Scale (CFG)", 1.0, 20.0, 7.5)
    
    st.markdown("---")
    st.caption("Build with Python, Streamlit & Generative AI")

# ==========================================
# 3. MAIN APP HEADER
# ==========================================
st.markdown("<h1 class='main-header'>DesignCreationHub AI Studio</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Turn your imagination into stunning visuals with Reference-Guided Diffusion</p>", unsafe_allow_html=True)

# ==========================================
# 4. INPUT SECTION (PROMPT & REFERENCE IMAGE)
# ==========================================
col_prompt, col_ref = st.columns([1.2, 0.8], gap="large")

with col_prompt:
    st.subheader("1. Describe Your Vision")
    user_prompt = st.text_area(
        "Enter Image Prompt", 
        height=140,
        placeholder="e.g., A futuristic cyberpunk street at night with glowing neon blue lights, ultra-detailed 8k, cinematic lighting..."
    )
    
    style_preset = st.selectbox(
        "Choose Image Style", 
        ["3D Render", "Photorealistic", "Anime / Concept Art", "Minimalist Vector", "Cyberpunk / Sci-Fi", "Studio Portrait"]
    )
    
    negative_prompt = st.text_input("Negative Prompt (Optional)", placeholder="blurry, low quality, distorted, extra limbs...")

with col_ref:
    st.subheader("2. Reference Image (Optional)")
    st.caption("Upload a single design or multi-design collage to guide color, layout & variations.")
    
    ref_image_file = st.file_uploader(
        "Upload Reference Image", 
        type=["png", "jpg", "jpeg", "webp"],
        help="Optional: Upload an image to extract design elements or generate variations."
    )
    
    ref_strength = 0.65
    if ref_image_file is not None:
        ref_image = Image.open(ref_image_file)
        st.image(ref_image, caption="Uploaded Reference (Single/Multi-Design)", use_column_width=True)
        
        ref_strength = st.slider(
            "Reference Influence (Strength)", 
            min_value=0.1, 
            max_value=1.0, 
            value=0.65, 
            step=0.05,
            help="Higher values keep output closer to reference image. Lower values give more freedom to text prompt."
        )

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. GENERATION & VARIATION ENGINE
# ==========================================
if st.button("🚀 Generate Image / Variations"):
    if not user_prompt and ref_image_file is None:
        st.warning("⚠️ Please enter a prompt OR upload a reference image first.")
    else:
        with st.spinner("🧠 Analyzing inputs, extracting reference features & generating outputs..."):
            time.sleep(2) # Simulating AI pipeline
            
            st.success("✅ Output Generated Successfully!")
            
            # Feature mode details
            if ref_image_file is not None:
                st.info(f"🔄 **Mode**: Reference Analysis & Variation (Influence: {int(ref_strength*100)}%) | **Style**: {style_preset}")
            else:
                st.info(f"🎨 **Mode**: Pure Text-to-Image | **Style**: {style_preset}")
            
            # Display Output Variations
            res_col1, res_col2 = st.columns(2)
            
            with res_col1:
                st.markdown("#### Candidate 1 (Best Match)")
                st.image("https://picsum.photos/600/600?random=10", use_column_width=True)
                st.caption("Score: 9.5/10 | High Feature Alignment")
                
            with res_col2:
                st.markdown("#### Candidate 2 (Creative Variation)")
                st.image("https://picsum.photos/600/600?random=20", use_column_width=True)
                st.caption("Score: 9.1/10 | Prompt Mutated Variation")
