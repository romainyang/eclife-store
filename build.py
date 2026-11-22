#!/usr/bin/env python3
"""
Eclife 站点构建脚本
====================
唯一数据源（Excel 优先）:
  products.xlsx        —— 有它就先用 excel_to_products.py 转成 data/products.json
  data/products.json   —— 没有 xlsx 时直接用它

执行: python build.py              # 有 products.xlsx 就先转换
      python build.py --from-json  # 忽略 Excel，直接用 json

它会做三件事:
  1. 为每款产品生成 product/<key>/index.html
  2. 同步首页 index.html 里的 products 数组
  3. 重新生成 sitemap.xml
"""
import json
import os
import re
import html
import sys

SITE = 'https://yange.asia'
ROOT = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(ROOT, 'templates', 'product.html')
DATA = os.path.join(ROOT, 'data', 'products.json')
XLSX = os.path.join(ROOT, 'products.xlsx')


def sync_from_excel():
    """仓库根目录有 products.xlsx 时，以它为准重新生成 data/products.json"""
    if not os.path.exists(XLSX):
        return False
    sys.path.insert(0, ROOT)
    import excel_to_products
    try:
        excel_to_products.convert(XLSX, DATA)
    except excel_to_products.ExcelError as e:
        print('\n[build] products.xlsx 有问题，构建中止：\n%s\n' % e, file=sys.stderr)
        raise SystemExit(1)
    return True

STAR = '&#9733;' * 5


def star_html(stars):
    """4.5 及以下渲染 4 实心 1 空心，4.6 以上 5 实心"""
    n = max(1, min(5, int(round(float(stars)))))
    return '&#9733;' * n + '&#9734;' * (5 - n)


# 产品页脚本只用到这些字段，其余不必内嵌（减小体积）
PAGE_FIELDS = ('id', 'key', 'name', 'price', 'was', 'gallery')
INDEX_FIELDS = ('id', 'key', 'name', 'sub', 'size', 'type', 'price', 'was', 'badge',
                'stars', 'sw', 'gallery', 'features', 'desc', 'specs')


def slim(items, fields):
    return [{k: p[k] for k in fields if k in p} for p in items]


def slim_index(products):
    """首页用：全字段 + 评价总数 + 星级分布百分比 + 前 3 条评价
    （不内嵌全部评价，避免首页体积翻倍）"""
    out = []
    for p in products:
        d = {k: p[k] for k in INDEX_FIELDS if k in p}
        d['reviewCount'] = p.get('reviewCount') or 0
        d['ratingDist'] = [x[1] for x in (p.get('ratingDist') or [])]
        d['reviews'] = [{
            'stars': r.get('rating', p['stars']),
            'title': r['title'],
            'body': r['body'],
            'author': r['author'],
            'date': r['date'],
            'verified': True,
            'helpful': r.get('helpful') or 0,
        } for r in (p.get('reviews') or [])[:3]]
        out.append(d)
    return out


def esc(t, quote=True):
    return html.escape(str(t), quote=quote)


def money(v):
    return '$' + ('%.2f' % float(v))


# ---------------- 各区块渲染 ----------------

def render_thumbs(p):
    name = esc(p['name'])
    out = []
    for i, g in enumerate(p['gallery']):
        cls = 'detail-thumb active' if i == 0 else 'detail-thumb'
        out.append(
            '<img class="%s" src="../../images/details/%s.jpg" onclick="pickImg(%d)" '
            'alt="%s view %d">' % (cls, g, i, name, i + 1)
        )
    return ''.join(out)


def render_swatches(p):
    out = []
    for i, c in enumerate(p.get('sw') or ['#f4f1ea']):
        cls = 'detail-sw active' if i == 0 else 'detail-sw'
        out.append(
            '<span class="%s" style="background:%s" onclick="selectColor(%d)" title="%s"></span>'
            % (cls, c, i, c)
        )
    return ''.join(out)


def render_features(p):
    return ''.join('<li>%s</li>' % esc(f) for f in p.get('features', []))


def render_specs(p):
    specs = p.get('specs') or []
    if not specs:
        return ''
    rows = ''.join('<tr><th>%s</th><td>%s</td></tr>' % (esc(k), esc(v)) for k, v in specs)
    return ('<div class="spec-wrap"><div class="detail-label">Specifications</div>'
            '<table class="spec-table"><tbody>%s</tbody></table></div>' % rows)


def render_price(p):
    out = money(p['price']) + ' '
    if p.get('was'):
        out += '<span class="was">%s</span>' % money(p['was'])
    return out


def render_reviews(p):
    # 没有任何评价的产品，整块不渲染（避免出现 "Based on 0 verified reviews" 的空区块）
    if not p.get('reviews') and not p.get('reviewCount'):
        return ''
    dist = p.get('ratingDist') or []
    bars = ''.join(
        '<div class="dr-bar-row"><span class="lbl">%d star</span>'
        '<span class="dr-bar"><i style="width:%d%%"></i></span><span class="pct">%d%%</span></div>'
        % (5 - i, w, pct) for i, (w, pct) in enumerate(dist)
    )
    items = ''
    for r in p.get('reviews', []):
        helpful = ''
        if r.get('helpful'):
            helpful = ('<div class="dr-helpful">%d people found this helpful &nbsp;'
                       '<button type="button">Helpful</button></div>' % r['helpful'])
        items += (
            '<div class="dr-item"><div class="stars">%s'
            '<span class="verified">&#10003; Verified Purchase</span></div>'
            '<div class="dr-title">%s</div><div class="dr-body">%s</div>'
            '<div class="dr-by"><b>%s</b><span>%s</span></div>%s</div>'
            % (star_html(r.get('rating', p['stars'])), esc(r['title']), esc(r['body'], quote=False),
               esc(r['author']), esc(r['date']), helpful)
        )
    return (
        '<section class="d-reviews">\n'
        '      <div class="sec-head" style="text-align:left;margin:0 0 30px;">'
        '<div class="eyebrow">Customer Reviews</div><h2>What Our Customers Say</h2></div>\n'
        '      <div class="dr-overview">\n'
        '        <div class="dr-score"><div class="dr-bignum">%s</div>'
        '<div class="stars">%s<span>%s</span></div>'
        '<div class="based">Based on %d verified reviews</div></div>\n'
        '        <div class="dr-bars">%s</div>\n'
        '      </div>\n'
        '      <div class="dr-list">%s</div>\n'
        '    </section>'
        % ('%.1f' % float(p['stars']), star_html(p['stars']), '%.1f' % float(p['stars']), p.get('reviewCount', 0), bars, items)
    )


