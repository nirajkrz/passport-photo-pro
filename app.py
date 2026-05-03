"""
Enhanced Passport Photo Converter — v2
Multi-country · Print sheets · Quality scoring · Buy Me a Coffee
"""
from __future__ import annotations

import io
import time
import uuid
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import streamlit as st
from PIL import Image

# ─────────────────────────────────────────────────────────────
# ⚙️  CONFIG — change these to personalise the app
# ─────────────────────────────────────────────────────────────

BMC_USERNAME   = "yourname"          # buymeacoffee.com/<yourname>
KOFI_USERNAME  = "yourname"          # ko-fi.com/<yourname>
CONTACT_EMAIL  = "you@example.com"
APP_TITLE      = "Passport Photo Pro"
APP_TAGLINE    = "Free · Private · Instant passport & visa photos for 6+ countries"

# ─────────────────────────────────────────────────────────────
# 📐 Photo Specifications
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PhotoSpec:
    name: str
    flag: str
    width_px: int
    height_px: int
    max_bytes: int
    face_ratio: float
    head_top_offset: float
    description: str
    bg_color: str = "White"

SPECS: dict[str, PhotoSpec] = {
    "🇮🇳  Indian Passport (Passport Seva)": PhotoSpec(
        "Indian Passport", "🇮🇳", 630, 810, 250*1024,
        0.50, 0.12, "630×810 px · JPEG < 250 KB · White background",
    ),
    "🇺🇸  US Passport / Visa": PhotoSpec(
        "US Passport", "🇺🇸", 600, 600, 240*1024,
        0.52, 0.12, "600×600 px · JPEG < 240 KB · White/off-white background",
    ),
    "🇬🇧  UK Passport": PhotoSpec(
        "UK Passport", "🇬🇧", 600, 750, 240*1024,
        0.50, 0.12, "600×750 px · JPEG < 240 KB · Cream/white background",
    ),
    "🇪🇺  EU / Schengen Visa": PhotoSpec(
        "EU / Schengen", "🇪🇺", 560, 700, 200*1024,
        0.50, 0.12, "560×700 px · JPEG < 200 KB · White/light background",
    ),
    "🇦🇺  Australian Passport": PhotoSpec(
        "Australian Passport", "🇦🇺", 472, 590, 200*1024,
        0.50, 0.12, "472×590 px · JPEG < 200 KB · White background",
    ),
    "🇨🇦  Canadian Passport": PhotoSpec(
        "Canadian Passport", "🇨🇦", 600, 750, 240*1024,
        0.50, 0.12, "600×750 px · JPEG < 240 KB · White/light-grey background",
    ),
}

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

CACHE_TTL      = 1800
CACHE_MAX      = 24
MIN_DIM        = 300
MAX_PIXELS     = 40_000_000
MAX_UPLOAD_MB  = 30
MAX_ASPECT     = 2.0
MIN_ASPECT     = 0.4
UPLOAD_COOLDOWN = 2
MAX_UPLOADS_HR  = 100

# ─────────────────────────────────────────────────────────────
# 🎨 CSS — premium travel-document aesthetic
# ─────────────────────────────────────────────────────────────

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 860px; }

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #0f2942 0%, #1a4068 55%, #1e5799 100%);
    border-radius: 18px;
    padding: 2.4rem 2.6rem 2rem;
    margin-bottom: 1.6rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}
.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.1rem;
    color: #ffffff;
    margin: 0 0 0.4rem;
    line-height: 1.2;
}
.hero-sub {
    color: #93c5fd;
    font-size: 1rem;
    font-weight: 400;
    margin: 0 0 1.3rem;
}
.hero-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}
.badge {
    background: rgba(255,255,255,0.12);
    color: #e0f2fe;
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 999px;
    padding: 0.22rem 0.85rem;
    font-size: 0.78rem;
    font-weight: 500;
    backdrop-filter: blur(4px);
}

