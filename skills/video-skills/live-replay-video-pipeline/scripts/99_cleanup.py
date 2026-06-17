#!/usr/bin/env python3
"""手动清理中间产物。**不会**被流程自动调用——请在**上传视频之后**自己运行，
这样中间文件只在你确认不再需要时才删。

默认是 DRY-RUN（只列出将删除什么，不真删）；加 --yes 才真正删除。

档位：
  (默认 safe)   删 scratch（可秒级重生成、不参与上传的大文件 / 工作目录）。
               保留所有成片产物 + 转写 + cut list（可随时重跑 05/06/...）。
  --minimal    连 source 转写 / cut list / 中间 JSON / covers(章节卡) 一起删，
               **只留上传需要的**。建议上传完再用。
  --keep {both,04,08}  你上传了哪一版就保留哪版（删掉另一版的视频+字幕+章节）。
               默认 both（两版都留）。

永不删除：被保留版本的视频 / 字幕 / 章节、09_publish_package.md、cover*.png(主封面)。
"""
import argparse, sys, shutil
from pathlib import Path

SCRATCH = ["01_audio.wav", "01_audio.ogg", "_edited_transcript.txt",
           "04_edited.fs.mp4", "_mimo_probe.wav", "_whispercpp.json"]
SCRATCH_DIRS = ["_edit_work", "_insert_work"]
INTERMEDIATE = ["02_transcript.json", "02_transcript.txt", "02_transcript.raw.json",
                "03_cut_list.json", "03_cut_list.bak.json"]
SET_04 = ["04_edited.mp4", "05_subtitles.srt", "06_chapters.txt", "06_chapters.json"]
SET_08 = ["08_final.mp4", "08_final_subtitles.srt", "08_final_chapters.txt",
          "08_final_chapters.json"]
IMG_EXT = (".png", ".jpg", ".jpeg")


def human(n):
    n = float(n)
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def size_of(p: Path) -> int:
    if p.is_dir():
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return p.stat().st_size


def protected(p: Path, keep: str, minimal: bool) -> bool:
    if p.name == "09_publish_package.md":
        return True
    if p.name.lower().startswith("cover") and p.suffix.lower() in IMG_EXT:
        return True                              # 主封面图永远留
    if p.name == "covers" and p.is_dir():
        return not minimal                       # 章节卡：只有 minimal 才删
    if p.name in SET_08:
        return keep in ("both", "08")
    if p.name in SET_04:
        return keep in ("both", "04")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--minimal", action="store_true", help="只留上传需要的文件")
    ap.add_argument("--keep", choices=["both", "04", "08"], default="both",
                    help="保留哪一版视频（删另一版）")
    ap.add_argument("--yes", action="store_true", help="真正删除（默认 dry-run）")
    args = ap.parse_args()
    out = Path(args.video).resolve().parent / "out"
    if not out.exists():
        print(f"[err] {out} 不存在"); sys.exit(2)

    candidates = list(SCRATCH) + list(SCRATCH_DIRS) + list(SET_04) + list(SET_08) + ["covers"]
    if args.minimal:
        candidates += INTERMEDIATE
    seen = set(); targets = []
    for n in candidates:
        if n in seen:
            continue
        seen.add(n)
        p = out / n
        if p.exists() and not protected(p, args.keep, args.minimal):
            targets.append(p)

    kept = sorted(c.name + ("/" if c.is_dir() else "")
                  for c in out.iterdir() if c not in targets)

    if not targets:
        print("[ok] 没有可清理的文件。")
    else:
        total = 0
        mode = ("minimal" if args.minimal else "safe") + f", keep={args.keep}"
        print(f"{'将删除' if args.yes else 'DRY-RUN（将删除）'} — 模式={mode}:")
        for p in sorted(targets, key=size_of, reverse=True):
            sz = size_of(p); total += sz
            print(f"  {human(sz):>9}  {p.name}{'/' if p.is_dir() else ''}")
        print(f"  {'-'*9}\n  {human(total):>9}  合计")
        if not args.yes:
            print("\n[dry-run] 加 --yes 才真正删除。")
        else:
            for p in targets:
                shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
            print(f"\n[ok] 已删除 {len(targets)} 项，回收约 {human(total)}。")

    print("\n保留：")
    for n in kept:
        print(f"  {n}")


if __name__ == "__main__":
    main()
