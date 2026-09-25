# 🎨 DesignCreationHub v6.0
### Professional POD Graphics Studio · Etsy Seller Edition

A production-ready Streamlit application for Print-on-Demand Etsy sellers to generate 
hand-drawn, vintage watercolor, and boutique apparel graphics using a **Triple-Tier AI Engine** 
that guarantees unlimited image generation even with no paid API keys.

---

## ✨ Key Features

### 🔄 Triple-Tier Silent Fallback Engine
| Tier | Provider | Cost | Model |
|------|----------|------|-------|
| **Tier 1** | Replicate | Pay-per-use | FLUX.1-dev / FLUX-Schnell |
| **Tier 2** | Google Gemini | Free quota | Imagen 3.0 |
| **Tier 3** | Pollinations.ai | **Always FREE** | FLUX |

The app automatically falls back through tiers silently — users see a status badge 
showing which provider rendered their image, never a raw error.

### 🎨 4 POD-Optimized Style Presets
- **🌸 Etsy Vintage Watercolor** — Soft botanical illustrations (CFG 4.0)
- **🍂 Cottagecore Fall** — Warm harvest aesthetics (CFG 3.8)
- **👕 Distressed Screenprint** — Vintage tee graphics (CFG 4.5)
- **🌻 Retro 70s Floral** — Groovy botanical vibes (CFG 4.2)

### 🔧 Automatic Prompt Engineering
- **Strips glossy/3D buzzwords**: `8k`, `ultra-detailed`, `sharp focus`, `HDR`, `photorealistic`, `3d render`, etc.
- **Injects tactile modifiers**: watercolor brushstrokes, paper grain, vintage screenprint textures
- **Enforces Single Design Mode**: prevents collages, grids, mockups in output
- **Low CFG enforcement** (3.5–4.5) for soft, painterly results

### 🖼️ Tab 1: Text → Image
- Describe your design in plain English
- Pre-set style examples per preset for quick starts
- Advanced prompt preview with auto-sanitization
- Download as PNG (300dpi) for POD production

### 🔄 Tab 2: Image → Image / Style Transfer
- Upload any reference image or moodboard
- Apply any of the 4 style presets via style transfer
- Image influence slider (0.30–0.70) for creative control
- Before/after comparison view

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)
Edit `.streamlit/secrets.toml`:
```toml
REPLICATE_API_TOKEN = "r8_your_token_here"
GEMINI_API_KEY = "AIzaSy_your_key_here"
```

Or enter keys directly in the app sidebar — **no configuration needed** if you want to use the free Tier 3 engine.

### 3. Run the App
```bash
streamlit run app.py
```

---

## 🔑 Getting Free API Keys

### Replicate (Tier 1) — Highest Quality
1. Go to [replicate.com](https://replicate.com)
2. Sign up for free
3. Visit [Account → API Tokens](https://replicate.com/account/api-tokens)
4. Copy your token (starts with `r8_`)

### Google Gemini (Tier 2) — Free Quota
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Sign in with Google account
3. Click "Get API Key"
4. Copy your key (starts with `AIzaSy`)

> ⚠️ **Important**: Use the **Developer API key** from AI Studio, NOT a Vertex AI service account. The app uses `google-genai` SDK with `imagen-3.0-generate-001` only.

### Pollinations.ai (Tier 3)
**No key required** — always works, completely free.

---

## 📐 Output Formats

| Preset | Dimensions | Use Case |
|--------|-----------|----------|
| 1:1 Square | 1024×1024 | Merch, stickers, universal |
| 4:5 Apparel | 896×1120 | T-shirts, hoodies, totes |
| 3:4 Poster | 768×1024 | Wall art, prints |

All downloads are RGB PNG at 300 DPI, ready for POD platforms (Printify, Printful, Gelato, etc.)

---

## 🏗️ Architecture

```
app.py
├── Prompt Engineering Layer
│   ├── sanitize_prompt()       — strips banned terms
│   ├── build_pod_prompt()      — injects preset modifiers
│   └── SINGLE_DESIGN_NEGATIVES — prevents collage outputs
│
├── Triple-Tier Generation Engine
│   ├── generate_with_replicate()     — Tier 1 (FLUX.1-dev)
│   ├── generate_with_gemini()        — Tier 2 (Imagen 3)
│   ├── generate_with_pollinations()  — Tier 3 (always free)
│   ├── run_triple_tier_generation()  — Text→Image orchestrator
│   └── run_img2img_generation()      — Image→Image orchestrator
│
└── Streamlit UI
    ├── Sidebar (API config, presets, output settings)
    ├── Tab 1: Text → Image
    └── Tab 2: Image → Image / Style Transfer
```

---

## ⚙️ Technical Notes

### Google Gemini Compatibility
This app uses only **Developer API-compatible** functions:
- ✅ `client.models.generate_images` with `imagen-3.0-generate-001`
- ❌ NOT `client.models.edit_image` (Vertex AI Enterprise only)
- ❌ NOT `INPAINT_INSERTION` (Enterprise only)

For Image-to-Image on Gemini, style context is injected directly into the prompt string.

### CFG Scale (Guidance Scale) Philosophy
| Preset | CFG | Effect |
|--------|-----|--------|
| Cottagecore | 3.8 | Very loose, painterly |
| Vintage Watercolor | 4.0 | Soft, organic |
| Retro 70s | 4.2 | Balanced illustration |
| Screenprint | 4.5 | Crisp but not plastic |

Low CFG values (3.5–4.5) are enforced to prevent the "over-rendered plastic" look 
common with high CFG settings in diffusion models.

---

## 📋 Requirements

```
streamlit>=1.35.0
Pillow>=10.3.0
requests>=2.31.0
replicate>=0.25.0
google-genai>=0.8.0
```

---

## 🎯 Designed For

- Etsy POD sellers creating original artwork
- Print-on-Demand designers (Printify, Printful, Gelato, Redbubble)
- Boutique apparel brand owners
- Digital download shop creators

---

*DesignCreationHub v6.0 · Built for Etsy POD Sellers*
