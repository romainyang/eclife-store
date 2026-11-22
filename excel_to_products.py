#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
products.xlsx  ->  data/products.json
=====================================
把 Excel 产品表转换成本站唯一数据源 data/products.json。
build.py 会自动调用本模块（只要仓库根目录有 products.xlsx）。

单独运行：
    python excel_to_products.py            # 转换并写回 data/products.json
    python excel_to_products.py --check    # 只校验，不写文件

四张表：
    products  一行一款产品（核心信息 + Feature 1..N）
    images    一行一款产品：key | Image 1 .. Image 15（图片单独一张表）
    specs     长表：key | attribute | value
    reviews   长表：key | rating | title | author | date | body | helpful

兼容旧文件：products 表里若还有 gallery 列，images 表没有该 key 时仍按老写法读。
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(ROOT, 'products.xlsx')
DATA = os.path.join(ROOT, 'data', 'products.json')
IMG_DIR = os.path.join(ROOT, 'images', 'details')

DEFAULT_DIST = [75, 16, 5, 2, 2]
SLUG_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
# gallery 里可以直接写外链（http/https 或 //cdn...），不当作本地文件名处理
IMG_URL_RE = re.compile(r'^(?:https?:)?//', re.I)
IMG_EXT_RE = re.compile(r'\.(jpe?g|png|webp|gif|avif)$', re.I)

# images 表：Image 1 .. Image 15，建议至少填 5 张
IMAGES_MAX = 15
IMAGES_MIN = 5


def is_img_url(v):
    """是不是图片外链（含 data: 内联图）"""
    s = str(v or '').strip()
    return bool(IMG_URL_RE.match(s)) or s.lower().startswith('data:')

# 常用色名 -> 色值（Excel 里可以直接写 white / black / sage 这种词）
NAMED_COLORS = {
    'white': '#f4f1ea', 'cream': '#f4f1ea', 'ivory': '#f4f1ea',
    'black': '#292722', 'charcoal': '#292722',
    'green': '#6b7d6a', 'sage': '#8a9c8b', 'olive': '#6b7d6a',
    'gold': '#c9a24a', 'brass': '#c9a24a',
    'oak': '#8a6a4f', 'walnut': '#6b4a34', 'wood': '#8a6a4f',
    'gray': '#9a9a9a', 'grey': '#9a9a9a',
    'beige': '#e8e2d8', 'taupe': '#c8bda8',
    'blue': '#4a6b8a', 'navy': '#2f4057',
}

# 表头单元格写中文也能识别
HEADER_ALIASES = {
    '名称': 'name', '产品名称': 'name', '标题': 'name',
    '价格': 'price', '售价': 'price', '原价': 'was',
    '属性': 'attribute', '属性名': 'attribute', '值': 'value', '属性值': 'value',
    '评分': 'rating', '打分': 'rating',
    '作者': 'author', '日期': 'date', '内容': 'body', '正文': 'body',
    '有帮助': 'helpful', '有用': 'helpful',
    '图片': 'gallery', '图片文件': 'gallery', '颜色': 'sw', '色块': 'sw',
    '尺寸': 'size', '类型': 'type', '标签': 'badge',
    '描述': 'desc', '副标题': 'sub', '评价数': 'reviewcount',
    'sku': 'key', 'productkey': 'key', '产品编码': 'key', '产品编号': 'key',
    '图片链接': 'gallery',
}
# images 表里 Image 1 / 图片1 / 图1 都认
for _i in range(1, IMAGES_MAX + 3):
    HEADER_ALIASES['图片%d' % _i] = 'image%d' % _i
    HEADER_ALIASES['图%d' % _i] = 'image%d' % _i
    HEADER_ALIASES['image%d' % _i] = 'image%d' % _i
del _i


class ExcelError(Exception):
    """表格内容有问题，构建应该停下并提示用户"""


# ---------------------------------------------------------------- 基础清洗

def _s(v) -> str:
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'yes' if v else ''
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else str(v)
    return str(v).strip()


def _num(v, label, key='', default=None, required=False):
    raw = _s(v)
    if raw == '':
        if required:
            raise ExcelError('%s 为空，必填' % label)
        return default
    cleaned = raw.replace('$', '').replace(',', '').replace('¥', '').strip()
    if cleaned.endswith('%'):
        cleaned = cleaned[:-1]
    try:
        n = float(cleaned)
    except ValueError:
        raise ExcelError('%s 不是数字：%r' % (label, raw))
    return int(n) if n.is_integer() else n


