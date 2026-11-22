#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data/products.json  ->  products.xlsx
=====================================
把当前站点的产品数据导出成 Excel 产品表（带格式、下拉选项、说明页）。
改完 Excel 后运行 build.py 即可重新生成所有页面。

用法：
    python make_products_xlsx.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data', 'products.json')
OUT = os.path.join(ROOT, 'products.xlsx')

INK = 'FF292722'
CREAM = 'FFF8F5F0'
GOLD = 'FFC9A24A'
GREY = 'FF6B675F'

PRODUCT_COLS = [
    ('key', 18, '必填 · 网址标识'),
    ('name', 46, '必填 · 产品标题'),
    ('sub', 34, '副标题：颜色 · 款式 · 台面 · 高度'),
    ('size', 7, '尺寸数字'),
    ('type', 9, 'single / double'),
    ('price', 10, '必填 · 售价'),
    ('was', 10, '原价（不促销就留空）'),
    ('badge', 13, 'Featured/Best Seller/New/Sale/Premium'),
    ('stars', 8, '评分 0-5'),
    ('reviewCount', 11, '评价总数（留空=按 reviews 条数）'),
    ('sw', 22, '色块颜色，逗号分隔'),
    ('gallery', 40, '必填 · 图片文件名，逗号分隔，第一张是主图'),
]
FEATURE_COLS = 6
TAIL_COLS = [
    ('desc', 70, '长描述（详情页正文 + SEO 描述）'),
    ('dist5', 7, '5 星占比 %'),
    ('dist4', 7, '4 星占比 %'),
    ('dist3', 7, '3 星占比 %'),
    ('dist2', 7, '2 星占比 %'),
    ('dist1', 7, '1 星占比 %'),
    ('id', 7, '内部 id，留空自动生成，勿改已有值'),
]

GUIDE = [
    ('Eclife 产品表使用说明', True),
    ('', False),
    ('改完这个文件，把 products.xlsx 上传到 GitHub 仓库根目录（覆盖旧的），', False),
    ('Actions 会自动重建所有页面并在 1-2 分钟后上线。', False),
    ('', False),
    ('一、products 表（第 1 张表）', True),
    ('每一行 = 一款产品。第 3 行开始填，第 2 行是灰色说明行，不要删也不要改（程序会自动跳过以 # 开头的行）。', False),
    ('行的顺序 = 首页展示顺序，想置顶就往上挪。', False),
    ('', False),
    ('key        必填。小写字母/数字/连字符，决定产品网址：/product/<key>/。一旦发布不要再改，改了旧链接会 404。', False),
    ('name       必填。产品标题，会显示在卡片、详情页和搜索引擎标题里。', False),
    ('sub        副标题。建议写成「Sage Green · Freestanding · 33.5" H」这种结构。', False),
    ('size       尺寸数字（18/24/30/48/60/72）。填数字即可，程序会转成文本；首页按尺寸筛选靠它。', False),
    ('type       只能是 single 或 double（单盆/双盆），有下拉可选。', False),
    ('price      必填。售价，只填数字（999.99）。有 $ 符号也能识别。', False),
    ('was        原价/划线价。不促销就留空；填了之后首页会多一个 "Sale" 筛选命中。', False),
    ('badge      角标，留空则不显示。常用：Featured / Best Seller / New / Sale / Premium（有下拉）。', False),
    ('stars      评分 0-5，可写 4.9。留空默认 4.8。星级图标按四舍五入取整。', False),
    ('reviewCount 评价总数，用来显示 "Based on N verified reviews"。留空则按 reviews 表的条数算。', False),
    ('sw         色块颜色，可写 #8a9c8b，也可写 white / black / sage / oak / gold 等色名。多个用逗号分隔。', False),
    ('gallery    必填。图片文件名，不带 .jpg 后缀，多张用逗号分隔，第一张是主图。', False),
    ('           例如：bv390-main, bv390-front, bv390-drawer', False),
    ('           图片本体要上传到 images/details/ 目录，文件名必须对得上，否则详情页会裂图。', False),
    ('Feature 1-6 五点卖点，一行一条。用「小标题：正文」格式最好读，例如：', False),
    ('           Double Sink Convenience: The 48" width with two basins is perfect for couples.', False),
    ('           用不到的行留空即可，也可以自己加 Feature 7、8 列。', False),
    ('desc       长描述，会作为详情页正文和搜索引擎描述（建议 300-600 字符）。', False),
    ('dist5-1    评价星级分布百分比，五个加起来 100。全部留空则默认 75/16/5/2/2。', False),
    ('id         内部编号，购物车用它区分商品。新行留空会自动生成，已有行不要改。', False),
    ('', False),
    ('二、specs 表（规格参数）', True),
    ('长表：key | attribute | value。一款产品几行就写几行，顺序就是页面上的显示顺序。', False),
    ('key 必须和 products 表里的 key 完全一致，否则会提示报错。没有规格的产品可以整行不写。', False),
    ('', False),
    ('三、reviews 表（客户评价）', True),
    ('长表：key | rating | title | author | date | body | helpful。', False),
    ('rating 填 1-5（这条评价自己的星级）；date 随便写，如 Aug 2026；helpful 是有多少人觉得有用，可留空。', False),
    ('一款产品至少要有一条评价，否则详情页不会显示评价区（这是刻意的，避免出现 Based on 0 reviews）。', False),
    ('', False),
    ('四、新增一款产品的完整流程', True),
    ('1. 把产品图压到 1400px 宽，命名成 bv390-main.jpg 这种格式，上传到 images/details/。', False),
    ('2. 在 products 表最后加一行，填 key / name / price / gallery 等。', False),
    ('3. 需要的话在 specs、reviews 表里补上这个 key 对应的行。', False),
    ('4. 保存成 .xlsx，拖到 GitHub 仓库上传，等 Actions 转绿。', False),
    ('5. 打开 https://yange.asia/product/<key>/ 检查，再去首页看卡片。', False),
    ('', False),
    ('五、常见报错', True),
    ('「key 不合法」—— 用了大写、空格或中文。只能 a-z、0-9、连字符。', False),
    ('「key 重复」—— 同一个 key 写了两行，key 必须唯一。', False),
    ('「price 不是数字」—— 混进了字母或者用了中文标点。', False),
    ('「缺图片文件」—— 只是警告不会中断，但页面上那张图会是裂的，记得补图。', False),
]


