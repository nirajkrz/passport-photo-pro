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

BMC_USERNAME   = "t8tavern"          # buymeacoffee.com/<yourname>
KOFI_USERNAME  = "yourname"          # ko-fi.com/<yourname>
CONTACT_EMAIL  = "tea8tavern@gmail.com"
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
        0.36, 0.30, "630×810 px · JPEG < 250 KB · White background",
    ),
    "🇺🇸  US Passport / Visa": PhotoSpec(
        "US Passport", "🇺🇸", 600, 600, 240*1024,
        0.50, 0.15, "600×600 px · JPEG < 240 KB · White/off-white background",
    ),
    "🇬🇧  UK Passport": PhotoSpec(
        "UK Passport", "🇬🇧", 600, 750, 240*1024,
        0.43, 0.20, "600×750 px · JPEG < 240 KB · Cream/white background",
    ),
    "🇪🇺  EU / Schengen Visa": PhotoSpec(
        "EU / Schengen", "🇪🇺", 560, 700, 200*1024,
        0.43, 0.20, "560×700 px · JPEG < 200 KB · White/light background",
    ),
    "🇦🇺  Australian Passport": PhotoSpec(
        "Australian Passport", "🇦🇺", 472, 590, 200*1024,
        0.40, 0.22, "472×590 px · JPEG < 200 KB · White background",
    ),
    "🇨🇦  Canadian Passport": PhotoSpec(
        "Canadian Passport", "🇨🇦", 600, 750, 240*1024,
        0.42, 0.22, "600×750 px · JPEG < 240 KB · White/light-grey background",
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
    grid-template-columns: repeat(5, 1fr);
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
# 🖼️  Image processing (unchanged core logic)
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FaceBox:
    x: int; y: int; w: int; h: int

def _pil_to_bgr(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

def _bgr_to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))

@st.cache_resource(show_spinner=False)
def _cascade():
    return cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

def _detect_faces(bgr: np.ndarray) -> list[FaceBox]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    rects = _cascade().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )
    if len(rects) == 0:
        return []
    return [FaceBox(int(x), int(y), int(w), int(h)) for x, y, w, h in rects]

def _largest_face(bgr: np.ndarray) -> Optional[FaceBox]:
    faces = _detect_faces(bgr)
    return max(faces, key=lambda f: f.w * f.h) if faces else None

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(v, hi))

def _crop_around_face(img_w: int, img_h: int, f: FaceBox, spec: PhotoSpec) -> tuple[int,int,int,int]:
    aspect = spec.width_px / spec.height_px
    ch = f.h / spec.face_ratio
    cw = ch * aspect
    ch = max(ch, f.h * 2.4)
    cw = max(cw, f.w * 2.0)
    if cw / ch < aspect: cw = ch * aspect
    else: ch = cw / aspect
    cw, ch = min(cw, float(img_w)), min(ch, float(img_h))
    if cw / ch < aspect: cw = ch * aspect
    else: ch = cw / aspect
    left = _clamp((f.x + f.w / 2) - cw / 2, 0, img_w - cw)
    top  = _clamp(f.y - ch * spec.head_top_offset, 0, img_h - ch)
    return int(round(left)), int(round(top)), int(round(left+cw)), int(round(top+ch))

def _center_crop(bgr: np.ndarray, aspect: float) -> np.ndarray:
    h, w = bgr.shape[:2]
    if w / h > aspect:
        nw = int(h * aspect); s = (w - nw) // 2
        return bgr[:, s:s + nw]
    nh = int(w / aspect); s = (h - nh) // 2
    return bgr[s:s + nh, :]