/* ── Country card selector ── */
.country-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.65rem;
    margin: 0.8rem 0 1.2rem;
}
.country-card {
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    padding: 0.75rem 0.9rem;
    cursor: pointer;
    transition: all 0.18s ease;
    text-align: center;
}
.country-card.selected {
    border-color: #1a4068;
    background: #eff6ff;
}
.country-card:hover { border-color: #93c5fd; background: #f0f9ff; }
.country-card .flag { font-size: 1.5rem; }
.country-card .cname { font-size: 0.72rem; font-weight: 600; color: #334155; margin-top: 0.2rem; }
.country-card .cspec { font-size: 0.62rem; color: #94a3b8; }

/* ── Upload zone styling ── */
[data-testid="stFileUploaderDropzone"] {
    border: 2px dashed #cbd5e1 !important;
    border-radius: 14px !important;
    background: #f8fafc !important;
    transition: border-color 0.2s;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #1a4068 !important;
}

/* ── Download button ── */
div[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
    color: #fff !important;
    border: 0 !important;
    font-weight: 700 !important;
    font-size: 1.02rem !important;
    border-radius: 10px !important;
    padding: 0.65rem 1.4rem !important;
    box-shadow: 0 4px 14px rgba(22,163,74,0.35) !important;
    transition: all 0.18s ease !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 18px rgba(22,163,74,0.45) !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.7rem !important;
}
[data-testid="stMetricLabel"] { font-size: 0.72rem !important; color: #64748b !important; }
[data-testid="stMetricValue"] { font-size: 1rem !important; font-weight: 700 !important; }

/* ── Section cards ── */
.section-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.3rem 1.4rem;
    margin: 1rem 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* ── Steps ── */
.steps {
    display: flex;
    gap: 0;
    margin: 1rem 0 0.5rem;
    position: relative;
}
.step {
    flex: 1;
    text-align: center;
    position: relative;
}
.step::after {
    content: '';
    position: absolute;
    top: 19px;
    left: 60%;
    right: -40%;
    height: 2px;
    background: #e2e8f0;
    z-index: 0;
}
.step:last-child::after { display: none; }
.step-dot {
    width: 40px; height: 40px;
    border-radius: 50%;
    background: #1a4068;
    color: #fff;
    display: inline-flex;
    align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.9rem;
    position: relative; z-index: 1;
    margin-bottom: 0.4rem;
}
.step-label { font-size: 0.73rem; font-weight: 600; color: #475569; }

/* ── BMC floating button ── */
.bmc-float {
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 9999;
    animation: bmc-pulse 3s ease-in-out infinite;
}
@keyframes bmc-pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.04); }
}

/* ── BMC inline banner ── */
.bmc-banner {
    background: linear-gradient(135deg, #FFDD00 0%, #FFC200 100%);
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 1rem 0;
    box-shadow: 0 4px 18px rgba(255,194,0,0.3);
    text-decoration: none;
    transition: transform 0.18s, box-shadow 0.18s;
}
.bmc-banner:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(255,194,0,0.4); }
.bmc-coffee { font-size: 2.1rem; }
.bmc-text h4 { margin: 0 0 0.1rem; font-size: 0.95rem; font-weight: 700; color: #1a1a1a; }
.bmc-text p  { margin: 0; font-size: 0.78rem; color: #4a3900; }
.bmc-btn {
    margin-left: auto;
    background: #1a1a1a;
    color: #FFDD00 !important;
    border-radius: 8px;
    padding: 0.45rem 1.1rem;
    font-weight: 700;
    font-size: 0.82rem;
    white-space: nowrap;
    text-decoration: none;
}

/* ── Privacy grid ── */
.privacy-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.8rem;
    margin-top: 0.6rem;
}
.privacy-item {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 0.8rem;
    text-align: center;
    font-size: 0.77rem;
}
.privacy-item .pi-icon { font-size: 1.4rem; margin-bottom: 0.3rem; }
.privacy-item strong { display: block; color: #166534; margin-bottom: 0.15rem; font-size: 0.78rem; }
.privacy-item span { color: #4b7c61; }

/* ── Preview comparison ── */
.compare-label {
    font-size: 0.78rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
}

/* ── Quality row ── */
.q-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 0.5rem;
    margin: 0.6rem 0;
}
.q-item {
    border-radius: 8px;
    padding: 0.55rem 0.4rem;
    text-align: center;
    font-size: 0.7rem;
}
.q-item .q-icon { font-size: 1.1rem; }
.q-item .q-label { color: #64748b; margin-top: 0.15rem; font-weight: 500; }
.q-pass { background: #f0fdf4; border: 1px solid #bbf7d0; }
.q-warn { background: #fefce8; border: 1px solid #fde68a; }
.q-fail { background: #fef2f2; border: 1px solid #fecaca; }

/* ── Footer ── */
.footer {
    margin-top: 2rem;
    padding: 1.2rem;
    text-align: center;
    color: #94a3b8;
    font-size: 0.75rem;
    border-top: 1px solid #e2e8f0;
}
</style>
"""

# ─────────────────────────────────────────────────────────────
# 🖼️  Image processing — robust OpenCV pipeline (no GrabCut)
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FaceBox:
    x: int; y: int; w: int; h: int

def _pil_to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

def _bgr_to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(v, hi))

# ── Face detection ──────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _cascades():
    """Load face + eye cascades once and keep in memory."""
    face_cc = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    # alt cascade catches faces the default misses
    face_alt = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
    )
    eye_cc = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml"
    )
    return face_cc, face_alt, eye_cc

def _detect_faces(bgr: np.ndarray) -> list[FaceBox]:
    """Multi-scale Haar cascade with two classifiers and histogram equalisation."""
    face_cc, face_alt, _ = _cascades()
    h, w = bgr.shape[:2]
    min_dim = max(40, min(w, h) // 8)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)            # boost contrast for dark/flat images

    boxes: list[FaceBox] = []
    for cc in (face_cc, face_alt):
        for g in (gray_eq, gray):               # try enhanced first, raw as fallback
            rects = cc.detectMultiScale(
                g,
                scaleFactor=1.05,               # finer scale steps than default 1.1
                minNeighbors=4,
                minSize=(min_dim, min_dim),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            if len(rects) > 0:
                boxes += [FaceBox(int(x), int(y), int(ww), int(hh))
                          for x, y, ww, hh in rects]
                break                           # no need to try raw if enhanced worked

    if not boxes:
        return []

    # Non-maximum suppression: merge heavily overlapping boxes
    def _iou(a: FaceBox, b: FaceBox) -> float:
        ix1, iy1 = max(a.x, b.x), max(a.y, b.y)
        ix2, iy2 = min(a.x+a.w, b.x+b.w), min(a.y+a.h, b.y+b.h)
        inter = max(0, ix2-ix1) * max(0, iy2-iy1)
        union = a.w*a.h + b.w*b.h - inter
        return inter / union if union > 0 else 0.0

    kept: list[FaceBox] = []
    for fb in sorted(boxes, key=lambda f: f.w*f.h, reverse=True):
        if all(_iou(fb, k) < 0.4 for k in kept):
            kept.append(fb)
    return kept

def _largest_face(bgr: np.ndarray) -> Optional[FaceBox]:
    faces = _detect_faces(bgr)
    return max(faces, key=lambda f: f.w * f.h) if faces else None

# ── Crop ────────────────────────────────────────────────────

def _crop_around_face(img_w: int, img_h: int, f: FaceBox, spec: PhotoSpec) -> tuple[int,int,int,int]:
    """
    Crop so the face (Haar box = forehead→chin) occupies face_ratio of crop height,
    with head_top_offset gap above it. Remaining space below goes to neck + shoulders.

    Example with face_ratio=0.50, head_top_offset=0.12, crop_h=H:
      • gap above hairline  = 0.12 * H
      • face box            = 0.50 * H   ← forehead to chin
      • neck + shoulders    = 0.38 * H   (everything below)
    This matches the classic passport-photo framing.
    """
    aspect = spec.width_px / spec.height_px

    # Total crop height derived from face height and desired face_ratio
    ch = float(f.h) / spec.face_ratio
    cw = ch * aspect

    # Enforce aspect ratio after clamping
    if cw > img_w: cw = float(img_w); ch = cw / aspect
    if ch > img_h: ch = float(img_h); cw = ch * aspect

    # Horizontal: centre crop on face midpoint
    cx   = f.x + f.w / 2.0
    left = _clamp(cx - cw / 2.0, 0.0, img_w - cw)

    # Vertical: place top of crop so there is head_top_offset*ch space
    # above the TOP of the Haar detection box (i.e. above the forehead)
    face_top = float(f.y)
    top = _clamp(face_top - ch * spec.head_top_offset, 0.0, img_h - ch)

    return int(round(left)), int(round(top)), int(round(left + cw)), int(round(top + ch))

def _center_crop(bgr: np.ndarray, aspect: float) -> np.ndarray:
    h, w = bgr.shape[:2]
    if w / h > aspect:
        nw = int(h * aspect); s = (w - nw) // 2
        return bgr[:, s:s + nw]
    nh = int(w / aspect); s = (h - nh) // 2
    return bgr[s:s + nh, :]

# ── Background replacement (flood-fill, NO GrabCut) ─────────

def _sample_bg_color(bgr: np.ndarray, corner_frac: float = 0.04) -> np.ndarray:
    """Sample median color from the four image corners — that is the background."""
    h, w = bgr.shape[:2]
    cs = max(4, int(min(h, w) * corner_frac))
    patches = [
        bgr[:cs, :cs],
        bgr[:cs, w-cs:],
        bgr[h-cs:, :cs],
        bgr[h-cs:, w-cs:],
    ]
    pixels = np.vstack([p.reshape(-1, 3) for p in patches])
    return np.median(pixels, axis=0).astype(np.uint8)   # shape (3,)

def _flood_fill_bg_mask(bgr: np.ndarray, seed_color: np.ndarray,
                        tolerance: int = 28) -> np.ndarray:
    """
    Flood-fill outward from all four corners using seed_color ± tolerance.
    Returns uint8 mask: 255 = background, 0 = foreground.
    Pure colour-distance flood — never touches the face region.
    """
    h, w = bgr.shape[:2]
    # Work in float32 for stable distance comparisons
    img_f   = bgr.astype(np.float32)
    seed_f  = seed_color.astype(np.float32)
    tol_sq  = float(tolerance ** 2)

    # Pre-compute per-pixel squared L2 distance to seed color
    dist_sq = np.sum((img_f - seed_f) ** 2, axis=2)   # shape (h, w)

    # Start mask: corners seed pixels
    visited = np.zeros((h, w), dtype=bool)
    bg_mask = np.zeros((h, w), dtype=bool)

    corner_size = max(3, int(min(h, w) * 0.03))
    seeds: list[tuple[int,int]] = []
    for ry in [range(corner_size), range(h-corner_size, h)]:
        for rx in [range(corner_size), range(w-corner_size, w)]:
            for y in ry:
                for x in rx:
                    if not visited[y, x]:
                        visited[y, x] = True
                        seeds.append((y, x))

    # BFS flood fill
    from collections import deque
    queue = deque()
    for y, x in seeds:
        if dist_sq[y, x] <= tol_sq:
            bg_mask[y, x] = True
            queue.append((y, x))

    dy = (-1, 1,  0, 0)
    dx = ( 0, 0, -1, 1)
    while queue:
        cy, cx = queue.popleft()
        for i in range(4):
            ny, nx = cy + dy[i], cx + dx[i]
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                visited[ny, nx] = True
                if dist_sq[ny, nx] <= tol_sq:
                    bg_mask[ny, nx] = True
                    queue.append((ny, nx))

    return (bg_mask.astype(np.uint8) * 255)

def _refine_mask(raw_mask: np.ndarray, h: int, w: int,
                 face: Optional[FaceBox]) -> np.ndarray:
    """
    Morphologically clean the flood-fill result, then create a soft
    alpha channel for natural compositing. Face region is hard-protected.
    """
    k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    k7 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    k15 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))

    # Fill small gaps that flood-fill missed
    fg_mask = cv2.bitwise_not(raw_mask)              # foreground = 255
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE,  k15)  # close holes
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN,   k3)   # remove noise
    fg_mask = cv2.dilate(fg_mask, k7, iterations=1)              # recover any over-eroded edges

    # Hard-protect face region — never let it become background
    if face is not None:
        pad = int(face.w * 0.15)
        fx1 = max(0, face.x - pad);    fx2 = min(w, face.x + face.w + pad)
        fy1 = max(0, face.y - pad);    fy2 = min(h, face.y + face.h + pad)
        fg_mask[fy1:fy2, fx1:fx2] = 255

    # Soft feathered alpha for smooth edges (avoids hard aliased lines)
    alpha = cv2.GaussianBlur(fg_mask, (21, 21), 0)
    return alpha          # uint8 0-255 soft alpha

def _replace_background(bgr: np.ndarray,
                         face: Optional[FaceBox]) -> tuple[np.ndarray, bool]:
    """
    Replace background with white (252,252,252) using flood-fill + soft compositing.
    No GrabCut — no black patches.
    """
    h, w = bgr.shape[:2]

    seed_color = _sample_bg_color(bgr)
    raw_mask   = _flood_fill_bg_mask(bgr, seed_color, tolerance=30)
    alpha      = _refine_mask(raw_mask, h, w, face)

    fg_coverage = float(np.count_nonzero(alpha > 127)) / (h * w)
    if fg_coverage < 0.10:
        # Mask looks wrong (almost nothing foreground) — return original untouched
        return bgr, False

    a   = alpha.astype(np.float32)[:, :, None] / 255.0
    white = np.full_like(bgr, 252, dtype=np.float32)
    result = (bgr.astype(np.float32) * a + white * (1.0 - a))
    return np.clip(result, 0, 255).astype(np.uint8), True

# ── Lighting enhancement ────────────────────────────────────

def _fix_lighting(bgr: np.ndarray) -> np.ndarray:
    """
    Gentle CLAHE in LAB L-channel + optional gamma lift for dark images.
    clipLimit=1.5 keeps it subtle — no halos or over-sharpening.
    """
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    l_eq  = clahe.apply(l)

    # Blend: 55 % enhanced + 45 % original to stay natural
    l_blend = cv2.addWeighted(l_eq, 0.55, l, 0.45, 0)

    mean_l = float(np.mean(l_blend))

    # Gentle gamma lift only if noticeably dark
    if mean_l < 105:
        gamma  = 0.82                          # < 1 brightens
        lut    = np.array([
            min(255, int((i / 255.0) ** gamma * 255))
            for i in range(256)
        ], dtype=np.uint8)
        l_blend = cv2.LUT(l_blend, lut)

    # Slight highlight recovery for over-exposed images
    elif mean_l > 210:
        lut = np.array([
            min(255, int((i / 255.0) ** 1.10 * 255))
            for i in range(256)
        ], dtype=np.uint8)
        l_blend = cv2.LUT(l_blend, lut)

    merged = cv2.merge([l_blend, a, b])
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

# ── Red-eye removal ─────────────────────────────────────────

def _remove_red_eyes(bgr: np.ndarray, face: Optional[FaceBox]) -> np.ndarray:
    """
    Two-stage red-eye fix:
    1. Use the eye cascade to find exact eye locations (precise).
    2. Fall back to heuristic eye-band scan if cascade finds nothing.
    Only modifies pixels where red channel dominates substantially.
    """
    if face is None:
        return bgr

    _, _, eye_cc = _cascades()
    out = bgr.copy()
    h_img, w_img = bgr.shape[:2]

    # Restrict search to upper half of face box
    ey1 = max(0, face.y + int(face.h * 0.10))
    ey2 = max(ey1 + 1, min(h_img, face.y + int(face.h * 0.60)))
    ex1 = max(0, face.x)
    ex2 = min(w_img, face.x + face.w)

    face_roi_gray = cv2.cvtColor(out[ey1:ey2, ex1:ex2], cv2.COLOR_BGR2GRAY)
    eye_rects = eye_cc.detectMultiScale(
        face_roi_gray, scaleFactor=1.1, minNeighbors=3,
        minSize=(max(8, face.w//8), max(8, face.h//8)),
    )

    def _fix_roi(roi_bgr: np.ndarray) -> np.ndarray:
        """Desaturate red-dominant pixels in a small eye ROI."""
        roi = roi_bgr.astype(np.float32)
        b_c, g_c, r_c = roi[:,:,0], roi[:,:,1], roi[:,:,2]
        avg_bg  = (b_c + g_c) / 2.0
        # Strict mask: red > 120, red > 2× average of other channels
        mask    = (r_c > 120) & (r_c > avg_bg * 2.0)
        if mask.any():
            # Replace with luminance-preserving grey (natural dark pupil)
            grey          = np.clip(avg_bg * 0.50, 0, 255)
            roi[:,:,2][mask] = grey[mask]          # red  → dark
            roi[:,:,1][mask] = grey[mask] * 0.95   # green → slightly dark
            roi[:,:,0][mask] = grey[mask] * 0.95   # blue  → slightly dark
        return np.clip(roi, 0, 255).astype(np.uint8)

    if len(eye_rects) > 0:
        # Cascade found eyes — fix each one precisely
        for (ex, ey, ew, eh) in eye_rects:
            abs_x1 = ex1 + ex;  abs_x2 = abs_x1 + ew
            abs_y1 = ey1 + ey;  abs_y2 = abs_y1 + eh
            out[abs_y1:abs_y2, abs_x1:abs_x2] =                 _fix_roi(out[abs_y1:abs_y2, abs_x1:abs_x2])
    else:
        # Fallback: fix the entire heuristic eye band
        out[ey1:ey2, ex1:ex2] = _fix_roi(out[ey1:ey2, ex1:ex2])

    return out

# ── Quality scoring ─────────────────────────────────────────

def _quality_score(bgr: np.ndarray, face: Optional[FaceBox], n_faces: int) -> list[dict]:
    h, w = bgr.shape[:2]
    gray   = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mean_b = float(np.mean(gray))
    lap    = cv2.Laplacian(gray, cv2.CV_64F).var()

    def _q(label, icon, ok, note):
        return {"label": label, "icon": icon, "ok": ok, "note": note,
                "cls": "q-pass" if ok else "q-fail"}

    # Red-eye pre-check (before correction)
    red_eye_detected = False
    if face is not None:
        ey1 = max(0, face.y + int(face.h * 0.10))
        ey2 = min(h, face.y + int(face.h * 0.60))
        ex1 = max(0, face.x); ex2 = min(w, face.x + face.w)
        if ey2 > ey1 and ex2 > ex1:
            roi  = bgr[ey1:ey2, ex1:ex2].astype(np.float32)
            r_c  = roi[:,:,2]
            avg  = (roi[:,:,0] + roi[:,:,1]) / 2.0
            pct  = float(np.mean((r_c > 120) & (r_c > avg * 2.0)))
            red_eye_detected = pct > 0.02

    bright_ok = 80 <= mean_b <= 210
    sharp_ok  = lap > 80

    items = [
        _q("Brightness",
           "☀️" if bright_ok else ("🌑" if mean_b < 80 else "💡"),
           bright_ok,
           "Good" if bright_ok else ("Too dark" if mean_b < 80 else "Too bright")),
        _q("Sharpness",
           "🔍" if sharp_ok else "🌫️",
           sharp_ok,
           "Sharp" if sharp_ok else "Blurry"),
        _q("Face",
           "🧑" if n_faces == 1 else ("❓" if n_faces == 0 else "👥"),
           n_faces == 1,
           "Detected" if n_faces == 1 else ("None found" if n_faces == 0 else f"{n_faces} faces")),
        _q("Face size",
           "✅" if (face and face.w * face.h / (w * h) >= 0.04) else "⚠️",
           bool(face and face.w * face.h / (w * h) >= 0.04),
           "Good" if (face and face.w * face.h / (w * h) >= 0.04) else "Too small"),
        _q("Resolution",
           "📐" if (w >= MIN_DIM and h >= MIN_DIM) else "📉",
           w >= MIN_DIM and h >= MIN_DIM,
           "Good" if (w >= MIN_DIM and h >= MIN_DIM) else "Low res"),
        _q("Red eyes",
           "🔴" if red_eye_detected else "👁️",
           not red_eye_detected,
           "Fixed ✓" if red_eye_detected else "None"),
        _q("Lighting",
           "✨" if bright_ok and sharp_ok else "🔦",
           bright_ok and sharp_ok,
           "Good" if bright_ok and sharp_ok else "Auto-enhanced"),
    ]
    return items

# ── Master pipeline ─────────────────────────────────────────

def _build_passport(img: Image.Image, spec: PhotoSpec):
    bgr       = _pil_to_bgr(img)
    all_faces = _detect_faces(bgr)
    face      = max(all_faces, key=lambda f: f.w * f.h) if all_faces else None
    quality   = _quality_score(bgr, face, len(all_faces))
    aspect    = spec.width_px / spec.height_px

    # 1 ── Red-eye removal (use original face coords before crop)
    bgr = _remove_red_eyes(bgr, face)

    # 2 ── Tight face-centred crop (or centre crop if no face)
    if face:
        l, t, r, b = _crop_around_face(bgr.shape[1], bgr.shape[0], face, spec)
        bgr = bgr[t:b, l:r]
    else:
        bgr = _center_crop(bgr, aspect)

    # 3 ── Lighting enhancement (CLAHE + optional gamma)
    bgr = _fix_lighting(bgr)

    # 4 ── Background replacement (flood-fill, NO GrabCut)
    face_after_crop = _largest_face(bgr)          # re-detect in cropped frame
    bgr, bg_ok = _replace_background(bgr, face_after_crop)

    # 5 ── Final resize to exact spec dimensions
    bgr = cv2.resize(bgr, (spec.width_px, spec.height_px),
                     interpolation=cv2.INTER_LANCZOS4)

    return _bgr_to_pil(bgr), face is not None, bg_ok, quality

def _encode_jpeg(img: Image.Image, limit: int) -> tuple[bytes, int]:
    rgb = img.convert("RGB"); rgb.info.clear()
    for q in range(95, 24, -5):
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=q, optimize=True, exif=b"")
        if len(buf.getvalue()) <= limit:
            return buf.getvalue(), q
    buf = io.BytesIO()
    rgb.save(buf, format="JPEG", quality=25, optimize=True, exif=b"")
    return buf.getvalue(), 25

def _normalize(raw: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA","LA") or (img.mode=="P" and "transparency" in img.info):
        bg = Image.new("RGBA", img.size, (255,255,255,255))
        return Image.alpha_composite(bg, img.convert("RGBA")).convert("RGB")
    return img.convert("RGB")

@st.cache_data(show_spinner=False, ttl=CACHE_TTL, max_entries=CACHE_MAX)
def _process(raw: bytes, spec_name: str):
    spec = SPECS[spec_name]
    result, face_ok, bg_ok, quality = _build_passport(_normalize(raw), spec)
    encoded, q = _encode_jpeg(result, spec.max_bytes)
    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=88, optimize=True)
    return encoded, q, face_ok, bg_ok, buf.getvalue(), quality

def _adjust(img: Image.Image, br, ct, zm, bg_pct) -> Image.Image:
    arr = np.array(img, dtype=np.float32)
    if br: arr = np.clip(arr + br, 0, 255)
    if ct:
        f = (100 + ct) / 100.0
        arr = np.clip(128 + f * (arr - 128), 0, 255)
    out = Image.fromarray(arr.astype(np.uint8))
    if zm != 100:
        w, h = out.size; s = zm/100
        nw, nh = int(w*s), int(h*s)
        r = out.resize((nw, nh), Image.LANCZOS)
        lx, ly = (nw-w)//2, (nh-h)//2
        out = r.crop((lx, ly, lx+w, ly+h))
    if bg_pct < 100:
        a = np.array(out, dtype=np.float32)
        m = np.all(a > 240, axis=2)
        a[m] = a[m]*(bg_pct/100) + 252*(1-bg_pct/100)
        out = Image.fromarray(a.astype(np.uint8))
    return out

def _make_print_sheet(photo_bytes: bytes, spec: PhotoSpec, layout: str) -> bytes:
    SHEET_W, SHEET_H = 1800, 1200
    MARGIN = 30; GAP = 16
    cols, rows = {"2×2": (2,2), "3×2": (3,2), "4×2": (4,2)}[layout]
    photo = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    sheet = Image.new("RGB", (SHEET_W, SHEET_H), (228, 228, 228))
    avail_w = SHEET_W - 2*MARGIN - (cols-1)*GAP
    avail_h = SHEET_H - 2*MARGIN - (rows-1)*GAP
    cw, ch  = avail_w//cols, avail_h//rows
    ph_asp  = spec.width_px / spec.height_px
    if ph_asp > cw/ch: pw, ph = cw, int(cw/ph_asp)
    else: ph, pw = ch, int(ch*ph_asp)
    thumb = photo.resize((pw, ph), Image.LANCZOS)
    bordered = Image.new("RGB", (pw+2, ph+2), (160,160,160))
    bordered.paste(thumb, (1,1))
    for r in range(rows):
        for c in range(cols):
            x = MARGIN + c*(cw+GAP) + (cw-pw)//2
            y = MARGIN + r*(ch+GAP) + (ch-ph)//2
            sheet.paste(bordered, (x, y))
    buf = io.BytesIO()
    sheet.save(buf, format="JPEG", quality=95, optimize=True)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────
# Validation & rate limiting
# ─────────────────────────────────────────────────────────────

def _validate(raw: bytes) -> tuple[bool, str]:
    if len(raw) > MAX_UPLOAD_MB * 1024 * 1024:
        return False, f"File must be under {MAX_UPLOAD_MB} MB."
    try:
        with Image.open(io.BytesIO(raw)) as img: img.verify()
    except Exception:
        return False, "Not a valid image file."
    img = Image.open(io.BytesIO(raw))
    w, h = img.size
    if (img.format or "").upper() not in {"JPEG","PNG"}:
        return False, "Only JPG/JPEG and PNG files are accepted."
    if w < MIN_DIM or h < MIN_DIM:
        return False, f"Image must be at least {MIN_DIM}×{MIN_DIM} px."
    if w * h > MAX_PIXELS:
        return False, "Resolution too high (max 40 MP)."
    if w/h > MAX_ASPECT: return False, "Landscape photos not supported. Use a portrait."
    if w/h < MIN_ASPECT: return False, "Image too narrow. Upload a standard portrait."
    return True, ""

def _rate_ok(action, cooldown, max_hr) -> tuple[bool, str]:
    now = time.time()
    s = st.session_state.setdefault(f"rl_{action}", {"ts": 0.0, "ev": []})
    s["ev"] = [t for t in s["ev"] if now - t < 3600]
    if now - s["ts"] < cooldown:
        return False, f"Please wait {int(cooldown-(now-s['ts']))+1}s."
    if len(s["ev"]) >= max_hr:
        return False, "Rate limit reached. Try again later."
    s["ts"] = now; s["ev"].append(now)
    return True, ""

def _sid() -> str:
    if "sid" not in st.session_state:
        st.session_state["sid"] = str(uuid.uuid4())
    return st.session_state["sid"]

# ─────────────────────────────────────────────────────────────
# 🧩 UI components
# ─────────────────────────────────────────────────────────────

def _bmc_url() -> str:
    return f"https://www.buymeacoffee.com/{BMC_USERNAME}"

def _render_hero() -> None:
    st.markdown(f"""
    <div class="hero">
        <div class="hero-title">📷 {APP_TITLE}</div>
        <div class="hero-sub">{APP_TAGLINE}</div>
        <div class="hero-badges">
            <span class="badge">🌍 6 Countries</span>
            <span class="badge">⚡ Instant Processing</span>
            <span class="badge">🔒 100% Private</span>
            <span class="badge">🖨️ Print-Ready Sheets</span>
            <span class="badge">✅ Spec-Compliant Output</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def _render_steps() -> None:
    st.markdown("""
    <div class="steps">
        <div class="step"><div class="step-dot">1</div><div class="step-label">Select Country</div></div>
        <div class="step"><div class="step-dot">2</div><div class="step-label">Upload Photo</div></div>
        <div class="step"><div class="step-dot">3</div><div class="step-label">Auto-Process</div></div>
        <div class="step"><div class="step-dot">4</div><div class="step-label">Download</div></div>
    </div>
    """, unsafe_allow_html=True)

def _render_bmc_banner() -> None:
    st.markdown(f"""
    <a href="{_bmc_url()}" target="_blank" class="bmc-banner">
        <div class="bmc-coffee">☕</div>
        <div class="bmc-text">
            <h4>This tool is free — but coffee helps!</h4>
            <p>If this saved you time or a trip to the photo studio, consider buying me a coffee.</p>
        </div>
        <span class="bmc-btn">Buy me a coffee →</span>
    </a>
    """, unsafe_allow_html=True)

def _render_bmc_float() -> None:
    st.markdown(f"""
    <div class="bmc-float">
        <a href="{_bmc_url()}" target="_blank">
            <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
                 alt="Buy Me A Coffee"
                 style="height:50px;width:180px;border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,0.18);">
        </a>
    </div>
    """, unsafe_allow_html=True)

def _render_quality(items: list[dict]) -> None:
    st.markdown('<div class="q-grid">' + "".join(
        f'<div class="q-item {i["cls"]}"><div class="q-icon">{i["icon"]}</div>'
        f'<div class="q-label">{i["label"]}</div>'
        f'<div style="font-weight:600;font-size:0.68rem;margin-top:0.1rem">{i["note"]}</div></div>'
        for i in items
    ) + "</div>", unsafe_allow_html=True)

def _render_privacy() -> None:
    st.markdown("""
    <div class="privacy-grid">
        <div class="privacy-item"><div class="pi-icon">🚫</div><strong>No Storage</strong><span>Never saved to disk</span></div>
        <div class="privacy-item"><div class="pi-icon">🔒</div><strong>In-Memory Only</strong><span>Ephemeral processing</span></div>
        <div class="privacy-item"><div class="pi-icon">🙅</div><strong>No Account</strong><span>Zero sign-up</span></div>
        <div class="privacy-item"><div class="pi-icon">💚</div><strong>100% Free</strong><span>No hidden charges</span></div>
    </div>
    """, unsafe_allow_html=True)

def _render_footer() -> None:
    st.markdown(f"""
    <div class="footer">
        © 2026 {APP_TITLE} &nbsp;·&nbsp;
        <a href="{_bmc_url()}" target="_blank" style="color:#d97706">☕ Support this project</a>
        &nbsp;·&nbsp;
        <a href="mailto:{CONTACT_EMAIL}" style="color:#64748b">{CONTACT_EMAIL}</a>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 🚀 Main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📷",
        layout="centered",
    )
    st.markdown(CSS, unsafe_allow_html=True)
    _render_bmc_float()
    st.session_state.setdefault("nonce", 0)

    if st.session_state.pop("downloaded", False):
        st.toast("✅ Photo downloaded successfully!")
        st.session_state["nonce"] += 1

    # ── Hero + steps ──────────────────────────────────────────
    _render_hero()
    _render_steps()

    # ── Country selector ──────────────────────────────────────
    st.markdown("### Step 1 — Choose your document type")
    spec_name = st.selectbox(
        "Document type",
        list(SPECS.keys()),
        label_visibility="collapsed",
        key="spec_select",
    )
    spec = SPECS[spec_name]
    st.markdown(
        f"<div style='background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;"
        f"padding:0.5rem 0.85rem;font-size:0.82rem;color:#1d4ed8;margin-bottom:0.5rem'>"
        f"📐 Output: <strong>{spec.description}</strong></div>",
        unsafe_allow_html=True,
    )

    # ── Checklist ─────────────────────────────────────────────
    with st.expander("📋 Photo checklist — expand before uploading"):
        st.markdown(
            "- **Face centered**, looking straight at the camera  \n"
            "- **Plain background** (white or light — app auto-whitens)  \n"
            "- **Good lighting** — no shadows on face or wall  \n"
            "- **No glasses**, hats, or head coverings (unless religious)  \n"
            "- **Neutral expression**, mouth closed  \n"
            "- **Head & shoulders** clearly visible"
        )

    # ── Upload ────────────────────────────────────────────────
    st.markdown("### Step 2 — Upload your photo")
    uploaded = st.file_uploader(
        "Drag & drop or click to browse",
        type=["jpg", "jpeg", "png"],
        key=f"uploader_{st.session_state['nonce']}",
        help=f"Max {MAX_UPLOAD_MB} MB · JPG or PNG · Portrait orientation",
    )
    st.caption("🔒 Your photo is processed in memory and never stored.")

    # ── BMC banner (shown when no photo yet) ──────────────────
    if not uploaded:
        st.markdown("---")
        _render_bmc_banner()

        with st.expander("❓ Frequently asked questions"):
            st.markdown("""
**Will my photo definitely be accepted?**  
This tool ensures correct dimensions and file size. Final acceptance also depends on photo quality, lighting, and expression.

**Does the app store my photo?**  
No. Processing is done in temporary memory; nothing is written to disk.

**Can I use a phone selfie?**  
Yes — use good lighting and a plain background, and avoid shadows.

**What if background removal is imperfect?**  
Stand in front of a plain white wall for best results. Use the manual adjustments to fine-tune afterwards.

**What countries are supported?**  
India, USA, UK, EU/Schengen, Australia, and Canada. More on request.
            """)

        st.markdown("#### 🔒 Privacy")
        _render_privacy()
        _render_footer()
        return

    # ── Validate & process ────────────────────────────────────
    raw = uploaded.getvalue()
    sig = f"{uploaded.name}:{len(raw)}:{spec_name}"

    if st.session_state.get("_ul_sig") != sig:
        ok, msg = _rate_ok("upload", UPLOAD_COOLDOWN, MAX_UPLOADS_HR)
        if not ok: st.error(msg); return
        st.session_state["_ul_sig"] = sig

    ok, msg = _validate(raw)
    if not ok:
        st.error(f"❌ {msg}")
        return

    with st.spinner("⚙️ Detecting face · whitening background · resizing…"):
        encoded, quality_val, face_ok, bg_ok, preview, qual_items = _process(raw, spec_name)

    # ── Manual adjustments ────────────────────────────────────
    with st.expander("🎛️ Manual adjustments (optional)"):
        c1, c2 = st.columns(2)
        with c1:
            br = st.slider("Brightness", -60, 60, 0, key="adj_br")
            ct = st.slider("Contrast",   -60, 60, 0, key="adj_ct")
        with c2:
            zm = st.slider("Zoom", 80, 130, 100, format="%d%%", key="adj_zm")
            bg = st.slider("Background whiteness", 0, 100, 100, format="%d%%", key="adj_bg")
        if br or ct or zm != 100 or bg != 100:
            adj = _adjust(Image.open(io.BytesIO(preview)), br, ct, zm, bg)
            encoded, quality_val = _encode_jpeg(adj, spec.max_bytes)
            buf = io.BytesIO(); adj.save(buf, format="JPEG", quality=88, optimize=True)
            preview = buf.getvalue()

    # ── Step 3: Preview ───────────────────────────────────────
    st.markdown("### Step 3 — Review & download")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="compare-label">Original upload</div>', unsafe_allow_html=True)
        st.image(raw, use_container_width=True)
    with c2:
        st.markdown(f'<div class="compare-label">{spec.flag} Passport-ready output</div>', unsafe_allow_html=True)
        st.image(preview, use_container_width=True)

    # ── Quality score ─────────────────────────────────────────
    st.markdown("**Photo quality check**")
    _render_quality(qual_items)

    # ── Compliance report ─────────────────────────────────────
    kb = len(encoded) / 1024
    st.markdown("**Compliance report**")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Dimensions", f"{spec.width_px}×{spec.height_px}", "✅ Exact")
    m2.metric("File size",  f"{kb:.1f} KB", "✅ OK" if kb <= spec.max_bytes/1024 else "❌ Over")
    m3.metric("Background", "White ✅" if bg_ok else "Partial ⚠️")
    m4.metric("Face",       "Found ✅" if face_ok else "Not found ⚠️")

    if not face_ok:
        st.warning("No face detected — center crop was applied. Upload a clear front-facing portrait.")
    if not bg_ok:
        st.warning("Background cleanup was partial. A plain background gives much better results.")

    # ── Download ──────────────────────────────────────────────
    st.markdown("---")
    safe = spec.name.lower().replace(" ","_").replace("/","_")
    dl_col, reset_col = st.columns([4, 1])
    with dl_col:
        st.download_button(
            f"⬇️ Download {spec.flag} {spec.name} JPEG ({kb:.0f} KB)",
            encoded,
            file_name=f"passport_{spec.width_px}x{spec.height_px}_{safe}.jpg",
            mime="image/jpeg",
            on_click=lambda: st.session_state.update(downloaded=True),
            use_container_width=True,
        )
    with reset_col:
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state["nonce"] += 1
            st.rerun()

    # ── Print sheet ───────────────────────────────────────────
    with st.expander("🖨️ Generate print sheet (6×4 inch, print-ready)"):
        st.caption("Creates a standard 6×4 inch sheet with multiple copies — ready for any photo lab.")
        layout = st.radio("Layout", ["2×2", "3×2", "4×2"],
                          horizontal=True, key="print_layout",
                          captions=["4 photos","6 photos","8 photos"])
        if st.button("Generate Print Sheet →", key="gen_sheet"):
            with st.spinner("Building sheet…"):
                sheet_b = _make_print_sheet(preview, spec, layout)
            st.image(sheet_b, caption="6×4 inch · 300 dpi", use_container_width=True)
            st.download_button(
                "⬇️ Download Print Sheet",
                sheet_b,
                file_name=f"print_sheet_{layout.replace('×','x')}.jpg",
                mime="image/jpeg",
                key="dl_sheet",
            )

    # ── Support banner ────────────────────────────────────────
    st.markdown("---")
    _render_bmc_banner()

    # ── Privacy ───────────────────────────────────────────────
    st.markdown("#### 🔒 Privacy")
    _render_privacy()
    _render_footer()


if __name__ == "__main__":
    main()
