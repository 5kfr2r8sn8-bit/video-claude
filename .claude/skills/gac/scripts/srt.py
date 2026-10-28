#!/usr/bin/env python3
"""Print an SRT as numbered lines with times, for planning. Usage: python3 srt.py FILE.srt"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from build import parse_srt
for i, (a, b, t) in enumerate(parse_srt(sys.argv[1]), 1):
    print(f'{i:3d}  {a:7.2f} - {b:7.2f}  ({b - a:4.1f}s)  {t}')
