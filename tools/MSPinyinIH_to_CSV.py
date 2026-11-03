#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decode Microsoft Pinyin ChsPinyinIH.dat to CSV.

Observed/tested layout for the sample used in this project:
- signature: 55 AA 88 80
- slot count: uint32 @ 0x0C
- data: 0x1400
- record size: 60 bytes
- +0x00 uint32 UTF-16 code-unit length
- +0x04 uint32 timestamp, treated as seconds since 2000-01-01 UTC
- +0x08 uint32 input count / frequency-like counter
- +0x0C UTF-16LE word
Remaining bytes are preserved as raw hex; their semantics are not asserted.
"""
import argparse, csv, struct
from datetime import datetime, timezone, timedelta
from pathlib import Path
BASE=datetime(2000,1,1,tzinfo=timezone.utc)
def ts2000(v):
    try: return (BASE+timedelta(seconds=v)).isoformat().replace('+00:00','Z')
    except Exception: return ''
def main():
    ap=argparse.ArgumentParser(description='ChsPinyinIH.dat -> CSV')
    ap.add_argument('--input',required=True); ap.add_argument('--output',required=True)
    ap.add_argument('--include-empty',action='store_true',help='也输出空槽')
    a=ap.parse_args(); raw=Path(a.input).read_bytes()
    if len(raw)<0x1400 or raw[:4]!=bytes.fromhex('55 aa 88 80'):
        raise SystemExit('不是已知的 ChsPinyinIH.dat 样本格式 (55 AA 88 80)')
    slots=struct.unpack_from('<I',raw,0x0C)[0]
    max_slots=(len(raw)-0x1400)//60
    slots=min(slots,max_slots)
    rows=[]
    for i in range(slots):
        off=0x1400+i*60; rec=raw[off:off+60]
        units,stamp,count=struct.unpack_from('<III',rec,0)
        if units==0 and not a.include_empty: continue
        if units>24:
            word=f'<invalid word_units={units}>'
        else:
            word=rec[12:12+units*2].decode('utf-16le',errors='replace')
        rows.append({
            'slot':i,'offset_hex':f'0x{off:08X}','word_units':units,'word':word,
            'timestamp_raw':stamp,'timestamp_utc':ts2000(stamp),'input_count':count,
            'tail_hex':rec[12+min(units,24)*2:].hex(' '),'record_hex':rec.hex(' ')
        })
    fields=list(rows[0].keys()) if rows else ['slot']
    with Path(a.output).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f'[成功] IH 非空记录 {len(rows)} 条 / slots={slots} -> {a.output}')
    print('[说明] timestamp/input_count 的业务语义按样本和既有逆向命名，未宣称为微软官方字段名。')
if __name__=='__main__': main()
