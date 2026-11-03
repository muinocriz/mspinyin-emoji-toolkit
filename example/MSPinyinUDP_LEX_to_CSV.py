#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse Microsoft Pinyin ChsPinyinUDP.lex (mschxudp) to editable CSV."""

import argparse
import csv
import json
import struct
from pathlib import Path

SIG = b"mschxudp"


def u32(raw, off):
    return struct.unpack_from("<I", raw, off)[0]


def parse_lex(path):
    raw = Path(path).read_bytes()
    if len(raw) < 0x40 or raw[:8] != SIG:
        raise ValueError("不是受支持的 mschxudp LEX/DAT 文件")

    magic1 = u32(raw, 0x08)
    version = u32(raw, 0x0C)
    offset_start = u32(raw, 0x10)
    data_start = u32(raw, 0x14)
    declared_size = u32(raw, 0x18)
    count = u32(raw, 0x1C)
    header_timestamp = struct.unpack_from("<Q", raw, 0x20)[0]
    tail_q = struct.unpack_from("<3Q", raw, 0x28)

    if declared_size != len(raw):
        raise ValueError(f"文件长度字段不匹配: header={declared_size}, actual={len(raw)}")
    if offset_start + count * 4 > len(raw):
        raise ValueError("offset table 越界")

    offsets = [u32(raw, offset_start + i * 4) for i in range(count)]
    ends = offsets[1:] + [len(raw) - data_start]
    rows = []

    for i, (a, b) in enumerate(zip(offsets, ends)):
        if a > b or data_start + b > len(raw):
            raise ValueError(f"第 {i+1} 条 offset 越界")
        rec = raw[data_start + a:data_start + b]
        if len(rec) < 18:
            raise ValueError(f"第 {i+1} 条记录过短")

        phrase_offset = struct.unpack_from("<H", rec, 4)[0]
        if phrase_offset < 18 or phrase_offset > len(rec) - 2:
            raise ValueError(f"第 {i+1} 条 phrase_offset 异常: {phrase_offset}")
        if rec[phrase_offset-2:phrase_offset] != b"\x00\x00" or rec[-2:] != b"\x00\x00":
            raise ValueError(f"第 {i+1} 条 UTF-16LE 终止符异常")

        py = rec[16:phrase_offset-2].decode("utf-16le")
        text = rec[phrase_offset:-2].decode("utf-16le")
        rows.append({
            "index": i,
            "py": py,
            "text": text,
            "candidate_slot": rec[6],
            "record_magic": u32(rec, 0),
            "flags_byte": rec[7],
            "type_id": u32(rec, 8),
            "record_timestamp": u32(rec, 12),
        })

    metadata = {
        "signature": SIG.decode("ascii"),
        "magic1": magic1,
        "version": version,
        "offset_start": offset_start,
        "data_start": data_start,
        "file_size": len(raw),
        "record_count": count,
        "header_timestamp": header_timestamp,
        "tail_q": list(tail_q),
        "py_sorted": all(rows[i]["py"] <= rows[i+1]["py"] for i in range(len(rows)-1)),
    }
    return metadata, rows


def main():
    ap = argparse.ArgumentParser(description="ChsPinyinUDP.lex -> CSV")
    ap.add_argument("--input", required=True, help="输入 ChsPinyinUDP.lex")
    ap.add_argument("--output", required=True, help="输出 CSV")
    ap.add_argument("--metadata", help="可选：输出文件头 metadata JSON")
    args = ap.parse_args()

    meta, rows = parse_lex(args.input)
    out = Path(args.output)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["index", "py", "text", "candidate_slot", "record_magic", "flags_byte", "type_id", "record_timestamp"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    if args.metadata:
        Path(args.metadata).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[成功] 解析 {len(rows)} 条记录")
    print(f"[输出] {out}")
    print(f"[排序] py 字典序: {'是' if meta['py_sorted'] else '否'}")
    if args.metadata:
        print(f"[Metadata] {args.metadata}")


if __name__ == "__main__":
    main()
