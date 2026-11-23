#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Walmart promosku 表格 -> Eclife 站点产品数据
============================================
从 Walmart「Product Content And Site Exp」表按列号取字段（该表有多个同名 Measure/Unit
列，按名字取会串，必须按列号），价格另从 ItemReport 用 SKU 匹配。

输出两个东西：
  1. data/walmart_new.json   23 款新产品的完整站点数据（含图片外链）
  2. new-products-<日期>.xlsx 只含这 23 款的上架表格（结构与 products.xlsx 一致）
"""
from __future__ import annotations

import json
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
WM_XLSX = r'D:\Office\Walmart\promosku-20261123 - 副本.xlsx'
WM_REPORT = r'D:\Office\Walmart\ItemReport\ItemReport_20261101.xlsx'
OUT_JSON = os.path.join(ROOT, 'data', 'walmart_new.json')

PRICE_MULT = 1.8          # 售价 = Walmart 价格 × 1.8

# ---- promosku 表列号（0 基）
C = {
    'sku': 3, 'name': 7, 'brand': 8, 'desc': 9,
    'feat0': 10, 'feat1': 11,                  # Key Features、Key Features 1..19
    'mpn': 33, 'model': 34,
    'main_img': 37, 'add_img0': 38,            # Additional Image URL、+1..+10
    'width_v': 79, 'width_u': 80,      # 实测：79 才是产品的宽（48 的柜子这里是 48）
    'height_v': 81, 'height_u': 82,    # 落地柜=高；吊柜/镜柜这里放的是进深
    'depth_v': 85, 'depth_u': 86,      # 落地柜=进深；吊柜/镜柜这里是高
    'weight_v': 83, 'weight_u': 84,
    'vanity_type': 94, 'cabinet_color': 97, 'cabinet_material': 98,
    'care': 102, 'collection': 103, 'color': 104,
    'door_material': 108, 'door_side': 109,
    'faucet_drill': 110, 'faucet_pos': 111,
    'hardware': 113, 'has_mirror': 114, 'has_sink': 115,
    'decor_style': 117, 'assembly': 119,
    'items_included': 121, 'material': 123,
    'mount': 128, 'basins': 134, 'doors': 135, 'drawers': 136,
    'pieces': 138, 'shelves': 139, 'occasion': 140, 'orientation': 142,
    'product_line': 143, 'shape': 145, 'sink_color': 146,
    'sink_install': 147, 'sink_material': 148, 'sink_type': 149,
    'people': 153, 'top_color': 154, 'top_finish': 156, 'top_material': 157,
    'warranty': 161, 'country': 75, 'weight_cap': 125,
}

SW_HEX = {
    'white': '#f4f1ea', 'black': '#292722', 'gray': '#9a9a9a', 'grey': '#9a9a9a',
    'oak': '#8a6a4f', 'walnut': '#6b4a34', 'brown': '#6b4a34', 'beige': '#e8e2d8',
    'green': '#6b7d6a', 'blue': '#4a6b8a', 'cream': '#f4f1ea',
    # 表格里会出现 "Dark Walnut" 这类带前缀的写法，统一按柜体主色归类
    'dark walnut': '#6b4a34', 'light oak': '#8a6a4f', 'natural': '#8a6a4f',
    'espresso': '#4a362a', 'charcoal': '#292722', 'ivory': '#f4f1ea',
}
EXTRA_IMAGES = {
    'BV249AK+VS039': [
        'https://i5.walmartimages.com/asr/97706001-fb97-4dd3-b179-2439bc4eeb10.'
        'ffd673818803fc925e75486c1514f9bc.jpeg',
    ],
}


def s(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    # 源表里有 Quick &amp; Easy 这类 HTML 实体，先解开，不然页面上会显示 &amp;
    return html.unescape(str(v)).strip()


def pretty(v):
    """walmart 的小写值 -> 展示用：black -> Black，manufactured wood -> Manufactured Wood"""
    t = s(v)
    if not t:
        return ''
    if t != t.lower():
        return t
    small = {'and', 'with', 'of', 'or', 'the'}
    words = t.split()
    out = [w if w in small and i else w[:1].upper() + w[1:] for i, w in enumerate(words)]
    return ' '.join(out)


def measure(v, u):
    v, u = s(v), s(u)
    if not v:
        return ''
    return '%s %s' % (v, u) if u else v


def parse_size(name):
    """从标题里取英寸数：48" / 36-Inch / 20'' / 24 in"""
    m = re.search(r'(\d{2,3}(?:\.\d+)?)\s*(?:"|\'\'|”|[-–\s]*(?:inch(?:es)?|in)\b)', name, re.I)
    if not m:
        return ''
    t = m.group(1)
    return t[:-2] if t.endswith('.0') else t


