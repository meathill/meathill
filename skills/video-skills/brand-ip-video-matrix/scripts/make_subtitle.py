#!/usr/bin/env python3
"""
生成字幕层 PNG（本机 ffmpeg 无 libfreetype/libass，文字全部由 PIL 渲染后 overlay）。
样式：深色半透明圆角底条 rgba(18,18,18,168) + Arial Rounded Bold 38px 白字，中心 y=1055（避开平台底部 UI）。
用法：python3 make_subtitle.py --text "第一行\n第二行" --out build/sub2.png
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 768, 1368
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",  # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",       # Linux
    "C:/Windows/Fonts/arialbd.ttf",                              # Windows
]
FONT_SIZE = 38
MAX_TEXT_W = 600          # 文字最大宽，超出自动折行
BAR_PAD_X = 28            # 底条左右内边距
BAR_PAD_Y = 18            # 底条上下内边距
RADIUS = 20               # 底条圆角
CENTER_Y = 1055           # 底条中心 y
BG = (18, 18, 18, 168)    # 半透明深灰
FG = (255, 255, 255, 255)


def load_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, FONT_SIZE)
    raise SystemExit(
        "找不到可用字体，尝试安装 DejaVu Sans Bold，或把字体路径加进 FONT_CANDIDATES："
        + ", ".join(FONT_CANDIDATES)
    )


def wrap(text, font, max_w):
    """按像素宽度折行；显式 \n 强制换行"""
    out = []
    for para in text.split("\n"):
        words, line = para.split(), ""
        for w in words:
            cand = f"{line} {w}".strip()
            if font.getlength(cand) <= max_w or not line:
                line = cand
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


def render(text, out_path):
    font = load_font()
    lines = wrap(text, font, MAX_TEXT_W)
    widths = [font.getlength(l) for l in lines]
    line_h = int(font.getbbox("Ag")[3] - font.getbbox("Ag")[1]) + 12

    bar_w = int(max(widths) + BAR_PAD_X * 2)
    bar_h = line_h * len(lines) + BAR_PAD_Y * 2
    x0 = (W - bar_w) // 2
    y0 = int(CENTER_Y - bar_h / 2)

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x0 + bar_w, y0 + bar_h],
                        radius=RADIUS, fill=BG)

    y = y0 + BAR_PAD_Y
    for l, w in zip(lines, widths):
        bbox = font.getbbox(l)
        lh = bbox[3] - bbox[1]
        d.text(((W - w) / 2, y + (line_h - 12 - lh) / 2 - bbox[1]),
               l, font=font, fill=FG)
        y += line_h

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path)
    print(f"[ok] {out_path}  {len(lines)} 行  底条 {bar_w}x{bar_h} @ y={y0}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    render(a.text, a.out)
