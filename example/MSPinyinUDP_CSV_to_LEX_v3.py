#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild Microsoft Pinyin ChsPinyinUDP.lex (mschxudp) from an editable CSV.

Safest usage:
    python MSPinyinUDP_CSV_to_LEX_v3.py ^
        --csv ChsPinyinUDP_full_roundtrip.csv ^
        --template ChsPinyinUDP.lex ^
        --output ChsPinyinUDP.modified.lex

The original/template LEX is read only and is never overwritten.
"""

import argparse
import csv
import struct
from pathlib import Path
from collections import Counter

SIG = b"mschxudp"

def u32(raw, off):
    return struct.unpack_from("<I", raw, off)[0]

def parse_template(path):
    raw = Path(path).read_bytes()
    if len(raw) < 0x40 or raw[:8] != SIG:
        raise ValueError("模板不是 mschxudp LEX/DAT")

    count = u32(raw, 0x1C)
    offset_start = u32(raw, 0x10)
    data_start = u32(raw, 0x14)

    if offset_start != 0x40:
        raise ValueError("目前只支持 offset table 从 0x40 开始的 mschxudp 文件")

    offsets = [u32(raw, offset_start + i*4) for i in range(count)]
    ends = offsets[1:] + [len(raw) - data_start]

    records = []
    for i,(a,b) in enumerate(zip(offsets, ends)):
        rec = raw[data_start+a:data_start+b]
        if len(rec) < 18:
            raise ValueError("模板第 %d 条记录过短" % i)
        phrase_offset = struct.unpack_from("<H", rec, 4)[0]
        records.append({
            "index": i,
            "py": rec[16:phrase_offset-2].decode("utf-16le"),
            "text": rec[phrase_offset:-2].decode("utf-16le"),
            "candidate_slot": rec[6],
            "record_magic": u32(rec, 0),
            "flags_byte": rec[7],
            "type_id": u32(rec, 8),
            "record_timestamp": u32(rec, 12),
        })

    def mode(key, fallback):
        vals = [r[key] for r in records]
        return Counter(vals).most_common(1)[0][0] if vals else fallback

    return {
        "raw_header": raw[:0x40],
        "magic1": u32(raw, 0x08),
        "version": u32(raw, 0x0C),
        "header_timestamp": struct.unpack_from("<Q", raw, 0x20)[0],
        "tail_q": struct.unpack_from("<3Q", raw, 0x28),
        "records": records,
        "defaults": {
            "record_magic": mode("record_magic", 0x00100010),
            "flags_byte": mode("flags_byte", 0x13),
            "type_id": 6,  # New Emoji records in ChsPinyinUDP use this most commonly.
            "record_timestamp": mode("record_timestamp", 0),
        }
    }

def to_int(value, default=None):
    if value is None:
        return default
    s = str(value).strip()
    if s == "":
        return default
    return int(s, 0)

def load_csv(path, defaults):
    rows = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        required = {"py","text","candidate_slot"}
        missing = required - set(r.fieldnames or [])
        if missing:
            raise ValueError("CSV 缺少列: " + ", ".join(sorted(missing)))

        for line_no, row in enumerate(r, start=2):
            py = (row.get("py") or "").strip()
            text = row.get("text")
            if text is None:
                text = ""
            slot = to_int(row.get("candidate_slot"))

            if not py:
                raise ValueError("CSV 第 %d 行 py 为空" % line_no)
            if slot is None or not (0 <= slot <= 255):
                raise ValueError("CSV 第 %d 行 candidate_slot 必须为 0..255" % line_no)

            rows.append({
                "py": py,
                "text": text,
                "candidate_slot": slot,
                "record_magic": to_int(row.get("record_magic"), defaults["record_magic"]),
                "flags_byte": to_int(row.get("flags_byte"), defaults["flags_byte"]),
                "type_id": to_int(row.get("type_id"), defaults["type_id"]),
                "record_timestamp": to_int(
                    row.get("record_timestamp"),
                    defaults["record_timestamp"]
                ),
            })
    return rows

def make_record(row):
    pyb = row["py"].encode("utf-16le")
    textb = row["text"].encode("utf-16le")

    phrase_offset = 16 + len(pyb) + 2
    if phrase_offset > 0xFFFF:
        raise ValueError("拼音过长，phrase_offset 超出 uint16")

    return (
        struct.pack(
            "<I H B B I I",
            row["record_magic"] & 0xFFFFFFFF,
            phrase_offset,
            row["candidate_slot"] & 0xFF,
            row["flags_byte"] & 0xFF,
            row["type_id"] & 0xFFFFFFFF,
            row["record_timestamp"] & 0xFFFFFFFF,
        )
        + pyb + b"\x00\x00"
        + textb + b"\x00\x00"
    )

def build_lex(template, rows):
    records = [make_record(r) for r in rows]
    offsets = []
    pos = 0
    for rec in records:
        offsets.append(pos)
        pos += len(rec)

    count = len(records)
    offset_start = 0x40
    data_start = offset_start + count * 4
    file_size = data_start + sum(len(x) for x in records)

    header = bytearray(0x40)
    header[0:8] = SIG
    struct.pack_into("<I", header, 0x08, template["magic1"])
    struct.pack_into("<I", header, 0x0C, template["version"])
    struct.pack_into("<I", header, 0x10, offset_start)
    struct.pack_into("<I", header, 0x14, data_start)
    struct.pack_into("<I", header, 0x18, file_size)
    struct.pack_into("<I", header, 0x1C, count)
    struct.pack_into("<Q", header, 0x20, template["header_timestamp"])
    struct.pack_into("<3Q", header, 0x28, *template["tail_q"])

    out = bytearray(header)
    for off in offsets:
        out += struct.pack("<I", off)
    for rec in records:
        out += rec
    return bytes(out)

def validate(raw):
    if raw[:8] != SIG:
        raise ValueError("输出签名错误")
    count = u32(raw, 0x1C)
    data_start = u32(raw, 0x14)
    declared_size = u32(raw, 0x18)
    if declared_size != len(raw):
        raise ValueError("输出文件长度字段不匹配")
    if data_start != 0x40 + count*4:
        raise ValueError("输出 data_start 不匹配")
    return count

def main():
    ap = argparse.ArgumentParser(
        description="把完整 ChsPinyinUDP CSV 重建为 mschxudp .lex"
    )
    ap.add_argument("--csv", required=True, help="完整可编辑 CSV（UTF-8）")
    ap.add_argument("--template", required=True, help="原始 ChsPinyinUDP.lex，只读用作模板")
    ap.add_argument("--output", required=True, help="输出新的 .lex 文件")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    template_path = Path(args.template)
    output_path = Path(args.output)

    # Never overwrite the template/original file.
    if output_path.resolve() == template_path.resolve():
        raise SystemExit("拒绝覆盖模板原文件。请指定一个新的输出文件名。")

    t = parse_template(template_path)
    rows = load_csv(csv_path, t["defaults"])

    # ChsPinyinUDP.lex is ordered by the pinyin/input-code field.
    # Keep equal-key rows in their original relative order (Python sort is stable).
    was_sorted = all(rows[i]["py"] <= rows[i+1]["py"] for i in range(len(rows)-1))
    if not was_sorted:
        print("[提示] CSV 的 py 顺序不是字典序；已自动排序后再生成 LEX。")
    rows = sorted(rows, key=lambda r: r["py"])

    # Compare normalized records against template as a multiset.
    # This reports genuinely new records even when the user appended them at the CSV end.
    def rec_key(r):
        return (
            r["py"], r["text"], r["candidate_slot"],
            r["record_magic"], r["flags_byte"],
            r["type_id"], r["record_timestamp"]
        )

    template_counter = Counter(rec_key(r) for r in t["records"])
    added_positions = []
    seen = Counter()
    for pos, r in enumerate(rows, start=1):
        k = rec_key(r)
        seen[k] += 1
        if seen[k] > template_counter[k]:
            added_positions.append((pos, r))

    raw = build_lex(t, rows)
    count = validate(raw)
    output_path.write_bytes(raw)

    print("[成功] 写入 %d 条记录" % count)
    print("[输出] %s" % output_path)

    if added_positions:
        print("")
        print("[新增记录最终位置]")
        for pos, r in added_positions:
            # pos is 1-based LEX record number; +1 is the CSV/Excel row including header.
            print(
                "  第 %d 条记录 / Excel 第 %d 行 : %s -> %s  (slot=%d)"
                % (pos, pos + 1, r["py"], r["text"], r["candidate_slot"])
            )
    else:
        print("")
        print("[新增记录最终位置] 未检测到相对模板新增的完整记录。")

    print("")
    print("注意：这只是生成新文件，不会自动替换 Windows 系统目录里的原始 LEX。")

if __name__ == "__main__":
    main()