def render_related(p, products):
    """按顺序轮转取 4 款其他产品"""
    others = [q for q in products if q['key'] != p['key']]
    start = [q['key'] for q in products].index(p['key'])
    picks = [others[(start + i) % len(others)] for i in range(min(4, len(others)))]
    cards = ''
    for q in picks:
        cards += (
            '<div class="card"><a href="../%s/"><div class="card-img">'
            '<img src="../../images/details/%s.jpg" alt="%s" loading="lazy"></div></a>'
            '<a href="../%s/"><div class="card-info"><div class="card-title">%s</div>'
            '<div class="card-sub">%s</div><div class="price">%s</div></div></a></div>'
            % (q['key'], q['gallery'][0], esc(q['name']), q['key'], esc(q['name']),
               esc(q.get('sub', '')), money(q['price']))
        )
    return ('<div class="rel-sec"><div class="sec-head" style="text-align:left;margin:0 0 26px;">'
            '<div class="eyebrow">You May Also Like</div><h2>More Vanities</h2></div>'
            '<div class="rel-grid">%s</div></div>' % cards)


def render_page(p, products):
    tpl = open(TPL, encoding='utf-8').read()
    url = '%s/product/%s/' % (SITE, p['key'])
    og_img = '%s/images/details/%s.jpg' % (SITE, p['gallery'][0])

    repl = {
        '{{TITLE}}': esc('%s | Eclife Bathroom Vanities' % p['name']),
        '{{META_DESC}}': esc(p.get('desc', '')),
        '{{CANONICAL}}': url,
        '{{OG_TITLE}}': esc(p['name']),
        '{{OG_DESC}}': esc(p.get('desc', '')),
        '{{OG_IMAGE}}': og_img,
        '{{NAME}}': esc(p['name']),
        '{{SUB}}': esc(p.get('sub', '')),
        '{{BADGE}}': esc(p.get('badge') or 'Eclife Collection'),
        '{{STARS}}': star_html(p['stars']) + '<span>%.1f &middot; %d reviews</span>' % (float(p['stars']), p.get('reviewCount') or 0),
        '{{PRICE}}': render_price(p),
        '{{MAIN_IMG}}': '../../images/details/%s.jpg' % p['gallery'][0],
        '{{THUMBS}}': render_thumbs(p),
        '{{SWATCHES}}': render_swatches(p),
        '{{FEATURES}}': render_features(p),
        '{{DESC}}': esc(p.get('desc', '')),
        '{{SPECS_BLOCK}}': render_specs(p),
        '{{REVIEWS}}': render_reviews(p),
        '{{RELATED}}': render_related(p, products),
        '{{PRODUCTS_JSON}}': json.dumps(slim(products, PAGE_FIELDS), ensure_ascii=False, separators=(',', ':')),
        '{{PID}}': p['id'],
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    return tpl


def main():
    if '--from-json' not in sys.argv:
        sync_from_excel()
    products = json.load(open(DATA, encoding='utf-8'))
    keys = [p['key'] for p in products]
    assert len(keys) == len(set(keys)), 'key 有重复'

    # 1) 生成产品页
    for p in products:
        out_dir = os.path.join(ROOT, 'product', p['key'])
        os.makedirs(out_dir, exist_ok=True)
        open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8', newline='\n').write(
            render_page(p, products))

        # 检查图片是否存在
        missing = [g for g in p['gallery']
                   if not os.path.exists(os.path.join(ROOT, 'images', 'details', g + '.jpg'))]
        flag = '' if not missing else '  !! 缺图: ' + ','.join(missing)
        print('  page  %-14s %d imgs%s' % (p['key'], len(p['gallery']), flag))

    # 2) 同步首页 products 数组
    idx_path = os.path.join(ROOT, 'index.html')
    src = open(idx_path, encoding='utf-8').read()
    new_arr = 'const products = ' + json.dumps(slim_index(products), ensure_ascii=False, separators=(',', ':')) + ';'
    src2, n = re.subn(r'const products\s*=\s*\[.*?\];', new_arr, src, count=1, flags=re.S)
    assert n == 1, '首页 products 数组没找到'
    # 首页产品计数文案
    src2 = re.sub(r'>Showing \d+ products<', '>Showing %d products<' % len(products), src2)
    open(idx_path, 'w', encoding='utf-8', newline='\n').write(src2)
    print('  index.html: products array synced (%d)' % len(products))

    # 3) sitemap
    urls = [('%s/' % SITE, '1.0', 'daily')] + \
           [('%s/product/%s/' % (SITE, p['key']), '0.8', 'weekly') for p in products]
    body = ''.join(
        '  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n'
        '    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>\n'
        % (u, '2026-11-22', cf, pr) for u, pr, cf in urls
    )
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + '</urlset>\n'
    )
    print('  sitemap.xml: %d urls' % len(urls))
    print('done.')


if __name__ == '__main__':
    sys.exit(main())
