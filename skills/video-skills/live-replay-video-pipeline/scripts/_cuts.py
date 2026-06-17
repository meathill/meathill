#!/usr/bin/env python3
"""Shared cut-list helpers for speed-aware editing.

A 03_cut_list.json entry may carry an optional "speed" field (float, default 1.0):
  speed == 1.0  -> kept at original speed, full audio
  speed  > 1.0  -> time-lapsed by that factor and MUTED (silent)

A kept segment's contribution to the edited timeline is (end - start) / speed,
and a point t inside it maps to  cum[i] + (t - start) / speed.
When every segment has speed 1.0 these reduce to the original cut-only math, so
all downstream scripts stay backward compatible.
"""
import json
from pathlib import Path


def load_segments(out_dir):
    """Return sorted [(start, end, speed)] from out/03_cut_list.json."""
    raw = json.loads((Path(out_dir) / "03_cut_list.json").read_text(encoding="utf-8"))
    segs = [(float(c["start"]), float(c["end"]), float(c.get("speed", 1.0))) for c in raw]
    segs.sort(key=lambda x: x[0])
    return segs


def build_cum(segs):
    """Given sorted [(s, e, sp)], return (cum, total) where cum[i] is the edited-
    timeline offset before segment i and total is the full edited duration."""
    cum = []
    acc = 0.0
    for s, e, sp in segs:
        cum.append(acc)
        acc += (e - s) / sp
    return cum, acc


def any_speed(segs):
    """True if any segment is sped up (speed != 1.0)."""
    return any(sp != 1.0 for (_s, _e, sp) in segs)
