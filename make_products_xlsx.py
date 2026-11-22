#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 Excel 产品表 —— products.xlsx 与 new-product-template.xlsx 共用同一套结构
=============================================================================
两个文件的表、列、样式、说明完全一致，唯一区别是数据：
    products.xlsx             —— 站点真实产品（从 data/products.json 导出）
    new-product-template.xlsx —— 一行示例产品（bv390），照着填

用法：
    python make_products_xlsx.py             # 两个文件都生成
    python make_products_xlsx.py --products   # 只生成 products.xlsx
    python make_products_xlsx.py --template   # 只生成模板

五张表：products / images / specs / reviews / 说明
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data', 'products.json')
OUT_PRODUCTS = os.path.join(ROOT, 'products.xlsx')
OUT_TEMPLATE = os.path.join(ROOT, 'new-product-template.xlsx')

INK = 'FF292722'
GREY = 'FF6B675F'
NOTE = 'FF8A8378'
SAMPLE_FILL = 'FFFBF7E8'

IMAGES_MAX = 15
IMAGES_MIN = 5
FEATURE_COLS = 6

PRODUCT_COLS = [
    ('key', 18, '必填 · 网址标识（小写字母/数字/连字符），发布后别改'),
    ('name', 46, '必填 · 产品标题'),
    ('sub', 34, '副标题：颜色 · 款式 · 台面 · 高度'),
    ('size', 7, '尺寸数字，如 30 / 48 / 60'),
    ('type', 9, 'single / double（有下拉）'),
    ('price', 10, '必填 · 售价，只填数字'),
    ('was', 10, '原价/划线价，不促销留空'),
    ('badge', 13, 'Featured / Best Seller / New / Sale / Premium（有下拉）'),
    ('stars', 8, '评分 0-5，如 4.9'),
    ('reviewCount', 11, '评价总数，留空=按 reviews 表条数算'),
    ('sw', 22, '色块颜色，逗号分隔；可写 #8a9c8b 或 white / sage / oak'),
]
TAIL_COLS = [
    ('desc', 70, '长描述（详情页正文 + SEO 描述），建议 300-600 字符'),
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
    ('Actions 会自动重建所有页面，1-2 分钟后上线。', False),
    ('', False),
    ('本文件共五张表：products（产品）/ images（图片）/ specs（规格）/ reviews（评价）/ 说明', True),
    ('new-product-template.xlsx 的表格结构与这个文件完全一致，只是数据换成了一行示例，可以照着填。', False),
    ('', False),
    ('一、products 表 —— 一行一款产品', True),
    ('第 1 行是表头，第 2 行灰色 # 开头的是说明行（程序自动跳过），第 3 行开始填数据。', False),
    ('行的顺序 = 首页展示顺序，想置顶就往上挪一行。', False),
    ('', False),
    ('key         必填。小写字母/数字/连字符，决定产品网址：/product/<key>/。一旦发布不要再改，改了旧链接会 404。', False),
    ('name        必填。产品标题，显示在卡片、详情页标题和搜索引擎结果里。', False),
    ('sub         副标题。建议「Sage Green · Freestanding · 33.5" H」这种结构。', False),
    ('size        尺寸数字（18/24/30/48/60/72）。填数字即可，程序会转成文本；首页按尺寸筛选靠它。', False),
    ('type        只能是 single 或 double（单盆/双盆），单元格有下拉。', False),
    ('price       必填。售价，只填数字（999.99），带 $ 也能识别。', False),
    ('was         原价/划线价。不促销就留空；填了之后首页会多一个 Sale 筛选命中。', False),
    ('badge       角标，留空不显示。常用 Featured / Best Seller / New / Sale / Premium（有下拉）。', False),
    ('stars       评分 0-5，可写 4.9。星级图标按四舍五入取整显示。', False),
    ('reviewCount 评价总数，用于显示 "Based on N verified reviews"。留空则按 reviews 表实际条数算。', False),
    ('sw          色块颜色，可写 #8a9c8b，也可写 white / black / sage / oak / gold 等色名，多个用逗号分隔。', False),
    ('Feature 1-6 五点卖点，一行一条，格式建议「小标题：正文」。用不到的留空，也可以自己加 Feature 7、8 列。', False),
    ('desc        长描述，作为详情页正文和搜索引擎描述。', False),
    ('dist5-1     评价星级分布百分比，五个加起来 100。全部留空则默认 75/16/5/2/2。', False),
    ('id          内部编号，购物车靠它区分商品。新行留空自动生成，已有行不要改。', False),
    ('', False),
    ('二、images 表 —— 图片（一行一款产品）', True),
    ('第一列是 key，后面 Image 1 到 Image 15。一行一款产品，按 key 和 products 表对应，顺序无所谓。', False),
    ('Image 1 是主图（列表卡片、详情页首图、分享预览图都用它），建议至少填 5 张，最多 15 张。', False),
    ('每格填一样东西，两种写法可以混用：', False),
    ('   ① 本地文件名：bv390-main（图要先传到 images/details/；不写后缀按 .jpg 处理）', False),
    ('   ② 图片外链：https://cdn.xxx.com/bv390-main.jpg', False),
    ('填外链不用自己传图：构建时会自动下载到 images/details/，存成 <key>-序号.<后缀>，页面改用仓库里这张图。', False),
    ('外链必须是图片直链（浏览器打开直接是图）；网盘分享页、商品详情页抓不下来，会退回直用外链并给警告。', False),
    ('下载的图超过 300KB 会自动压缩到 300KB 以内：长边超过 1400px 先缩到 1400px，再逐级降质量重编码；', False),
    ('PNG 带透明会保留透明通道（必要时转 256 色），实在压不下去才转 JPEG。压缩在构建日志里会写成 412KB->248KB。', False),
    ('中间空着的格子会被跳过，图片会按顺序往前排，所以不必填满 15 格。', False),
    ('', False),
    ('三、specs 表 —— 规格参数（长表）', True),
    ('key | attribute | value。一款产品几行就写几行，写的顺序就是页面上的显示顺序。', False),
    ('key 必须和 products 表一致，对不上会报错；没有规格的产品整行不写即可。', False),
    ('', False),
    ('四、reviews 表 —— 客户评价（长表）', True),
    ('key | rating | title | author | date | body | helpful。', False),
    ('rating 填 1-5（这条评价自己的星级）；date 随便写如 Aug 2026；helpful 是有多少人觉得有用，可留空。', False),
    ('一款产品一条评价都没有时，详情页不会显示评价区（刻意如此，避免出现 Based on 0 reviews）。', False),
    ('', False),
    ('五、新增一款产品的完整流程', True),
    ('1. 准备图片：外链直接贴到 images 表；本地图先压到 1400px 宽、300KB 以内，传到 images/details/。', False),
    ('2. products 表最后加一行，填 key / name / price / size / type / sw / 卖点 / desc。', False),
    ('3. images 表加一行，第一列填同一个 key，Image 1 开始往后填图片（至少 5 张）。', False),
    ('4. 需要的话在 specs、reviews 表里补上这个 key 对应的行。', False),
    ('5. 保存成 .xlsx，拖到 https://github.com/romainyang/eclife-store/upload/main 覆盖。', False),
    ('6. 等 Actions 转绿，打开 https://yange.asia/product/<key>/ 检查，再去首页看卡片。', False),
    ('', False),
    ('六、常见报错', True),
    ('「key 不合法」—— 用了大写、空格或中文。只能 a-z、0-9、连字符。', False),
    ('「key 重复」—— 同一个 key 写了两行（products 或 images 表里都可能）。', False),
    ('「price 不是数字」—— 混进了字母或者用了中文标点。', False),
    ('「没有图片」—— images 表里没有这个 key 的行，或 Image 1-15 全空。', False),
    ('「只有 3 张图，建议至少 5 张」—— 只是提醒，不中断构建。', False),
    ('「缺图片文件」—— 只是警告不中断，但页面上那张图会是裂的，记得补图。', False),
]

