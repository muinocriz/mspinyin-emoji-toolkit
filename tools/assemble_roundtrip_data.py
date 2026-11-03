#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconstruct data/ChsPinyinUDP_full_roundtrip.csv from compressed Base64 chunks."""

from pathlib import Path
import base64
import gzip
import hashlib

EXPECTED_SHA256 = "42d351f345ddea6f9b1423bbb4dfdce7756420e09cdec0ee86318891bc98d5d2"
EXPECTED_LINES = 3100

root = Path(__file__).resolve().parents[1]
parts_dir = root / "data" / "roundtrip_b64_parts"
out = root / "data" / "ChsPinyinUDP_full_roundtrip.csv"
parts = sorted(parts_dir.glob("chunk_*.b64"))

if not parts:
    raise SystemExit(f"No chunks found: {parts_dir}")

packed_b64 = "".join(p.read_text(encoding="ascii").strip() for p in parts)
raw = gzip.decompress(base64.b64decode(packed_b64))
sha256 = hashlib.sha256(raw).hexdigest()
lines = raw.count(b"\n")

if sha256 != EXPECTED_SHA256:
    raise SystemExit(f"SHA256 mismatch: {sha256}")
if lines != EXPECTED_LINES:
    raise SystemExit(f"Line count mismatch: {lines}")

out.write_bytes(raw)
print(f"[OK] {out}")
print(f"[lines] {lines}")
print(f"[SHA256] {sha256}")
