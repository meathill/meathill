#!/usr/bin/env python3
"""For each chapter, grab a frame from the EDITED video at the midpoint and
overlay the chapter title at the bottom. Output to out/covers/<idx>_<title>.png.
"""
import json, subprocess, sys, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES_CJK = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
]
FONT_CANDIDATES_LATIN = [
    "/System/Library/Fonts/SFNS.ttf",  # macOS PingFang covers latin too; this is a fallback
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
FONT_CANDIDATES = FONT_CANDIDATES_CJK + FONT_CANDIDATES_LATIN  # for back-compat

def _find(paths, size):
    for p in paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return None

def find_font(size: int) -> ImageFont.FreeTypeFont:
    f = _find(FONT_CANDIDATES, size)
    return f or ImageFont.load_default()

def find_fonts(size: int):
    """Return (cjk_font, latin_font). Latin falls back to cjk if no Latin font found."""
    cjk = _find(FONT_CANDIDATES_CJK, size)
    latin = _find(FONT_CANDIDATES_LATIN, size) or cjk
    return cjk or ImageFont.load_default(), latin or ImageFont.load_default()

def is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF or  # CJK Unified
        0x3400 <= cp <= 0x4DBF or  # CJK Ext A
        0x3000 <= cp <= 0x303F or  # CJK Punctuation
        0xFF00 <= cp <= 0xFFEF or  # Halfwidth/Fullwidth
        0x3040 <= cp <= 0x309F or  # Hiragana
        0x30A0 <= cp <= 0x30FF      # Katakana
    )

def draw_mixed(draw, xy, text, cjk_font, latin_font, fill):
    """Draw text glyph-by-glyph, choosing font per character."""
    x, y = xy
    for ch in text:
        f = cjk_font if is_cjk(ch) else latin_font
        draw.text((x, y), ch, fill=fill, font=f)
        bbox = draw.textbbox((0, 0), ch, font=f)
        x += bbox[2] - bbox[0]

def measure_mixed(draw, text, cjk_font, latin_font):
    w = 0; h = 0
    for ch in text:
        f = cjk_font if is_cjk(ch) else latin_font
        bbox = draw.textbbox((0, 0), ch, font=f)
        w += bbox[2] - bbox[0]
        h = max(h, bbox[3] - bbox[1])
    return w, h

def safe_name(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|\s]+", "_", s).strip("_")
    return s[:40] or "chapter"

def grab_frame(video: Path, t: float, out_png: Path):
    cmd = [
        "ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", str(video),
        "-frames:v", "1", "-q:v", "2", str(out_png),
    ]
    print("[run]", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

def overlay_title(img_path: Path, title: str, idx: int, total: int):
    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    # Bottom dark band
    band_h = int(H * 0.18)
    band = Image.new("RGBA", (W, band_h), (0, 0, 0, 180))
    img.paste(band, (0, H - band_h), band)
    draw = ImageDraw.Draw(img)
    # Title
    title_cjk, title_latin = find_fonts(int(band_h * 0.42))
    badge_cjk, badge_latin = find_fonts(int(band_h * 0.28))
    badge = f"{idx:02d} / {total:02d}"
    pad = int(W * 0.03)
    # Wrap title if too long
    max_text_w = W - 2 * pad
    line = ""
    lines = []
    for ch in title:
        trial = line + ch
        w, _ = measure_mixed(draw, trial, title_cjk, title_latin)
        if w > max_text_w and line:
            lines.append(line); line = ch
        else:
            line = trial
    if line: lines.append(line)
    if len(lines) > 2:  # cap at 2 lines
        lines = [lines[0], "".join(lines[1:])]
    # Draw lines
    line_h = int(band_h * 0.46)
    y = H - band_h + int(band_h * 0.18)
    for ln in lines:
        draw_mixed(draw, (pad, y), ln, title_cjk, title_latin, (255, 255, 255))
        y += line_h
    # Badge top-right of band
    bw, _ = measure_mixed(draw, badge, badge_cjk, badge_latin)
    draw_mixed(draw, (W - pad - bw, H - band_h + int(band_h * 0.22)),
               badge, badge_cjk, badge_latin, (180, 220, 255))
    img.save(img_path, "PNG")

def main():
    if len(sys.argv) < 2:
        print("usage: 07_make_covers.py <video_path>")
        sys.exit(2)
    vid = Path(sys.argv[1]).resolve()
    out_dir = vid.parent / "out"
    edited = out_dir / "04_edited.mp4"
    src = edited if edited.exists() else vid  # fall back to original
    chapters = json.loads((out_dir / "06_chapters.json").read_text(encoding="utf-8"))
    covers = out_dir / "covers"
    covers.mkdir(exist_ok=True)
    total = len(chapters)
    for i, ch in enumerate(chapters, start=1):
        s, e = float(ch["start"]), float(ch["end"])
        mid = s + (e - s) * 0.4  # bias slightly earlier than midpoint
        png = covers / f"{i:02d}_{safe_name(ch['title'])}.png"
        grab_frame(src, mid, png)
        overlay_title(png, ch["title"], i, total)
        print(f"[ok] {png}")

if __name__ == "__main__":
    main()
