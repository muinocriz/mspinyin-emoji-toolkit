#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Basic structural/hash checker for ChsPinyinUDP.lex."""

import argparse
import hashlib
import struct
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(path):
    raw = Path(path).read_bytes()
    if len(raw) < 0x40 or raw[:8] != b"mschxudp":
        raise ValueError("不是 mschxudp")
    count = struct.unpack_from("<I", raw, 0x1C)[0]
    offset_start = struct.unpack_from("<I", raw, 0x10)[0]
    data_start = struct.unpack_from("<I", raw, 0x14)[0]
    declared_size = struct.unpack_from("<I", raw, 0x18)[0]
    if declared_size != len(raw):
        raise ValueError("file_size 字段与实际长度不一致")
    if offset_start + count * 4 > data_start:
        raise ValueError("offset table/data_start 异常")
    offsets = [struct.unpack_from("<I", raw, offset_start+i*4)[0] for i in range(count)]
    if offsets != sorted(offsets):
        raise ValueError("record offsets 非单调")
    return len(raw), count, data_start


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--compare", help="可选：比较另一个文件 SHA256")
    args = ap.parse_args()
    size, count, data_start = inspect(args.file)
    h = sha256(args.file)
    print(f"[结构] OK, size={size}, records={count}, data_start={data_start}")
    print(f"[SHA256] {h}")
    if args.compare:
        h2 = sha256(args.compare)
        print(f"[COMPARE] {h2}")
        print(f"[相同] {'是' if h == h2 else '否'}")


if __name__ == "__main__":
    main()
