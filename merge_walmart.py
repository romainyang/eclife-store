#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 walmart_new.json 里的新款并入站点产品，并写出两张表：
  products.xlsx                现有 10 款 + 新款 23 款（站点主表，覆盖上传）
  new-products-20261123.xlsx   只含这 23 款（留档 / 下次上架的参照）

用法： python merge_walmart.py            # 只写表，不下载图片
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import make_products_xlsx as mk

DATA = os.path.join(ROOT, 'data', 'products.json')
NEW = os.path.join(ROOT, 'data', 'walmart_new.json')
OUT_ALL = os.path.join(ROOT, 'products.xlsx')
OUT_NEW = os.path.join(ROOT, 'new-products-20261123.xlsx')

SITE_FIELDS = ('key', 'name', 'sub', 'size', 'type', 'price', 'badge',
               'stars', 'sw', 'gallery', 'features', 'desc', 'specs',
               'reviews', 'ratingDist')


def to_site(p):
    out = {k: p.get(k) for k in SITE_FIELDS if p.get(k) not in (None, '')}
    out.setdefault('badge', '')
    out.setdefault('sw', ['#f4f1ea'])
    out.setdefault('reviews', [])
    out.setdefault('ratingDist', [])
    out.setdefault('specs', [])
    return out


def main():
    old = json.load(open(DATA, encoding='utf-8'))
    new = json.load(open(NEW, encoding='utf-8'))

    # 可重复运行：先把上一轮并进去的同名 key 摘掉，再按最新数据重新追加
    new_keys = {p['key'] for p in new}
    old = [p for p in old if p['key'] not in new_keys]

    merged_new = []
    for i, p in enumerate(new, start=1):
        d = to_site(p)
        d['id'] = 'w%d' % i
        merged_new.append(d)

    combined = old + merged_new
    nfeat = max(len(p.get('features') or []) for p in combined)

    mk.build(combined, OUT_ALL, nfeat=nfeat)
    print('wrote products.xlsx: %d 款（原有 %d + 新增 %d），Feature 列 %d'
          % (len(combined), len(old), len(merged_new), nfeat))

    mk.build(merged_new, OUT_NEW, nfeat=nfeat)
    print('wrote new-products-20261123.xlsx: %d 款' % len(merged_new))

    json.dump(combined, open(os.path.join(ROOT, 'data', 'products_merged.json'), 'w',
                             encoding='utf-8', newline='\n'),
              ensure_ascii=False, indent=2)
    print('wrote data/products_merged.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
