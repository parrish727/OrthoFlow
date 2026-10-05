"""Ceph Suite Phase C — multi-format diagnostic report generator.

Renders a cephalometric diagnostic report from a finalized (or draft) tracing in four formats:
  • PNG  — annotated ceph image (landmarks + polygons) beside a measurement table vs norms
  • PDF  — the same single page saved as PDF (PIL, no extra dependency)
  • JSON — structured machine-readable report (measurements, norms, status, polygons)
  • Medicaid — a submission-oriented text/JSON summary (ties into medicaid_rules HLD framing)

Only PIL is used (already a dependency). Reports are server-generated + trusted, so they are stored
directly in the private documents bucket (no virus scan needed) and recorded as a PatientDocument.
"""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

from app.services import ceph_engine


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


_STATUS_RGB = {"normal": (16, 150, 110), "high": (200, 40, 40), "low": (40, 90, 200), "missing": (150, 150, 150)}


def build_json(tracing: dict, patient_name: str, analysis_name: str) -> dict:
    """Structured report payload (also the basis for Medicaid format)."""
    return {
        "report_type": "cephalometric_analysis",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "patient": patient_name,
        "analysis": {"key": tracing.get("analysis_type"), "name": analysis_name},
        "status": tracing.get("status"),
        "is_ai_assisted": tracing.get("is_ai_assisted", False),
        "calibration": tracing.get("calibration"),
        "measurements": tracing.get("measurements", {}),
        "landmarks": tracing.get("landmarks", {}),
        "disclaimer": "Cephalometric analysis is clinical decision-support reviewed and finalized "
                      "by the treating orthodontist.",
    }


def build_medicaid(tracing: dict, patient_name: str, analysis_name: str) -> dict:
    """Medicaid submission summary — a concise, reviewer-oriented structure. References the HLD /
    medical-necessity framing used by medicaid_rules; the practice attaches this with the claim."""
    m = tracing.get("measurements", {})
    abnormal = {k: v for k, v in m.items() if v.get("status") in ("high", "low")}
    return {
        "document": "Cephalometric Analysis Summary (Medicaid Submission)",
        "patient": patient_name,
        "analysis": analysis_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skeletal_findings": {k: {"value": v.get("value"), "unit": v.get("unit"),
                                   "norm": v.get("norm"), "status": v.get("status")}
                              for k, v in m.items()},
        "notable_deviations": {k: v.get("value") for k, v in abnormal.items()},
        "medical_necessity_note": (
            "Cephalometric measurements supporting the orthodontic treatment plan. Deviations from "
            "population norms documented above; submit alongside the HLD index score and clinical "
            "photographs per payer orthodontic medical-necessity criteria."
        ),
        "clinician_finalized": tracing.get("status") == "finalized",
    }


def render_png(tracing: dict, patient_name: str, analysis_name: str, image_bytes: bytes | None) -> bytes:
    """Render the annotated report page as PNG bytes."""
    W, H = 1400, 1000
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    f_title, f_h, f_b, f_s = _font(30), _font(20), _font(16), _font(13)

    draw.text((30, 24), "Cephalometric Analysis Report", font=f_title, fill=(15, 30, 50))
    draw.text((30, 64), f"{patient_name}   •   {analysis_name}   •   "
                        f"{datetime.now().strftime('%Y-%m-%d')}", font=f_s, fill=(90, 100, 110))
    draw.line((30, 92, W - 30, 92), fill=(220, 225, 230), width=2)

    # Left: annotated image (landmarks + polygons)
    img_box = (30, 110, 760, 940)
    lm = tracing.get("landmarks", {})
    if image_bytes:
        try:
            base = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            bw, bh = base.size
            tw, th = img_box[2] - img_box[0], img_box[3] - img_box[1]
            scale = min(tw / bw, th / bh)
            nw, nh = int(bw * scale), int(bh * scale)
            base = base.resize((nw, nh))
            canvas.paste(base, (img_box[0], img_box[1]))
            # overlay polygons + landmarks in resized/offset coords
            ox, oy = img_box[0], img_box[1]
            polys = ceph_engine.polygons_for(lm)
            for pts in polys.values():
                xy = [(ox + p["x"] * scale, oy + p["y"] * scale) for p in pts]
                if len(xy) >= 2:
                    draw.line(xy, fill=(0, 194, 168), width=2)
            for k, p in lm.items():
                x, y = ox + p["x"] * scale, oy + p["y"] * scale
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(34, 211, 238), outline=(15, 23, 42))
                draw.text((x + 6, y - 14), k, font=f_s, fill=(10, 120, 140))
        except Exception:
            draw.rectangle(img_box, outline=(220, 220, 220))
            draw.text((img_box[0] + 20, img_box[1] + 20), "(image unavailable)", font=f_b, fill=(150, 150, 150))
    else:
        draw.rectangle(img_box, outline=(220, 220, 220))

    # Right: measurement table
    tx = 800
    draw.text((tx, 110), "Measurements", font=f_h, fill=(15, 30, 50))
    draw.text((tx, 140), "Measure", font=f_s, fill=(120, 130, 140))
    draw.text((tx + 300, 140), "Value", font=f_s, fill=(120, 130, 140))
    draw.text((tx + 430, 140), "Norm", font=f_s, fill=(120, 130, 140))
    y = 166
    for k, v in tracing.get("measurements", {}).items():
        val = v.get("value")
        unit = v.get("unit", "")
        us = "°" if unit == "deg" else ("%" if unit == "%" else f" {unit}")
        draw.text((tx, y), v.get("label", k)[:34], font=f_b, fill=(40, 50, 60))
        draw.text((tx + 300, y), (f"{val}{us}" if val is not None else "—"), font=f_b,
                  fill=_STATUS_RGB.get(v.get("status", "missing"), (40, 50, 60)))
        draw.text((tx + 430, y), f"{v.get('norm')}±{v.get('sd')}", font=f_s, fill=(140, 150, 160))
        y += 30
    draw.text((tx, 920), "Clinical decision-support — reviewed by the treating orthodontist.",
              font=f_s, fill=(150, 160, 170))

    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def render_pdf(tracing: dict, patient_name: str, analysis_name: str, image_bytes: bytes | None) -> bytes:
    """Single-page PDF via PIL (PNG → PDF, no extra dependency)."""
    png = render_png(tracing, patient_name, analysis_name, image_bytes)
    page = Image.open(io.BytesIO(png)).convert("RGB")
    out = io.BytesIO()
    page.save(out, format="PDF", resolution=150.0)
    return out.getvalue()


def generate(fmt: str, tracing: dict, patient_name: str, analysis_name: str,
             image_bytes: bytes | None) -> tuple[bytes, str, str]:
    """Return (content_bytes, mime_type, extension) for the requested format."""
    fmt = (fmt or "pdf").lower()
    if fmt == "png":
        return render_png(tracing, patient_name, analysis_name, image_bytes), "image/png", "png"
    if fmt == "json":
        payload = json.dumps(build_json(tracing, patient_name, analysis_name), indent=2).encode()
        return payload, "application/json", "json"
    if fmt == "medicaid":
        payload = json.dumps(build_medicaid(tracing, patient_name, analysis_name), indent=2).encode()
        return payload, "application/json", "medicaid.json"
    # default: pdf
    return render_pdf(tracing, patient_name, analysis_name, image_bytes), "application/pdf", "pdf"