def slugify(sku):
    t = sku.lower().replace('+', '-').replace('_', '-').replace(' ', '-')
    t = re.sub(r'[^a-z0-9-]', '', t)
    return re.sub(r'-{2,}', '-', t).strip('-')


def load_prices():
    import openpyxl
    wb = openpyxl.load_workbook(WM_REPORT, data_only=True)
    ws = wb.active
    hdr = {c.value: i for i, c in enumerate(ws[1])}
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        sku = s(row[hdr['SKU']])
        if not sku:
            continue
        out[sku] = {
            'price': row[hdr['Price']],
            'item_id': s(row[hdr['Item ID']]),
            'url': s(row[hdr['Item Page URL']]),
            'reviews': row[hdr['Reviews Count']],
            'rating': row[hdr['Average Rating']],
        }
    return out


def extract():
    import openpyxl
    prices = load_prices()
    wb = openpyxl.load_workbook(WM_XLSX, data_only=True)
    ws = wb['Product Content And Site Exp']

    def g(r, col):
        return ws.cell(r, col + 1).value

    products, missing_price = [], []
    for r in range(7, ws.max_row + 1):
        sku = s(g(r, C['sku']))
        if not sku:
            continue
        name = s(g(r, C['name']))

        feats = []
        for col in [C['feat0']] + [C['feat1'] + i for i in range(20)]:
            v = s(g(r, col))
            if v and v not in feats:
                feats.append(v)

        imgs = []
        for col in [C['main_img']] + [C['add_img0'] + i for i in range(11)]:
            v = s(g(r, col))
            if v.startswith('http') and v not in imgs:
                imgs.append(v)
        for v in EXTRA_IMAGES.get(sku, []):
            if v not in imgs:
                imgs.append(v)

        wm = prices.get(sku) or {}
        base_price = wm.get('price')
        if not base_price:
            missing_price.append(sku)

        specs = []
        def add(label, val):
            v = s(val) if not isinstance(val, str) else val
            if v:
                specs.append([label, v])

        # 宽/深/高三列在源表里并不稳定：79 和 85 有时是「宽+深」，有时是「深+宽」，
        # 吊柜（镜柜）还把高塞在 85、进深塞在 81。按标题里的英寸数反推哪一列才是宽。
        is_cabinet = 'medicine cabinet' in name.lower()
        v79 = measure(g(r, C['width_v']), g(r, C['width_u']))
        v81 = measure(g(r, C['height_v']), g(r, C['height_u']))
        v85 = measure(g(r, C['depth_v']), g(r, C['depth_u']))

        def num(t):
            m = re.match(r'[\d.]+', str(t or ''))
            return float(m.group(0)) if m else None

        want = num(parse_size(name))
        a, b = num(v79), num(v85)
        if a is None or b is None:
            wide, other = v79, v85
        elif want is None:
            wide, other = (v79, v85) if a >= b else (v85, v79)
        else:
            wide, other = (v79, v85) if abs(a - want) <= abs(b - want) else (v85, v79)
        if is_cabinet:
            w_m, h_m, d_m = wide, other, v81
        else:
            w_m, h_m, d_m = wide, v81, other

        add('Overall Width', w_m)
        add('Overall Depth', d_m)
        add('Overall Height', h_m)
        add('Product Weight', measure(g(r, C['weight_v']), g(r, C['weight_u'])))
        add('Maximum Load', s(g(r, C['weight_cap'])))
        add('Vanity Type', pretty(g(r, C['vanity_type'])))
        add('Mount Type', pretty(g(r, C['mount'])))
        add('Cabinet Color', pretty(g(r, C['cabinet_color'])))
        add('Cabinet Material', pretty(g(r, C['cabinet_material'])))
        add('Door Material', pretty(g(r, C['door_material'])))
        add('Hardware Finish', pretty(g(r, C['hardware'])))
        add('Top Material', pretty(g(r, C['top_material'])))
        add('Top Color', pretty(g(r, C['top_color'])))
        add('Top Finish', pretty(g(r, C['top_finish'])))
        has_sink = s(g(r, C['has_sink'])).lower().startswith('y')
        if has_sink:
            add('Number of Basins', s(g(r, C['basins'])))
            add('Sink Type', pretty(g(r, C['sink_type'])))
            add('Sink Material', pretty(g(r, C['sink_material'])))
            add('Sink Color', pretty(g(r, C['sink_color'])))
            add('Sink Installation', pretty(g(r, C['sink_install'])))
            add('Basin Shape', pretty(g(r, C['shape'])))
            add('Faucet Drillings', pretty(g(r, C['faucet_drill'])))
            add('Faucet Position', pretty(g(r, C['faucet_pos'])))
        add('Number of Doors', s(g(r, C['doors'])))
        add('Number of Drawers', s(g(r, C['drawers'])))
        add('Number of Shelves', s(g(r, C['shelves'])))
        add('Has Mirror', pretty(g(r, C['has_mirror'])))
        add('Items Included', pretty(g(r, C['items_included'])))
        if s(g(r, C['collection'])):
            add('Collection', pretty(g(r, C['collection'])))
        add('Home Decor Style', pretty(g(r, C['decor_style'])))
        add('Assembly Required', pretty(g(r, C['assembly'])))
        add('People for Assembly', s(g(r, C['people'])))
        add('Warranty', s(g(r, C['warranty'])).replace('Monthes', 'Months'))
        add('Country of Origin', pretty(g(r, C['country'])))
        add('Care & Maintenance', pretty(g(r, C['care'])))

        basins_n = s(g(r, C['basins']))
        ptype = 'double' if (basins_n.startswith('2') or 'double' in name.lower()) else 'single'

        color = pretty(g(r, C['cabinet_color'])) or pretty(g(r, C['color'])) or pretty(g(r, C['top_color']))
        if not color:
            m = re.search(r'\b(white|black|gray|grey|oak|walnut|brown)\b', name, re.I)
            color = m.group(1).capitalize() if m else ''
        color = 'Gray' if color.lower() == 'grey' else color
        mount = pretty(g(r, C['mount']))
        if not mount:
            low = name.lower()
            mount = ('Wall Mount' if 'wall mount' in low or 'wall-mount' in low
                     else 'Floating' if 'floating' in low
                     else 'Freestanding' if 'freestanding' in low else '')
        top = pretty(g(r, C['top_material']))
        h_txt = ''
        if h_m:
            num = re.match(r'[\d.]+', h_m)
            h_txt = ('%.1f' % float(num.group(0)) if num else h_m.replace(' in', ''))
        sub_bits = [b for b in (color, mount, (top + ' Top') if top else '',
                               ('%s" H' % h_txt) if h_txt else '') if b]
        sub = ' · '.join(sub_bits)

        # 只取柜体颜色。台面颜色不是变体，混进来会生成"没有图片的假色块"。
        sw = []
        cab = pretty(g(r, C['cabinet_color'])).lower() or color.lower()
        hexv = SW_HEX.get(cab)
        if hexv:
            sw.append(hexv)
        if not sw:
            sw = ['#f4f1ea']

        price = round(float(base_price) * PRICE_MULT, 2) if base_price else None

        products.append({
            'wm_sku': sku,
            'wm_item_id': wm.get('item_id', ''),
            'wm_url': wm.get('url', ''),
            'wm_price': float(base_price) if base_price else None,
            'key': slugify(sku),
            'name': name,
            'sub': sub,
            'size': parse_size(name) or s(g(r, C['width_v'])).split('.')[0],
            'type': ptype,
            'price': price,
            'badge': '',
            'stars': 4.8,
            'sw': sw,
            'gallery': imgs,
            'features': feats[:10],
            'feat_total': len(feats),
            'desc': s(g(r, C['desc'])),
            'specs': specs,
            'reviews': [],
            'ratingDist': [],
        })
    return products, missing_price


def main():
    products, missing = extract()
    print('%d products' % len(products))
    for p in products:
        print('%-22s %-22s $%-8s size=%-4s %-6s imgs=%-2d feat=%d/%d specs=%d'
              % (p['wm_sku'], p['key'], p['price'], p['size'], p['type'],
                 len(p['gallery']), len(p['features']), p['feat_total'], len(p['specs'])))
    if missing:
        print('!! 没匹配到价格：%s' % ', '.join(missing))
    keys = [p['key'] for p in products]
    dup = {k for k in keys if keys.count(k) > 1}
    if dup:
        print('!! key 重复：%s' % dup)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(products, open(OUT_JSON, 'w', encoding='utf-8', newline='\n'),
              ensure_ascii=False, indent=2)
    print('wrote', OUT_JSON)


if __name__ == '__main__':
    sys.exit(main())