def main():
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        print('缺少 openpyxl，先运行： python -m pip install openpyxl', file=sys.stderr)
        return 1

    products = json.load(open(DATA, encoding='utf-8'))
    nfeat = max([len(p.get('features') or []) for p in products] + [FEATURE_COLS])
    nfeat = max(FEATURE_COLS, min(nfeat, 10))

    head_fill = PatternFill('solid', fgColor=INK)
    head_font = Font(color='FFFFFFFF', bold=True, size=10)
    note_font = Font(color=GREY, size=9, italic=True)
    thin = Side(style='thin', color='FFDDD8CE')
    border = Border(bottom=thin)

    wb = Workbook()

    # ---------------- products
    ws = wb.active
    ws.title = 'products'

    cols = list(PRODUCT_COLS) + [('Feature %d' % i, 52, '卖点 %d' % i) for i in range(1, nfeat + 1)] + list(TAIL_COLS)

    for j, (name, width, _) in enumerate(cols, start=1):
        c = ws.cell(1, j, name)
        c.fill, c.font = head_fill, head_font
        c.alignment = Alignment(horizontal='center', vertical='center')
        ws.column_dimensions[get_column_letter(j)].width = width
        note = ws.cell(2, j, '# ' + _)
        note.font = note_font
        note.alignment = Alignment(vertical='center', wrap_text=False)
    ws.row_dimensions[1].height = 26
    ws.row_dimensions[2].height = 18
    ws.freeze_panes = 'C3'

    for i, p in enumerate(products):
        r = 3 + i
        vals = {
            'key': p['key'], 'name': p['name'], 'sub': p.get('sub', ''),
            'size': p.get('size', ''), 'type': p.get('type', ''),
            'price': p['price'], 'was': p.get('was'),
            'badge': p.get('badge') or '', 'stars': p.get('stars'),
            'reviewCount': p.get('reviewCount'),
            'sw': ', '.join(p.get('sw') or []),
            'gallery': ', '.join(p.get('gallery') or []),
            'desc': p.get('desc', ''),
            'id': p.get('id'),
        }
        dist = p.get('ratingDist') or []
        for k, name in enumerate(('dist5', 'dist4', 'dist3', 'dist2', 'dist1')):
            vals[name] = dist[k][0] if k < len(dist) else None
        for k, f in enumerate(p.get('features') or [], start=1):
            vals['Feature %d' % k] = f

        for j, (name, _w, _n) in enumerate(cols, start=1):
            c = ws.cell(r, j, vals.get(name))
            c.alignment = Alignment(vertical='top', wrap_text=name in ('name', 'sub', 'desc') or name.startswith('Feature'))
            c.border = border
            if name in ('price', 'was'):
                c.number_format = '0.00'
        ws.row_dimensions[r].height = 60

    last = 2 + len(products)
    dv_type = DataValidation(type='list', formula1='"single,double"', allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv_type)
    dv_type.add('%s3:%s%d' % (get_column_letter(_col(cols, 'type')), get_column_letter(_col(cols, 'type')), last + 20))

    dv_badge = DataValidation(type='list', formula1='"Featured,Best Seller,New,Sale,Premium"',
                              allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv_badge)
    dv_badge.add('%s3:%s%d' % (get_column_letter(_col(cols, 'badge')), get_column_letter(_col(cols, 'badge')), last + 20))

    # ---------------- specs
    ws2 = wb.create_sheet('specs')
    for j, (h, w) in enumerate((('key', 18), ('attribute', 30), ('value', 44)), start=1):
        c = ws2.cell(1, j, h)
        c.fill, c.font = head_fill, head_font
        ws2.column_dimensions[get_column_letter(j)].width = w
    ws2.freeze_panes = 'A2'
    r = 2
    for p in products:
        for k, v in (p.get('specs') or []):
            ws2.cell(r, 1, p['key']).border = border
            ws2.cell(r, 2, k).border = border
            ws2.cell(r, 3, v).border = border
            r += 1
    if r == 2:
        ws2.cell(2, 1, '# 还没有规格数据。格式：key | attribute | value，一款产品几行就写几行').font = note_font

    # ---------------- reviews
    ws3 = wb.create_sheet('reviews')
    heads = (('key', 18), ('rating', 8), ('title', 34), ('author', 18), ('date', 12), ('body', 80), ('helpful', 9))
    for j, (h, w) in enumerate(heads, start=1):
        c = ws3.cell(1, j, h)
        c.fill, c.font = head_fill, head_font
        ws3.column_dimensions[get_column_letter(j)].width = w
    ws3.freeze_panes = 'A2'
    r = 2
    for p in products:
        for rv in (p.get('reviews') or []):
            ws3.cell(r, 1, p['key']).border = border
            ws3.cell(r, 2, rv.get('rating')).border = border
            ws3.cell(r, 3, rv.get('title')).border = border
            ws3.cell(r, 4, rv.get('author')).border = border
            ws3.cell(r, 5, rv.get('date')).border = border
            cb = ws3.cell(r, 6, rv.get('body'))
            cb.border = border
            cb.alignment = Alignment(vertical='top', wrap_text=True)
            ws3.cell(r, 7, rv.get('helpful')).border = border
            r += 1

    # ---------------- 说明
    ws4 = wb.create_sheet('说明')
    ws4.column_dimensions['A'].width = 118
    for i, (text, bold) in enumerate(GUIDE, start=1):
        c = ws4.cell(i, 1, text)
        c.alignment = Alignment(vertical='top', wrap_text=False)
        c.font = Font(bold=True, size=11, color=INK) if bold else Font(size=10, color='FF3A3833')

    wb.save(OUT)
    print('wrote %s  (%d products, %d spec rows, %d review rows)'
          % (os.path.relpath(OUT, ROOT), len(products),
             sum(len(p.get('specs') or []) for p in products),
             sum(len(p.get('reviews') or []) for p in products)))
    return 0


def _col(cols, name):
    for j, (n, _w, _n) in enumerate(cols, start=1):
        if n == name:
            return j
    raise KeyError(name)


if __name__ == '__main__':
    sys.exit(main())