def _list(v):
    """逗号 / 中文逗号 / 分号 / 换行 分隔"""
    return [p.strip() for p in re.split(r'[,，;；\n\r]+', _s(v)) if p.strip()]


def _color(v):
    c = v.strip()
    low = c.lower()
    if low in NAMED_COLORS:
        return NAMED_COLORS[low]
    if not c.startswith('#'):
        c = '#' + c
    return c


def _gallery(v):
    """图片列：既可以是本地文件名（bv390-main），也可以是完整链接（https://.../a.jpg）

    本地文件名会去掉目录，保留后缀（不写后缀就按 .jpg 处理）；
    外链原样保留，不去后缀、不改斜杠。
    """
    out = []
    for g in _list(v):
        g = g.replace('\\', '/').strip()
        if not g:
            continue
        if is_img_url(g):
            out.append(g)          # 外链原样保留，构建时会被下载进仓库
            continue
        g = g.split('/')[-1]       # 本地：只留文件名
        m = IMG_EXT_RE.search(g)
        out.append(g[:m.start()] + m.group(0).lower() if m else g)
    return out


def local_file(g):
    """本地图片的实际文件名：没写后缀就按 .jpg"""
    g = str(g)
    return g if IMG_EXT_RE.search(g) else g + '.jpg'


# ---------------------------------------------------------------- 读表工具

def _sheet(wb, name):
    for ws in wb.worksheets:
        if ws.title.strip().lower() == name:
            return ws
    raise ExcelError('缺少工作表「%s」（现有：%s）'
                     % (name, ' / '.join(w.title for w in wb.worksheets)))


def _headers(ws, need=('key',)):
    """在前 10 行里找表头行，返回 {规范化列名: 列号} 和表头行号"""
    for r in range(1, min(ws.max_row, 10) + 1):
        cols = {}
        for c in range(1, ws.max_column + 1):
            raw = _s(ws.cell(r, c).value)
            name = re.sub(r'\s+', '', raw.lower())
            if name:
                cols[HEADER_ALIASES.get(name, name)] = c
        if all(n in cols for n in need) and len(cols) >= len(need) + 1:
            return cols, r
    raise ExcelError('工作表「%s」找不到表头行（需要包含 %s 等列名）'
                     % (ws.title, '、'.join(need)))


def _rows(ws, cols, header_row):
    """逐行产出 {列名: 值}，跳过空行和以 # 开头的说明行"""
    for r in range(header_row + 1, ws.max_row + 1):
        row = {name: ws.cell(r, col).value for name, col in cols.items()}
        key = _s(row.get('key'))
        if not key or key.startswith('#'):
            continue
        yield r, row


def _images_map(wb, errors, warns):
    """images 表：key | Image 1 .. Image N，一行一款产品的图片

    返回 {key: {列序号: [图片…]}}；没有 images 表时返回空 dict（走旧的 gallery 列）。
    """
    if not any(w.title.strip().lower() == 'images' for w in wb.worksheets):
        return {}
    ws = _sheet(wb, 'images')
    cols, hrow = _headers(ws, need=('key',))
    img_cols = sorted(
        (int(m.group(1)), n) for n, c in cols.items()
        if (m := re.match(r'^image(\d+)$', n))
    )
    if not img_cols:
        raise ExcelError('images 表里没有 Image 1 / Image 2 … 这样的列（第一列必须是 key）')

    out, seen = {}, {}
    for r, row in _rows(ws, cols, hrow):
        key = _s(row['key']).lower()
        if key in seen:
            errors.append('images 第 %d 行：key「%s」和第 %d 行重复，一款产品只占一行'
                          % (r, key, seen[key]))
            continue
        seen[key] = r
        vals = {}
        for idx, name in img_cols:
            v = _s(row.get(name))
            if v:
                vals[idx] = v
        out[key] = vals
    return out


# ---------------------------------------------------------------- 主转换

