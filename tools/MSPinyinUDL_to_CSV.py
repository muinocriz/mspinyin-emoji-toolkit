#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decode Microsoft Pinyin ChsPinyinUDL.dat to CSV.

Observed/tested layout for the sample used in this project:
- signature: 55 AA 88 81
- count: uint32 @ 0x0C
- data: 0x2400
- record size: 60 bytes
- +0x00 uint32 timestamp, seconds since 2000-01-01 UTC
- +0x04..+0x06 3-byte short key / jianpin
- +0x0A byte word UTF-16 code-unit length
- +0x0B byte flag (usually 0x5A in the sample)
- +0x0C UTF-16LE word
- immediately after word: word_len uint16 pinyin indices

Pinyin index table follows nopdan/rose format/mspy_udl/pinyin_list.go.
"""
import argparse, csv, struct
from datetime import datetime, timezone, timedelta
from pathlib import Path
from mspy_pinyin_list import PY_LIST

BASE = datetime(2000,1,1,tzinfo=timezone.utc)

def ts2000(v):
    try:
        return (BASE + timedelta(seconds=v)).isoformat().replace('+00:00','Z')
    except Exception:
        return ''

def main():
    ap=argparse.ArgumentParser(description='ChsPinyinUDL.dat -> CSV')
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    args=ap.parse_args()
    raw=Path(args.input).read_bytes()
    if len(raw)<0x2400 or raw[:4] != bytes.fromhex('55 aa 88 81'):
        raise SystemExit('不是已知的 ChsPinyinUDL.dat 样本格式 (55 AA 88 81)')
    count=struct.unpack_from('<I',raw,0x0C)[0]
    max_count=(len(raw)-0x2400)//60
    if count>max_count:
        raise SystemExit(f'header count={count} 超过可容纳记录数 {max_count}')
    rows=[]
    for i in range(count):
        off=0x2400+i*60
        rec=raw[off:off+60]
        stamp=struct.unpack_from('<I',rec,0)[0]
        short_raw=rec[4:7]
        short=''.join(chr(x) if 32<=x<127 else '' for x in short_raw).rstrip('\x00')
        word_units=rec[10]
        flag=rec[11]
        if word_units>12:
            word=f'<invalid word_units={word_units}>'
            indices=[]; pys=[]
        else:
            p=12+word_units*2
            word=rec[12:p].decode('utf-16le',errors='replace')
            indices=[struct.unpack_from('<H',rec,p+2*j)[0] for j in range(word_units)]
            pys=[PY_LIST[x] if x < len(PY_LIST) else f'<idx:{x}>' for x in indices]
        rows.append({
            'index':i,
            'offset_hex':f'0x{off:08X}',
            'timestamp_raw':stamp,
            'timestamp_utc':ts2000(stamp),
            'short_key':short,
            'bytes_7_9_hex':rec[7:10].hex(' '),
            'word_units':word_units,
            'flag_hex':f'0x{flag:02X}',
            'word':word,
            'pinyin':"'".join(pys),
            'pinyin_indices':' '.join(map(str,indices)),
            'record_hex':rec.hex(' '),
        })
    fields=list(rows[0].keys()) if rows else ['index']
    with Path(args.output).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f'[成功] UDL {len(rows)} 条 -> {args.output}')
    print(f'[头部] count={count}; data_start=0x2400; record_size=60')

if __name__=='__main__': main()