def _whiten_bg(bgr: np.ndarray, face: Optional[FaceBox]) -> tuple[np.ndarray, bool]:
    h, w = bgr.shape[:2]
    mask   = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    bg_mdl = np.zeros((1, 65), np.float64)
    fg_mdl = np.zeros((1, 65), np.float64)
    bx, by = max(8, int(w*.03)), max(8, int(h*.03))
    mask[:by, :] = mask[-by:, :] = cv2.GC_BGD
    mask[:, :bx] = mask[:, -bx:] = cv2.GC_BGD
    mx, my = max(20, int(w*.18)), max(20, int(h*.12))
    mask[my:h-my, mx:w-mx] = cv2.GC_PR_FGD
    if face is not None:
        fl = int(_clamp(face.x - face.w*.9, 0, w-1))
        ft = int(_clamp(face.y - face.h*1.2, 0, h-1))
        fr = int(_clamp(face.x + face.w*1.9, 1, w))
        fb = int(_clamp(face.y + face.h*3.2, 1, h))
        if fr > fl and fb > ft:
            mask[ft:fb, fl:fr] = cv2.GC_FGD
    try:
        cv2.grabCut(bgr, mask, None, bg_mdl, fg_mdl, 5, cv2.GC_INIT_WITH_MASK)
        fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    except cv2.error:
        fg = np.full((h, w), 255, np.uint8)
    k = np.ones((5, 5), np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k)
    fg = cv2.dilate(fg, k)
    fg = cv2.GaussianBlur(fg, (7, 7), 0)
    if np.count_nonzero(fg) / (h * w) < 0.18:
        return bgr, False
    a = (fg.astype(np.float32) / 255.0)[..., None]
    white = np.full_like(bgr, 252)
    return (bgr.astype(np.float32) * a + white.astype(np.float32) * (1-a)).astype(np.uint8), True

def _quality_score(bgr: np.ndarray, face: Optional[FaceBox], n_faces: int) -> list[dict]:
    h, w = bgr.shape[:2]
    gray  = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mean_b = float(np.mean(gray))
    lap    = cv2.Laplacian(gray, cv2.CV_64F).var()

    def _q(label, icon, ok, note):
        return {"label": label, "icon": icon, "ok": ok, "note": note,
                "cls": "q-pass" if ok else "q-fail"}

    items = [
        _q("Brightness", "☀️" if 80<=mean_b<=200 else ("🌑" if mean_b<80 else "💡"),
           80<=mean_b<=200, "Good" if 80<=mean_b<=200 else ("Too dark" if mean_b<80 else "Too bright")),
        _q("Sharpness", "🔍" if lap>100 else "🌫️",
           lap>100, "Sharp" if lap>100 else "Blurry"),
        _q("Face", "🧑" if n_faces==1 else ("❓" if n_faces==0 else "👥"),
           n_faces==1, "Detected" if n_faces==1 else (f"None found" if n_faces==0 else f"{n_faces} faces")),
        _q("Face size", "✅" if (face and face.w*face.h/(w*h)>=0.05) else "⚠️",
           bool(face and face.w*face.h/(w*h)>=0.05), "Good" if (face and face.w*face.h/(w*h)>=0.05) else "Too small"),
        _q("Resolution", "📐" if (w>=MIN_DIM and h>=MIN_DIM) else "📉",
           w>=MIN_DIM and h>=MIN_DIM, "Good" if (w>=MIN_DIM and h>=MIN_DIM) else "Low res"),
    ]
    return items

def _build_passport(img: Image.Image, spec: PhotoSpec):
    bgr = _pil_to_bgr(img)
    all_faces = _detect_faces(bgr)
    face = max(all_faces, key=lambda f: f.w*f.h) if all_faces else None
    quality = _quality_score(bgr, face, len(all_faces))
    aspect = spec.width_px / spec.height_px
    if face:
        l, t, r, b = _crop_around_face(bgr.shape[1], bgr.shape[0], face, spec)
        bgr = bgr[t:b, l:r]
    else:
        bgr = _center_crop(bgr, aspect)
    bgr, bg_ok = _whiten_bg(bgr, _largest_face(bgr))
    bgr = cv2.resize(bgr, (spec.width_px, spec.height_px), interpolation=cv2.INTER_CUBIC)
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