# 模板里的示例产品（照着填就行，key 用 bv390）
SAMPLE_PRODUCT = {
    'key': 'bv390',
    'name': 'Eclife 30" Bathroom Vanity with Sink, Single Sink Freestanding Cabinet with Soft-Close Door, White',
    'sub': 'White · Freestanding · Integrated Sink Top · 33.5" H',
    'size': 30,
    'type': 'single',
    'price': 549.99,
    'was': 699,
    'badge': 'New',
    'stars': 4.9,
    'sw': ['#f4f1ea'],
    'features': [
        'Integrated Sink Top: Ceramic basin and countertop come as one piece, '
        'no sealing or aligning required.',
        'Soft-Close Door: The single door closes silently and stays shut, rated for 50,000 cycles.',
        'Real Storage: One adjustable shelf splits the cabinet so tall bottles and folded towels both fit.',
        'Moisture-Resistant Finish: Multi-layer protective coating resists steam and daily splashes.',
        'Ready in 30 Minutes: Pre-drilled faucet holes and adjustable levelers, no power tools needed.',
    ],
    'desc': 'A compact 30-inch vanity that fits small bathrooms without giving up storage. The integrated '
            'ceramic top wipes clean in one pass, the soft-close door keeps early mornings quiet, and the '
            'white finish matches most tile and hardware schemes. Ships in one box, assembles in about half '
            'an hour.',
    'gallery': ['bv390-1', 'bv390-2', 'bv390-3', 'bv390-4', 'bv390-5', 'bv390-6'],
    'specs': [
        ['Overall Height', '33.5 in'],
        ['Overall Width', '30 in'],
        ['Overall Depth', '18.1 in'],
        ['Cabinet Material', 'Solid wood frame with MDF panels'],
        ['Countertop', 'Integrated ceramic, pre-drilled for 4 in centerset faucet'],
        ['Sink Type', 'Single basin, undermount'],
        ['Mount Type', 'Freestanding'],
        ['Number of Doors', 1],
        ['Number of Shelves', 1],
        ['Assembly', 'Required, about 30 minutes'],
    ],
    'ratingDist': [[80, 80], [20, 20], [0, 0], [0, 0], [0, 0]],
    'reviews': [
        {'rating': 5, 'title': 'Fits a small bath perfectly', 'author': 'Dana R.', 'date': 'Oct 2026',
         'body': 'Our bathroom is 5x7 and this was the only 30-inch I could find with a real shelf inside. '
                 'The door closes with a soft click instead of a slam, which matters at 6am.',
         'helpful': 14},
        {'rating': 5, 'title': 'Top arrived in one piece', 'author': 'Miguel A.', 'date': 'Sep 2026',
         'body': 'I was worried about a ceramic top shipping, but it was double boxed and the sink and '
                 'counter are genuinely one piece. Nothing to caulk, no gaps.', 'helpful': 9},
        {'rating': 4, 'title': 'Good buy, faucet not included', 'author': 'K. Whitfield', 'date': 'Aug 2026',
         'body': 'Solid build and the white is a true white, not cream. Only note: no faucet in the box and '
                 'the instructions are mostly pictures, so budget for both.', 'helpful': 5},
        {'rating': 5, 'title': 'Finish has held up well', 'author': 'Priya S.', 'date': 'Jul 2026',
         'body': 'Four months of daily use with two kids and the white finish still wipes clean. No swelling '
                 'around the door edge, which is what killed our last vanity.', 'helpful': 7},
        {'rating': 5, 'title': 'Shelf height is adjustable', 'author': 'Tom B.', 'date': 'Jun 2026',
         'body': 'Moved the shelf down one notch and a 32oz shampoo bottle stands upright. Small thing, but '
                 'it means the cabinet actually works for us.', 'helpful': 3},
    ],
}


