# OrthoFlow — Infrastructure Scaling: Problems to Solve

Running list of infrastructure problems to resolve as OrthoFlow scales. Current infra = self-hosted
Docker on the Mac Pro (16-core, 32GB) + Kind K8s; GHCR → Watchtower deploys; MinIO/Postgres/Redis/
Ollama/ClamAV/LiveKit containers. No cloud (self-hosted per Melanin Tech standards).

---

## 1. GPU inference host for 3D imaging + generative AI  [TABLED — revisit when scaling infra]

**Problem:** Several high-value clinical capabilities need a GPU-backed ML inference service that the
current infrastructure cannot provide. OrthoFlow's code is already wired to call it (dormant); the
gap is purely infrastructure + models, not application code.

**Capabilities blocked on this:**
- **3D CBCT auto-landmarking** — self-hosted 3D CV model (nnU-Net / nnLandmark family) to produce
  3D landmark coordinates from a CBCT volume. OrthoFlow calls it via `CBCT_GEOMETRY_URL` /
  `CBCT_GEOMETRY_ENABLED` (currently dormant → manual 3D landmarks work today).
- **Airway / segmentation analysis** — 3D segmentation model (separate from landmarking).
- **Generative photo-realistic soft-tissue morph** — GAN/diffusion model (the schematic CPU morph
  already ships; generative needs GPU).

**Where the LLM fits (decided — do NOT re-litigate):** the LLM (Claude) is the LANGUAGE/REASONING
layer ONLY — interpretation, report/narrative writing, patient-facing explanation, and 2D-ceph
landmark *suggestion* (Phase B). It does NOT do geometry/landmark-detection/segmentation — those are
specialized CV models. Architecture: `CBCT volume → [3D CV model: geometry, GPU, NO LLM] →
measurements → [Claude Opus: interpretation]`. The LLM is the narrator/advisor, never the measurer.
(`ANTHROPIC_CBCT_MODEL=claude-opus-4-6` already wired for the interpretation layer.)

**Hardware finding (2026-10):** the Mac Pro's **AMD Radeon Pro Vega 56 (8GB) CANNOT be used** — the
3D/generative ML stack needs CUDA (NVIDIA) or Apple-Silicon Metal; AMD needs ROCm which is Linux-only
(not macOS), so a discrete AMD GPU on a Mac has no usable PyTorch backend → CPU fallback, impractical
for 3D volumetric inference. 8GB is also under nnU-Net 3D's typical 11–24GB.

**Options to evaluate when we scale:**
- A dedicated **NVIDIA/Linux GPU box** on-prem (fits the self-hosted model; needs a GPU with enough
  VRAM, e.g. ≥16–24GB) running the model behind an internal inference API.
- A **hosted GPU inference endpoint** (would need to weigh against the self-hosted/no-cloud standard
  + any PHI/BAA implications for sending imaging off-box).

**Also needed alongside the GPU/model:** DICOM/3D libs in the backend image (pydicom / SimpleITK /
numpy — intentionally kept OUT of the lean image until there's a model to use them); a trained or
licensed 3D model + an annotated CBCT dataset (data-acquisition + annotation effort).

**"What type of 3D imaging?" — still to decide (tabled):** the 3D track spans distinct capabilities
with different complexity: (1) 3D volume *viewing/MPR* (browser WebGL, no server GPU), (2) 3D
*cephalometric analysis* (Phase F scaffold — needs the GPU model for auto-landmarking), (3) airway
analysis, (4) intraoral-scan/STL digital setup (different input, not CBCT), (5) 3D facial/photogrammetry
soft-tissue morph. OrthoFlow currently: 2D ceph fully live; 3D CBCT analysis scaffolded (manual
landmarks + Opus interpretation); NO 3D volume viewer / airway / STL / 3D-face yet. Pick the target
capability before investing.

---

## (add future infra problems below as they arise)
