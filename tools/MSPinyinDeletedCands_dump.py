#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump ChsPinyinDeletedCands.dat internal records.

The examined sample stores no plaintext deleted phrase. It has a DEL header and
8-byte opaque records; therefore this tool deliberately exports IDs/hashes as
hex instead of inventing a word-decoding scheme.
"""
import argparse,csv,struct
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(description='ChsPinyinDeletedCands.dat -> opaque CSV')
    ap.add_argument('--input',required=True); ap.add_argument('--output',required=True)
    a=ap.parse_args(); raw=Path(a.input).read_bytes()
    if len(raw)<0x400 or raw[:4]!=b'DEL ':
        raise SystemExit("不是已知的 DeletedCands 格式（缺少 'DEL '）")
    version=struct.unpack_from('<I',raw,4)[0]
    count=struct.unpack_from('<I',raw,0x14)[0]
    rows=[]
    for i in range(count):
        off=0x400+i*8
        if off+8>len(raw): break
        a1,a2=struct.unpack_from('<II',raw,off)
        rows.append({'index':i,'offset_hex':f'0x{off:08X}',
                     'value1_hex':f'0x{a1:08X}','value2_hex':f'0x{a2:08X}',
                     'raw_hex':raw[off:off+8].hex(' ')})
    with Path(a.output).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['index','offset_hex','value1_hex','value2_hex','raw_hex']); w.writeheader(); w.writerows(rows)
    print(f'[成功] version={version}; header_count={count}; dumped={len(rows)} -> {a.output}')
    print('[说明] 这些是内部不透明记录；样本中没有可直接 UTF-16 解码的删除候选字符串。')
if __name__=='__main__': main()
