#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UserDefinedPhrase.dat / mschxudp -> CSV.

This is intentionally a thin wrapper around the generic mschxudp parser used
for ChsPinyinUDP.lex: the record container is the same family, while field
values (notably flags/category fields) can differ between user phrase and
system UDP files.
"""
import argparse,csv,json
from pathlib import Path
from MSPinyinUDP_LEX_to_CSV import parse_lex

def main():
    ap=argparse.ArgumentParser(description='UserDefinedPhrase.dat (mschxudp) -> CSV')
    ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); ap.add_argument('--metadata')
    a=ap.parse_args(); meta,rows=parse_lex(a.input)
    fields=['index','py','text','candidate_slot','record_magic','flags_byte','type_id','record_timestamp']
    with Path(a.output).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    if a.metadata: Path(a.metadata).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'[成功] mschxudp 用户短语 {len(rows)} 条 -> {a.output}')
if __name__=='__main__': main()