def _col_index(cols, name):
    for j, (n, _w, _hint) in enumerate(cols, start=1):
        if n == name:
            return j
    raise KeyError(name)


def build(products, out, template=False, nfeat=None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    head_fill = PatternFill('solid', fgColor=INK)
    head_font = Font(color='FFFFFFFF', bold=True, size=10)
    note_font = Font(color=NOTE, size=9, italic=True)
    sample_fill = PatternFill('solid', fgColor=SAMPLE_FILL)
    thin = Side(style='thin', color='FFDDD8CE')
    border = Border(bottom=thin)

    if nfeat is None:
        nfeat = max([len(p.get('features') or []) for p in products] + [FEATURE_COLS])
    nfeat = max(FEATURE_COLS, min(nfeat, 10))

    wb = Workbook()

    # ------------------------------------------------ products
    ws = wb.active
    ws.title = 'products'
    cols = (list(PRODUCT_COLS)
            + [('Feature %d' % i, 52, '卖点 %d，格式「小标题：正文」' % i) for i in range(1, nfeat + 1)]
            + list(TAIL_COLS))

    for j, (name, width, hint) in enumerate(cols, start=1):
        c = ws.cell(1, j, name)
        c.fill, c.font = head_fill, head_font
        c.alignment = Alignment(horizontal='center', vertical='center')
        ws.column_dimensions[get_column_letter(j)].width = width
        note = ws.cell(2, j, '# ' + hint)
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
            'desc': p.get('desc', ''),
            'id': p.get('id'),
        }
        dist = p.get('ratingDist') or []
        for k, name in enumerate(('dist5', 'dist4', 'dist3', 'dist2', 'dist1')):
            vals[name] = dist[k][0] if k < len(dist) else None
        for k, f in enumerate(p.get('features') or [], start=1):
            vals['Feature %d' % k] = f

        for j, (name, _w, _hint) in enumerate(cols, start=1):
            c = ws.cell(r, j, vals.get(name))
            c.alignment = Alignment(vertical='top',
                                    wrap_text=name in ('name', 'sub', 'desc') or name.startswith('Feature'))
            c.border = border
            if name in ('price', 'was'):
                c.number_format = '0.00'
            if template:
                c.fill = sample_fill
        ws.row_dimensions[r].height = 60 if not template else 150

    last = 2 + max(len(products), 1) + 20
    for col_name, formula in (('type', '"single,double"'),
                              ('badge', '"Featured,Best Seller,New,Sale,Premium"')):
        dv = DataValidation(type='list', formula1=formula, allow_blank=True, showDropDown=False)
        ws.add_data_validation(dv)
        j = get_column_letter(_col_index(cols, col_name))
        dv.add('%s3:%s%d' % (j, j, last))

    # ------------------------------------------------ images
    ws_img = wb.create_sheet('images')
    head = [('key', 18)] + [('Image %d' % i, 22) for i in range(1, IMAGES_MAX + 1)]
    for j, (h, w) in enumerate(head, start=1):
        c = ws_img.cell(1, j, h)
        c.fill, c.font = head_fill, head_font
        c.alignment = Alignment(horizontal='center', vertical='center')
        ws_img.column_dimensions[get_column_letter(j)].width = w
    ws_img.row_dimensions[1].height = 26

    img_notes = ['# 与 products 表的 key 一致', '# 主图', '# 侧面', '# 打开内部', '# 细节', '# 尺寸标注']
    for j, text in enumerate(img_notes, start=1):
        c = ws_img.cell(2, j, text)
        c.font = note_font
        c.alignment = Alignment(vertical='center')
    ws_img.freeze_panes = 'B3'

    for i, p in enumerate(products):
        r = 3 + i
        c = ws_img.cell(r, 1, p['key'])
        c.border = border
        c.font = Font(bold=True, size=10, color=INK)
        for k, g in enumerate((p.get('gallery') or [])[:IMAGES_MAX]):
            cc = ws_img.cell(r, 2 + k, g)
            cc.border = border
            cc.alignment = Alignment(vertical='top')
            if template:
                cc.fill = sample_fill
        ws_img.row_dimensions[r].height = 30

    # ------------------------------------------------ specs
    ws2 = wb.create_sheet('specs')
    for j, (h, w) in enumerate((('key', 18), ('attribute', 30), ('value', 44)), start=1):
        c = ws2.cell(1, j, h)
        c.fill, c.font = head_fill, head_font
        ws2.column_dimensions[get_column_letter(j)].width = w
    ws2.freeze_panes = 'A2'
    r = 2
    for p in products:
        for k, v in (p.get('specs') or []):
            for j, x in enumerate((p['key'], k, v), start=1):
                cc = ws2.cell(r, j, x)
                cc.border = border
                if template:
                    cc.fill = sample_fill
            r += 1
    if r == 2:
        ws2.cell(2, 1, '# 还没有规格数据。格式：key | attribute | value，一款产品几行就写几行').font = note_font

    # ------------------------------------------------ reviews
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
            row = (p['key'], rv.get('rating'), rv.get('title'), rv.get('author'),
                   rv.get('date'), rv.get('body'), rv.get('helpful'))
            for j, x in enumerate(row, start=1):
                cc = ws3.cell(r, j, x)
                cc.border = border
                if j == 6:
                    cc.alignment = Alignment(vertical='top', wrap_text=True)
                if template:
                    cc.fill = sample_fill
            r += 1

    # ------------------------------------------------ 说明
    ws4 = wb.create_sheet('说明')
    ws4.column_dimensions['A'].width = 118
    for i, (text, bold) in enumerate(GUIDE, start=1):
        c = ws4.cell(i, 1, text)
        c.alignment = Alignment(vertical='top', wrap_text=False)
        c.font = Font(bold=True, size=11, color=INK) if bold else Font(size=10, color='FF3A3833')

    wb.save(out)
    return wb


