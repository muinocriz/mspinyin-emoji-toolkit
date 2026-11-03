#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge a small Emoji patch CSV into a full ChsPinyinUDP CSV."""

import argparse
import csv
from pathlib import Path

FIELDS = ["index", "py", "text", "candidate_slot", "record_magic", "flags_byte", "type_id", "record_timestamp"]


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description="把小型 patch CSV 合并进完整 UDP CSV")
    ap.add_argument("--base", required=True, help="LEX_to_CSV 生成的完整 CSV")
    ap.add_argument("--patch", required=True, help="补丁 CSV，至少包含 py,text,candidate_slot")
    ap.add_argument("--output", required=True, help="输出合并后的完整 CSV")
    args = ap.parse_args()

    base = read_csv(args.base)
    patch = read_csv(args.patch)
    if not patch:
        raise SystemExit("patch 为空")
    missing = {"py", "text", "candidate_slot"} - set(patch[0].keys())
    if missing:
        raise SystemExit("patch 缺少列: " + ", ".join(sorted(missing)))

    rows = []
    for r in base:
        rows.append({k: r.get(k, "") for k in FIELDS})
    for r in patch:
        nr = {k: "" for k in FIELDS}
        for k in FIELDS:
            if k in r:
                nr[k] = r.get(k, "")
        nr["index"] = ""
        rows.append(nr)

    # Stable sort: existing equal-py order and patch order are preserved.
    rows = sorted(rows, key=lambda r: r["py"])
    for i, r in enumerate(rows):
        r["index"] = i

    with Path(args.output).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"[成功] base={len(base)} + patch={len(patch)} -> {len(rows)} 条")
    print("[补丁最终位置]")
    # Track by py/text/slot, enough for a human-facing patch report.
    for p in patch:
        for i, r in enumerate(rows, start=1):
            if r["py"] == p.get("py", "") and r["text"] == p.get("text", "") and r["candidate_slot"] == p.get("candidate_slot", ""):
                print(f"  第 {i} 条 / Excel 第 {i+1} 行 : {r['py']} -> {r['text']} (slot={r['candidate_slot']})")
                break
    print(f"[输出] {args.output}")


if __name__ == "__main__":
    main()
