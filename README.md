<![CDATA[<div align="center">

# 🌙 LunaAlign AI

### A Multi-Modal, Illumination-Invariant Lunar Image Correspondence & Registration System with Uniformly Distributed Sub-Pixel Tie Points

**SIH26166 | Sponsored by ISRO | Smart India Hackathon 2026**

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0-5C3EE8?logo=opencv)](https://opencv.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org)
[![Kornia](https://img.shields.io/badge/Kornia-LoFTR-green)](https://kornia.github.io)

</div>

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [What is LunaAlign?](#-what-is-lunaalign)
- [Why This Matters](#-why-this-matters)
- [System Architecture](#-system-architecture)
- [Core Pipeline & Algorithms](#-core-pipeline--algorithms)
  - [1. Image Ingestion & Preprocessing](#1-image-ingestion--preprocessing)
  - [2. Classical Feature Matching (SIFT & ORB)](#2-classical-feature-matching-sift--orb)
  - [3. Illumination-Invariant Structural Features](#3-illumination-invariant-structural-features)
  - [4. Deep Learning Matching (LoFTR)](#4-deep-learning-matching-loftr)
  - [5. Geometric Verification (RANSAC / MAGSAC++)](#5-geometric-verification-ransac--magsac)
  - [6. Uniform Spatial Distribution](#6-uniform-spatial-distribution)
  - [7. Sub-Pixel Refinement](#7-sub-pixel-refinement)
  - [8. Adaptive Transformation Selection](#8-adaptive-transformation-selection)
  - [9. Explainable AI Module](#9-explainable-ai-module)
  - [10. Automated Scientific Reporting](#10-automated-scientific-reporting)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [How It Works (End-to-End Flow)](#-how-it-works-end-to-end-flow)
- [Evaluation & Benchmarking](#-evaluation--benchmarking)
- [Key Technical Decisions](#-key-technical-decisions)
- [Team & License](#-team--license)

---

## 🎯 Problem Statement

> **SIH26166**: *Develop software for co-registration of multi-sensor, multi-temporal Lunar images (such as Chandrayaan-2 TMC-2 and OHRC) with sub-pixel accuracy, producing uniformly distributed tie points even under extreme illumination and viewpoint variation.*

Lunar surface imagery captured by different sensors (e.g., **OHRC at 0.25 m/pixel** vs **TMC-2 at 5 m/pixel**) varies drastically in:

| Challenge | Description |
|-----------|-------------|
| **Illumination** | Different solar azimuth and elevation angles create inverted shadows |
| **Scale** | Up to **20× resolution difference** between sensors |
| **Viewpoint** | Translation, rotation, and perspective distortion |
| **Modality** | Different spectral bands and sensor characteristics |

Traditional image registration algorithms (e.g., standard SIFT) **mathematically shatter** under these extreme conditions. LunaAlign was engineered from the ground up to solve this.

---

## 🚀 What is LunaAlign?

**LunaAlign AI** is a full-stack, multi-algorithm image registration system that:

1. **Ingests** raw satellite imagery (TIFF, PNG, PDS, FITS, IMG formats)
2. **Preprocesses** images using CLAHE normalization and multi-scale pyramids
3. **Extracts** structurally invariant features using both classical (SIFT/ORB) and deep learning (LoFTR) approaches
4. **Matches** features across images with illumination-invariant representations (Phase Congruency, Gradient Orientation, Structural Edge Maps)
5. **Verifies** correspondences geometrically using RANSAC/MAGSAC++ outlier rejection
6. **Distributes** tie points uniformly across the image using grid-based Adaptive Non-Maximal Suppression (ANMS)
7. **Refines** matches to sub-pixel accuracy using gradient-based and Fourier Phase Correlation methods
8. **Registers** images using the optimal transformation model (Affine / Homography)
9. **Explains** every decision with human-readable diagnostic dossiers
10. **Reports** results in auto-generated scientific HTML/PDF documents

---

## 💡 Why This Matters

| Impact Area | Description |
|-------------|-------------|
| **Chandrayaan Missions** | Enables ISRO scientists to precisely overlay OHRC and TMC-2 imagery for geological analysis |
| **Landing Site Selection** | Accurate co-registered maps are critical for identifying safe landing zones for future missions |
| **Lunar Cartography** | Uniformly distributed sub-pixel tie points produce scientifically valid mosaic maps |
| **Resource Mapping** | Precise registration enables multi-spectral mineral and resource identification |
| **Scientific Publications** | Auto-generated reports meet ISRO publication standards |

---

## 🏗 System Architecture

LunaAlign follows a **three-layer decoupled architecture**:

```
┌─────────────────────────────────────────────────────────┐
│                  LAYER 1: PRESENTATION                  │
│              Vite + React + Three.js Dashboard           │
│  ┌──────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ Upload   │  │ Pipeline         │  │ Results      │  │
│  │ Panel    │  │ Visualizer       │  │ Viewer       │  │
│  │ (D&D)    │  │ (Live Telemetry) │  │ (Explainer)  │  │
│  └──────────┘  └──────────────────┘  └──────────────┘  │
│         HTTP fetch (REST)    ▲    WebSocket (Live)       │
└──────────────────────────────┼──────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────┐
│                  LAYER 2: API GATEWAY                   │
│                     FastAPI (Async)                      │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ /upload      │ │ /registration│ │ /results       │  │
│  │ Binary       │ │ Background   │ │ Telemetry &    │  │
│  │ Ingestion    │ │ Task Broker  │ │ Reports        │  │
│  └──────────────┘ └──────────────┘ └────────────────┘  │
│            ConnectionManager (Session UUIDs)             │
└──────────────────────────────┼──────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────┐
│              LAYER 3: MATHEMATICAL PIPELINE              │
│                 OpenCV + PyTorch + Kornia                │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Classical Matching → Geometric Verification →     │  │
│  │  Sub-Pixel Refinement → Model Validation →         │  │
│  │  Explainability → Report Generation                │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🧠 Core Pipeline & Algorithms

### 1. Image Ingestion & Preprocessing

- **Supported Formats**: TIFF, PNG, JPEG, PDS (Planetary Data System), FITS, IMG
- **CLAHE** (Contrast Limited Adaptive Histogram Equalization): Normalizes local contrast without amplifying noise
- **Multi-Scale Gaussian Pyramids**: Constructs resolution hierarchies for scale-robust processing
- **TilingEngine**: For massive satellite imagery (10GB+ TIFFs), slides `1000×1000` blocks with 100px overlap to prevent Out-of-Memory crashes — keeping memory allocation **linear**

### 2. Classical Feature Matching (SIFT & ORB)

| Algorithm | Descriptor Type | Matcher | Complexity | Best For |
|-----------|----------------|---------|------------|----------|
| **SIFT** | Continuous (128-D float) | FLANN KD-Tree | O(N log N) | Scale + rotation invariance |
| **ORB** | Binary (256-bit) | FLANN LSH | O(N log N) | Speed-critical scenarios |

> **Key Optimization**: We deprecated **Brute-Force O(N²) matching** entirely. All continuous descriptors use **KD-Tree FLANN indexers**, and all binary descriptors use **Locality-Sensitive Hashing (LSH)** — achieving a verified **38% speedup**.

- **Lowe's Ratio Test** filters ambiguous matches (threshold: 0.75 for SIFT, 0.8 for ORB)

### 3. Illumination-Invariant Structural Features

Standard SIFT degrades sharply when shadows are inverted between images. We solve this with three structural transformations:

| Transformation | Theory | Effect |
|---------------|--------|--------|
| **Phase Congruency** (Log-Gabor) | Image features exist where Fourier components are maximally in phase — **independent of brightness** | Maintains >50% inlier ratio even on inverted-shadow datasets |
| **Gradient Orientation Histograms** | Gradient *direction* (angle) remains constant regardless of lighting intensity | Robust to contrast changes |
| **Structural Edge Maps** (Canny) | Binary edge masks force detectors to ignore pixel gradients and focus on spatial geometry | Complete illumination invariance |

The `IlluminationInvariantMatcher` acts as a facade: it decomposes raw inputs into invariant maps before passing them to classical matchers.

### 4. Deep Learning Matching (LoFTR)

When classical methods fail (e.g., 20× scale difference between OHRC and TMC-2), we fall back to **LoFTR (Local Feature TRansformer)**:

- **Architecture**: Detector-free matcher using self-attention and cross-attention Transformer layers
- **Implementation**: Kornia's pre-trained `kornia.feature.LoFTR`
- **Why it works**: Computes dense cross-attention probability matrices that operate **independently of local gradient boundaries** — the exact failure mode of SIFT at extreme scales
- **Integration**: LoFTR tensor outputs are mapped back to OpenCV `cv2.KeyPoint` and `cv2.DMatch` objects for seamless downstream compatibility

> **PipelineExhaustionError**: When SIFT shatters (N < 4 matches), our architecture intercepts the failure gracefully and prompts the operator to switch to LoFTR via the React UI.

### 5. Geometric Verification (RANSAC / MAGSAC++)

After matching, we reject outlier correspondences using:

- **RANSAC** (Random Sample Consensus): Iteratively fits geometric models, discarding points that don't conform
- **USAC / MAGSAC++**: Advanced variants with adaptive thresholds for improved robustness
- **Minimum requirement**: 4 point correspondences for homography estimation

### 6. Uniform Spatial Distribution

Raw feature matching produces clustered tie points (e.g., all concentrated in a single crater). ISRO requires **uniformly distributed** points. We implement:

- **Grid-Based Adaptive Non-Maximal Suppression (ANMS)**: Divides the image into a grid and enforces a maximum match density per cell
- Ensures scientifically valid coverage across the entire image

### 7. Sub-Pixel Refinement

Integer-pixel matches are insufficient for ISRO's precision requirements. At 0.25 m/pixel resolution, a **0.5 pixel error = 12.5 cm physical misalignment** on the lunar surface.

Our hybrid **two-pass IterativeRefiner**:

| Pass | Method | Description |
|------|--------|-------------|
| **1. Self-Refinement** | `cv2.cornerSubPix` | Computes spatial gradients around each keypoint to find the most acute corner/edge structure |
| **2. Cross-Refinement** | Fourier Phase Correlation | Executes frequency-domain phase shift comparison between matched patches, identifying fractional translation vectors |

**Result**: Integer coordinates like `(420.0, 115.0)` converge to continuous floating-point targets like `(419.642, 115.201)`.

### 8. Adaptive Transformation Selection

Not all image pairs require the same geometric model. Our `ModelValidationPipeline` iterates through:

1. **Rigid** (rotation + translation)
2. **Affine** (6 DOF — handles shear and non-uniform scale)
3. **Partial-Affine** (subset of affine parameters)
4. **Homography** (8 DOF — handles full perspective distortion)

The pipeline selects the model that minimizes re-projection error while avoiding overfitting.

### 9. Explainable AI Module

Every match decision is auditable through five diagnostic tools:

| Component | Purpose |
|-----------|---------|
| **Match Information Panel** | Exact sub-pixel coordinates, scale ratios, angle differences |
| **Feature Similarity Visualizer** | Side-by-side 4× zoomed patches proving structural correspondence |
| **Geometric Consistency Checker** | Isolated Euclidean error per match (Inlier/Outlier classification) |
| **Refinement Visualizer** | Phase Correlation sub-pixel shift vectors |
| **Uncertainty Visualizer** | 1-Sigma radial heat boundary showing spatial tolerance bounds |

### 10. Automated Scientific Reporting

Every successful registration auto-generates a **base64-encoded, offline-capable scientific HTML report** containing:

- Registration parameters and transformation matrices
- Visual overlays of matched and registered images
- Statistical metrics (RMSE, TRE, inlier ratios)
- Explainability dossiers for selected matches
- Ready for ISRO publication standards

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React + Vite + Three.js | Interactive dashboard, drag-and-drop upload, live pipeline visualization |
| **Backend** | FastAPI + Uvicorn | Async API gateway with WebSocket telemetry |
| **Classical CV** | OpenCV 5.0+ | SIFT, ORB, CLAHE, RANSAC, cornerSubPix, Phase Correlation |
| **Deep Learning** | PyTorch + Kornia | LoFTR Transformer-based feature matching |
| **Scientific** | NumPy, SciPy, Matplotlib | Numerical computation, signal processing, visualization |
| **Testing** | Pytest + httpx | Unit tests, integration tests, edge case validation |
| **Language** | Python 3.12+ (backend), JavaScript (frontend) | Core implementation |

---

## 📂 Project Structure

```
LunaAlign-AI/
├── backend/                     # FastAPI backend server
│   ├── main.py                  # Application entry point & router registration
│   ├── api/endpoints/           # REST & WebSocket route handlers
│   │   ├── upload.py            # Binary image ingestion
│   │   ├── registration.py      # Pipeline execution & WebSocket telemetry
│   │   ├── results.py           # Report retrieval
│   │   └── dem.py               # 3D DEM visualization
│   ├── cache/                   # Runtime image & result storage
│   └── custom_cors.py           # CORS middleware
│
├── frontend/                    # Vite + React application
│   ├── src/
│   │   ├── components/          # React UI components
│   │   ├── services/            # API service layer (apiService.js)
│   │   └── App.jsx              # Root application
│   ├── package.json
│   └── vite.config.js
│
├── src/                         # Core mathematical pipeline
│   ├── preprocessing/           # CLAHE, normalization, multi-scale pyramids
│   ├── structural_features/     # Phase congruency, gradient orientation
│   ├── matching/                # Feature detection & matching engines
│   ├── verification/            # RANSAC, USAC, MAGSAC++ verification
│   ├── registration/            # Image warping & alignment
│   ├── subpixel/                # Sub-pixel refinement (gradient + phase correlation)
│   ├── spatial_distribution/    # Grid-based ANMS for uniform coverage
│   ├── transformation/          # Adaptive model selection
│   ├── explainability/          # Match diagnostic dossiers
│   ├── evaluation/              # RMSE, TRE metric computation
│   ├── visualization/           # Matplotlib-based result plotting
│   ├── reporting/               # Auto-generated HTML/PDF reports
│   └── utils/                   # Shared utilities
│
├── data/                        # Datasets
│   ├── raw/                     # Original mission data
│   ├── processed/               # Preprocessed imagery
│   ├── synthetic/               # Generated test datasets with ground truth
│   ├── pairs/                   # Image pair configurations
│   └── metadata/                # Metadata files
│
├── tests/                       # Test suites
│   ├── edge_cases/              # Scale extremes, illumination inversion
│   └── integration/             # End-to-end pipeline tests
│
├── docs/                        # Technical documentation
│   ├── theoretical_background.md
│   ├── system_architecture.md
│   ├── TALKING_POINTS.md
│   ├── DEMONSTRATION_SCRIPT.md
│   └── ...38 more documents
│
├── demo/                        # SIH demonstration assets
├── notebooks/                   # Jupyter notebooks
├── scripts/                     # Utility scripts
├── archived_experiments/        # Permanent experiment records
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

## ⚡ Getting Started

### Prerequisites

- **Python 3.12+**
- **Node.js 18+** and **npm**
- **Git**

### 1. Clone the Repository

```bash
git clone https://github.com/dhamalavishkar/LunaAlign.git
cd LunaAlign
```

### 2. Backend Setup

```bash
# Create and activate virtual environment
py -3.12 -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run the Application

**Terminal 1 — Backend:**
```bash
py -3.12 -m uvicorn backend.main:app --host 127.0.0.1 --port 8088
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5188
```

### 5. Access the Application

| Service | URL |
|---------|-----|
| **Dashboard** | [http://localhost:5188](http://localhost:5188) |
| **API Docs (Swagger)** | [http://localhost:8088/docs](http://localhost:8088/docs) |
| **Health Check** | [http://localhost:8088/health](http://localhost:8088/health) |

---

## 🔄 How It Works (End-to-End Flow)

```
User drags & drops two lunar images into the React UI
                    │
                    ▼
    ┌───────────────────────────────┐
    │  1. UPLOAD (REST POST)        │  Images → FastAPI → disk cache
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │  2. PREPROCESSING             │  CLAHE → Normalization → Pyramids
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │  3. STRUCTURAL DECOMPOSITION  │  Phase Congruency / Gradient Orient.
    └───────────────┬───────────────┘  (illumination invariance)
                    │
                    ▼
    ┌───────────────────────────────┐
    │  4. FEATURE MATCHING          │  SIFT/ORB (classical)
    │                               │  LoFTR (deep learning fallback)
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │  5. GEOMETRIC VERIFICATION    │  RANSAC/MAGSAC++ outlier rejection
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │  6. UNIFORM DISTRIBUTION      │  Grid-based ANMS filtering
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │  7. SUB-PIXEL REFINEMENT      │  cornerSubPix + Phase Correlation
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │  8. TRANSFORMATION SELECTION  │  Best-fit: Affine or Homography
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │  9. IMAGE REGISTRATION        │  Warp source → align with reference
    └───────────────┬───────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │ 10. EXPLAINABILITY & REPORT   │  Dossiers + HTML scientific report
    └───────────────────────────────┘
                    │
                    ▼
        Results displayed in React UI
       (with live WebSocket telemetry)
```

---

## 📊 Evaluation & Benchmarking

### Core Metrics

| Metric | Description |
|--------|-------------|
| **RMSE** (Root Mean Square Error) | Average point-to-point distance between reference keypoints and re-projected source keypoints via the estimated homography |
| **TRE** (Target Registration Error) | Mean corner disparity between ground truth and predicted homography projections — the ultimate measure of full-image alignment accuracy |
| **Inlier Ratio** | Percentage of matches surviving geometric verification |
| **Execution Time** | Pipeline latency benchmarked across configurations |

### Benchmark Results (Synthetic Dataset)

| Configuration | Inlier Ratio | Notes |
|--------------|-------------|-------|
| SIFT (moderate perspective) | >90% | High precision on standard pairs |
| SIFT (20× scale — OHRC vs TMC-2) | **FAILS** | DoG pyramid smooths craters to flat pixels |
| Phase Congruency + SIFT (inverted shadows) | >50% | Robust without GPU |
| LoFTR (extreme cross-modal) | ✅ Works | Dense attention bypasses gradient limits |

### Automated Testing

```bash
# Run the full test suite
pytest tests/ -v

# Run edge case tests specifically
pytest tests/edge_cases/ -v

# Run integration tests
pytest tests/integration/ -v
```

---

## 🔑 Key Technical Decisions

### 1. Why Not Just Use SIFT for Everything?

SIFT relies on Difference-of-Gaussian (DoG) scale pyramids. When the scale variance between OHRC (0.25m/pixel) and TMC-2 (5m/pixel) hits **20×**, the macroscopic craters become perfectly flat, smoothed-out pixels in the DoG pyramid. SIFT mathematically shatters because there is **no localized gradient left to extract**. We empirically proved this in our Edge-Case Test Suite.

### 2. Why Deprecate Brute-Force Matching?

`cv2.BFMatcher` calculates L2 Norm between every query descriptor against every train descriptor → **O(N²)**. With thousands of structural features from dense OHRC imagery, this created severe latency bottlenecks. KD-Tree FLANN reduces this to **O(N log N)**, and LSH FLANN for binary descriptors (ORB) drops latency by **38%**.

### 3. How Do You Handle 10GB+ Satellite Images?

The custom `TilingEngine` grid-slices massive TIFFs into `1000×1000` sliding blocks with 100px overlap. Memory allocation remains **linear**, preventing Out-of-Memory segmentation faults on edge hardware.

### 4. What Happens When the Pipeline Fails?

The `PipelineExhaustionError` safeguard wraps all mathematical endpoints. If geometry drops below RANSAC requirements (N < 4 matches), the FastAPI backend degrades gracefully and pipes a readable JSON exception directly to the React UI via WebSockets.

---

## 👥 Team & License

This project is developed for **SIH26166** under **ISRO sponsorship** as part of the **Smart India Hackathon 2026**.

**Repository**: [github.com/dhamalavishkar/LunaAlign](https://github.com/dhamalavishkar/LunaAlign)

---

<div align="center">

*Built with 🔬 science and ☕ caffeine for ISRO's lunar exploration program*

</div>
]]>