def _load_products():
    products = json.load(open(DATA, encoding='utf-8'))
    for p in products:
        g = p.get('gallery') or []
        if len(g) > IMAGES_MAX:
            print('  ! %s 有 %d 张图，images 表只能放 %d 列，多出的 %d 张没写进表格'
                  % (p['key'], len(g), IMAGES_MAX, len(g) - IMAGES_MAX))
    return products


def main(argv):
    do_products = '--template' not in argv
    do_template = '--products' not in argv

    # 卖点列数按真实数据算，两个文件共用同一个值，保证结构一致
    nfeat = FEATURE_COLS
    products = []
    if os.path.exists(DATA):
        products = _load_products()
        nfeat = max([len(p.get('features') or []) for p in products] + [FEATURE_COLS])

    if do_products:
        build(products, OUT_PRODUCTS, nfeat=nfeat)
        print('wrote %s  (%d products, %d spec rows, %d review rows)'
              % (os.path.relpath(OUT_PRODUCTS, ROOT), len(products),
                 sum(len(p.get('specs') or []) for p in products),
                 sum(len(p.get('reviews') or []) for p in products)))

    if do_template:
        build([SAMPLE_PRODUCT], OUT_TEMPLATE, template=True, nfeat=nfeat)
        print('wrote %s  (示例产品 %s)' % (os.path.relpath(OUT_TEMPLATE, ROOT), SAMPLE_PRODUCT['key']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
