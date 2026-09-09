# LunaAlign AI

A Multi-Modal, Illumination-Invariant Lunar Image Correspondence and Registration System with Uniformly Distributed Sub-Pixel Tie Points.

## Project Overview

LunaAlign AI is a Smart India Hackathon (SIH26166) project sponsored by ISRO. The system addresses the challenge of registering lunar images taken under varying illumination conditions, viewpoints, scales, and sensor modalities.

## Core Concept

The system finds reliable correspondence points between two lunar images despite:
- Illumination variation (different solar azimuth and elevation)
- Viewpoint variation (translation, rotation, perspective distortion)
- Scale variation (different altitudes and spatial resolutions)
- Multi-sensor variation (different visual or spectral characteristics)

And then performs:
- Geometric verification
- Uniform match distribution optimization
- Sub-pixel refinement
- Image registration

## Directory Structure

```
LunaAlign-AI/
    data/
        raw/                 # Original mission data
        processed/           # Processed images
        synthetic/           # Synthetic datasets
        pairs/               # Image pairs
        metadata/            # Metadata files
        splits/              # Train/test splits
    src/
        data/                # Data handling and ingestion
        preprocessing/       # Image preprocessing
        structural_features/ # Illumination-invariant features
        matching/            # Feature detection and matching
        verification/        # Geometric verification
        registration/        # Image registration
        evaluation/          # Evaluation metrics
        visualization/       # Visualization tools
        subpixel/            # Sub-pixel refinement
        spatial_distribution/# Uniform distribution
        transformation/      # Transformation models
        explainability/      # Explainable AI
        utils/               # Utility functions
        reporting/           # Report generation
    frontend/                # Future independent frontend
    backend/                 # FastAPI backend
    models/                  # Trained models
    experiments/             # Experiment tracking
    results/                 # Experiment results
    notebooks/               # Jupyter notebooks
    tests/                   # Unit and integration tests
    docs/                    # Documentation
```

## Getting Started

1. Clone the repository
2. Set up virtual environment: `py -m venv venv`
3. Activate environment: `source venv/Scripts/activate` (Windows) or `source venv/bin/activate` (Unix)
4. Install dependencies: `py -m pip install -r requirements.txt`

## Core Components

- **Scientific Image Ingestion**: Handles IMG, PDS, FITS formats
- **Preprocessing Pipeline**: CLAHE, normalization, multi-scale pyramids
- **Classical Matchers**: SIFT, ORB baselines
- **Deep Learning Matchers**: LoFTR-inspired architectures
- **Illumination Invariance**: Phase congruency, gradient orientation
- **Geometric Verification**: RANSAC, USAC, MAGSAC++
- **Uniform Distribution**: Grid-based adaptive non-maximal suppression
- **Sub-Pixel Refinement**: Gradient-based and correlation refinement
- **Transformation Selection**: Adaptive model selection (affine, homography)
- **Evaluation Framework**: RMSE, reprojection error, distribution metrics
- **Explainable AI**: Match inspection and confidence visualization
- **Web Application**: FastAPI backend with modern frontend compatibility

## Development Approach

The project follows a phased implementation approach:
1. Repository setup and environment configuration
2. Dataset strategy and acquisition
3. Synthetic dataset generation
4. Scientific image handling
5. Metadata management and pair construction
6. Baseline preprocessing
7. Classical feature matching
8. Geometric verification
9. Deep learning correspondence
10. Illumination invariance
11. Multi-scale/multi-modal matching
12. Uniform spatial distribution
13. Sub-pixel refinement
14. Transformation model selection
15. Evaluation and benchmarking
16. Explainability features
17. Interactive visualization dashboard
18. Backend API integration
19. Frontend integration
20. End-to-end system integration
21. Real dataset experiments
22. Performance optimization
23. Testing and edge cases
24. Automated technical reporting
25. SIH demonstration preparation
26. Documentation and polish
27. Knowledge transfer

## License

This project is developed for SIH26166 under ISRO sponsorship.

## Contact

For questions regarding this project, please refer to the SIH26166 documentation.