def convert(xlsx=XLSX, out=DATA, write=True):
    try:
        import openpyxl
    except ImportError:
        raise ExcelError('缺少 openpyxl，先运行： python -m pip install openpyxl')

    if not os.path.exists(xlsx):
        raise ExcelError('找不到 %s' % xlsx)

    wb = openpyxl.load_workbook(xlsx, data_only=True)
    errors, warns = [], []

    # ---- images（图片单独一张表，按 key 对应）
    imgs = _images_map(wb, errors, warns)

    # ---- products
    ws = _sheet(wb, 'products')
    cols, hrow = _headers(ws, need=('key', 'name'))
    feat_cols = sorted(
        (int(m.group(1)), n) for n, c in cols.items()
        if (m := re.match(r'^feature(\d+)$', n))
    )

    products, seen = [], {}

    def parse_row(r, row):
        where = '第 %d 行' % r
        key = _s(row['key']).lower()
        if not SLUG_RE.match(key):
            errors.append('%s key「%s」不合法：只能用小写字母、数字和连字符（如 bv390-white）'
                          % (where, _s(row['key'])))
            return None
        if key in seen:
            errors.append('%s key「%s」和第 %d 行重复；key 决定网址，必须唯一'
                          % (where, key, seen[key]))
            return None
        seen[key] = r

        def need(col, label):
            v = row.get(col)
            if not _s(v):
                errors.append('%s [%s] %s 为空，必填' % (where, key, label))
            return v

        try:
            name = _s(need('name', 'name 产品标题'))
            price = _num(need('price', 'price 售价'), 'price 售价', key, required=True)

            # 图片：优先 images 表里同 key 的那一行（Image 1..15），没有才读 products 的 gallery 列
            cells = imgs.get(key) or {}
            gallery = []
            if cells:
                for idx in sorted(cells):
                    gallery.extend(_gallery(cells[idx]))
            else:
                gallery = _gallery(row.get('gallery'))
            if not gallery:
                errors.append('%s [%s] 没有图片：在 images 表这一行填 Image 1 到 Image 5 以上'
                              % (where, key))
                return None
            if len(gallery) < IMAGES_MIN:
                warns.append('%s [%s] 只有 %d 张图，建议至少 %d 张（主图/侧面/内部/细节/尺寸）'
                             % (where, key, len(gallery), IMAGES_MIN))
            if not name:
                return None

            size = _s(row.get('size')).replace('.0', '')
            ptype = _s(row.get('type')).lower() or 'single'
            if ptype not in ('single', 'double'):
                warns.append('%s [%s] type「%s」不是 single/double，首页筛选用不了'
                             % (where, key, ptype))

            feats = [f for f in (_s(row.get(n)) for _, n in feat_cols) if f]
            sw = [_color(c) for c in _list(row.get('sw'))] or ['#f4f1ea']

            dist_raw = [_s(row.get('dist%d' % i)) for i in (5, 4, 3, 2, 1)]
            if not any(dist_raw):
                dist = [[v, v] for v in DEFAULT_DIST]
            else:
                dist = []
                for i, v in enumerate(dist_raw):
                    pct = int(_num(v, '%d 星占比' % (5 - i), key, default=0) or 0)
                    dist.append([pct, pct])

            stars = _num(row.get('stars'), 'stars 评分', key, default=4.8)
            if not 0 <= float(stars) <= 5:
                warns.append('%s [%s] stars=%s 超出 0-5，已按边界处理' % (where, key, stars))
                stars = max(0, min(5, float(stars)))
            if any(dist_raw):
                total = sum(x[0] for x in dist)
                if total != 100:
                    warns.append('%s [%s] 五档星级占比合计 %d%%，不是 100%%' % (where, key, total))

            was = _num(row.get('was'), 'was 原价', key)
            count = _num(row.get('reviewcount'), 'reviewCount 评价总数', key)

            item = {
                'id': _s(row.get('id')) or 'p%d' % len(products),
                'key': key,
                'name': name,
                'sub': _s(row.get('sub')),
                'size': size,
                'type': ptype,
                'price': price,
            }
            # was 没填就不写这个键，保持 json 干净（键顺序也和原数据一致）
            if was not in (None, ''):
                item['was'] = was
            item.update({
                'badge': _s(row.get('badge')),
                'stars': int(stars) if float(stars).is_integer() else float(stars),
                'sw': sw,
                'gallery': gallery,
                'features': feats,
                'desc': _s(row.get('desc')),
                'specs': [],
            })
            if count:
                item['reviewCount'] = count
            item['ratingDist'] = dist
            item['reviews'] = []
        except ExcelError as e:
            errors.append('%s [%s] %s' % (where, key, e))
            return None

        # 只有本地文件名才检查文件是否存在；外链没法在构建时验证，跳过
        local_imgs = [g for g in gallery if not is_img_url(g)]
        missing = [g for g in local_imgs
                   if not os.path.exists(os.path.join(IMG_DIR, local_file(g)))]
        if missing:
            warns.append('%s [%s] 缺图片文件：%s'
                         % (where, key, ', '.join('images/details/%s' % local_file(m) for m in missing)))
        odd = [g for g in gallery
               if is_img_url(g) and not IMG_EXT_RE.search(g.split('?')[0].split('#')[0])]
        if odd:
            warns.append('%s [%s] 这些图片链接结尾不像图片（没有 .jpg/.png/.webp），'
                         '如果抓不下来会退回外链：%s' % (where, key, ', '.join(odd)))
        return item

    for r, row in _rows(ws, cols, hrow):
        item = parse_row(r, row)
        if item:
            products.append(item)

    if not products and not errors:
        raise ExcelError('products 表里没有读到任何产品（第 3 行开始填，第一列是 key）')

    # id 去重
    used = set()
    for i, p in enumerate(products):
        if p['id'] in used:
            p['id'] = 'p%d' % i
        while p['id'] in used:
            p['id'] += 'x'
        used.add(p['id'])

    by_key = {p['key']: p for p in products}
    bad_keys = set()   # 同一个 key 只报一次，避免级联刷屏

    # ---- images 表里有、products 表里没有的 key
    for k in sorted(imgs):
        if k not in by_key:
            errors.append('images 表：key「%s」在 products 表里不存在' % k)

    # ---- specs
    if any(w.title.strip().lower() == 'specs' for w in wb.worksheets):
        ws = _sheet(wb, 'specs')
        cols, hrow = _headers(ws, need=('key', 'attribute'))
        for r, row in _rows(ws, cols, hrow):
            key = _s(row['key']).lower()
            attr = _s(row.get('attribute'))
            val = _s(row.get('value'))
            if not attr:
                continue
            if key not in by_key:
                if key not in bad_keys:
                    errors.append('specs 第 %d 行：key「%s」在 products 表里不存在' % (r, key))
                    bad_keys.add(key)
                continue
            by_key[key]['specs'].append([attr, val])

    # ---- reviews
    if any(w.title.strip().lower() == 'reviews' for w in wb.worksheets):
        ws = _sheet(wb, 'reviews')
        cols, hrow = _headers(ws, need=('key', 'title'))
        for r, row in _rows(ws, cols, hrow):
            key = _s(row['key']).lower()
            if key not in by_key:
                if key not in bad_keys:
                    errors.append('reviews 第 %d 行：key「%s」在 products 表里不存在' % (r, key))
                    bad_keys.add(key)
                continue
            title = _s(row.get('title'))
            if not title:
                continue
            rev = {
                'title': title,
                'body': _s(row.get('body')),
                'author': _s(row.get('author')) or 'Verified Buyer',
                'date': _s(row.get('date')),
            }
            try:
                helpful = _num(row.get('helpful'), 'helpful', key)
                rating = _num(row.get('rating'), 'rating', key,
                              default=round(float(by_key[key]['stars'])))
            except ExcelError as e:
                errors.append('reviews 第 %d 行 [%s] %s' % (r, key, e))
                continue
            if helpful:
                rev['helpful'] = int(helpful)
            rev['rating'] = max(1, min(5, int(rating)))
            by_key[key]['reviews'].append(rev)

    # reviewCount 留空时用真实评价条数；没有任何评价就清掉分布，详情页不渲染评价区
    for p in products:
        if not p.get('specs'):
            p.pop('specs', None)      # 没有规格就不写这个键，保持 json 干净
        if not p.get('reviewCount') and p['reviews']:
            p['reviewCount'] = len(p['reviews'])
        if not p['reviews'] and not p.get('reviewCount'):
            p.pop('reviewCount', None)
            p['ratingDist'] = []

    print('[excel] %s -> %d products' % (os.path.basename(xlsx), len(products)))
    for p in products:
        print('   %-16s %-6s %-7s $%-8s imgs=%d specs=%d reviews=%d'
              % (p['key'], p['size'], p['type'], p['price'],
                 len(p['gallery']), len(p.get('specs') or []), len(p['reviews'])))
    for w in warns:
        print('   ! ' + w)

    if errors:
        raise ExcelError('表格里有 %d 处需要修正：\n  - %s' % (len(errors), '\n  - '.join(errors)))

    if write:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print('[excel] wrote %s' % os.path.relpath(out, ROOT))
    return products


def main(argv):
    check = '--check' in argv
    try:
        convert(write=not check)
    except ExcelError as e:
        print('\n[excel] 失败：%s\n' % e, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
