#!/usr/bin/env python3
"""
Eclife 站点构建脚本
====================
唯一数据源（Excel 优先）:
  products.xlsx        —— 有它就先用 excel_to_products.py 转成 data/products.json
  data/products.json   —— 没有 xlsx 时直接用它

执行: python build.py              # 有 products.xlsx 就先转换
      python build.py --from-json  # 忽略 Excel，直接用 json
      python build.py --no-fetch    # 跳过外链图片抓取（离线时用）

它会做四件事:
  1. 图片外链 -> 下载进 images/details/，换成本地文件名；超过 300KB 自动压到 300KB 以内
  2. 为每款产品生成 product/<key>/index.html
  3. 同步首页 index.html 里的 products 数组
  4. 重新生成 sitemap.xml
"""
import json
import os
import re
import html
import sys
import urllib.request

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


# ---------------- 图片地址 ----------------
# gallery 里每一项既可以是本地文件名（bv390-main），也可以是完整外链
IMG_URL_RE = re.compile(r'^(?:https?:)?//', re.I)


def is_img_url(g):
    s = str(g or '').strip()
    return bool(IMG_URL_RE.match(s)) or s.lower().startswith('data:')


def img_src(g, prefix=''):
    """页面里用的 src：外链原样返回，本地文件名拼 images/details/<名字>"""
    g = str(g)
    return g if is_img_url(g) else prefix + 'images/details/' + local_file(g)


def img_abs(g):
    """og:image / 结构化数据要绝对地址"""
    g = str(g)
    if is_img_url(g):
        return 'https:' + g if g.startswith('//') else g
    return SITE + '/images/details/' + local_file(g)


# ---------------- 外链图片抓取 ----------------
# gallery 列可以直接写图片外链；构建时会自动下载存进 images/details/，
# 页面最终用仓库里的本地文件名（快、稳、不依赖别人的图床）。抓取失败才退回外链。
IMG_DIR = os.path.join(ROOT, 'images', 'details')
LOCAL_EXT_RE = re.compile(r'\.(jpe?g|png|webp|gif|avif)$', re.I)
IMG_EXTS = ('jpg', 'jpeg', 'png', 'webp', 'gif', 'avif')
UA = 'Mozilla/5.0 (compatible; EclifeSiteBuild/1.0)'
MAX_BYTES = 20 * 1024 * 1024


def local_file(g):
    """本地图片的实际文件名：没写后缀就按 .jpg"""
    g = str(g)
    return g if LOCAL_EXT_RE.search(g) else g + '.jpg'


def sniff_ext(data):
    """按文件头判断真实格式，避免把错误页 / 防盗链页面当图片存下来"""
    if data[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    if data[4:8] == b'ftyp' and data[8:12] in (b'avif', b'avis'):
        return 'avif'
    return None


def _download(url, timeout=25):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8,*/*;q=0.5',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = (r.headers.get('Content-Type') or '').lower()
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('文件超过 %d MB' % (MAX_BYTES // 1048576))
    ext = sniff_ext(data)
    if not ext:
        raise ValueError('返回的不是图片（Content-Type: %s，多半是网页或防盗链拦截）'
                         % (ctype or '未知'))
    return data, ext


def _existing_variants(stem):
    """同一个 key-序号 之前抓过什么后缀的文件，返回 (文件名, 路径)"""
    for ext in IMG_EXTS:
        name = '%s.%s' % (stem, ext)
        path = os.path.join(IMG_DIR, name)
        if os.path.exists(path):
            return name, path
    return None, None


# ---------------- 图片压缩 ----------------
# 从外链抓下来的图经常是 1-3MB 的原图，直接进仓库会把 repo 撑肥、页面也变慢。
# 超过 300KB 就自动压：先缩到最长边 1400px，再逐级降质量重编码，直到低于 300KB。
# 带透明的 PNG 尽量保留透明通道（必要时转 256 色），实在压不下去才铺白底转 JPEG。
MAX_IMG_BYTES = 300 * 1024
MAX_IMG_WIDTH = 1400

try:
    from PIL import Image, ImageOps
    HAVE_PIL = True
except ImportError:            # 本机没装也不影响构建，只是不压缩
    HAVE_PIL = False


def _encode(im, fmt, quality=None):
    """按指定格式编码成字节；JPEG 会自动把透明通道铺成白底"""
    import io
    buf = io.BytesIO()
    if fmt == 'JPEG':
        if im.mode != 'RGB':
            bg = Image.new('RGB', im.size, (255, 255, 255))
            mask = im.split()[-1] if im.mode in ('RGBA', 'LA') else None
            bg.paste(im, mask=mask)
            im = bg
        im.save(buf, 'JPEG', quality=quality, optimize=True, progressive=True)
    elif fmt == 'WEBP':
        im.save(buf, 'WEBP', quality=quality, method=4)
    else:
        im.save(buf, 'PNG', optimize=True, compress_level=9)
    return buf.getvalue()


def shrink_image(data, ext, label=''):
    """超过 300KB 的图片压到 300KB 以内，返回 (bytes, 新后缀)"""
    if len(data) <= MAX_IMG_BYTES:
        return data, ext
    if not HAVE_PIL:
        print('  warn  %-18s %.0f KB 超过 300KB，但没装 Pillow，跳过压缩'
              % (label, len(data) / 1024))
        return data, ext

    import io
    try:
        src = Image.open(io.BytesIO(data))
        src.load()
        if getattr(src, 'n_frames', 1) > 1:
            print('  warn  %-18s 是动图，跳过压缩（%.0f KB）' % (label, len(data) / 1024))
            return data, ext
    except Exception as e:
        print('  warn  %-18s 无法解码（%s），跳过压缩' % (label, e))
        return data, ext

    src = ImageOps.exif_transpose(src)      # 先按 EXIF 摆正，顺带丢掉元数据
    has_alpha = src.mode in ('RGBA', 'LA') or (src.mode == 'P' and 'transparency' in src.info)
    src = src.convert('RGBA' if has_alpha else 'RGB')

    # 优先保留原格式特性：带透明的 png 先试 png / webp，其余直接走 jpeg
    if ext == 'png' and has_alpha:
        plans = ['PNG', 'WEBP', 'JPEG']
    elif ext == 'webp':
        plans = ['WEBP', 'JPEG']
    else:
        plans = ['JPEG']
    exts = {'PNG': 'png', 'WEBP': 'webp', 'JPEG': 'jpg'}
    qualities = (90, 86, 82, 78, 74, 70, 64, 58)

    best_size, best_blob, best_ext = len(data), data, ext

    for max_w in (MAX_IMG_WIDTH, 1200, 1000):
        cur = src.copy()
        if cur.width > max_w:
            cur.thumbnail((max_w, 100000), Image.LANCZOS)
        for fmt in plans:
            cands = []
            if fmt == 'PNG':
                cands.append(('PNG', None, _encode(cur, 'PNG')))
                try:
                    cands.append(('PNG', '256色', _encode(
                        cur.quantize(colors=256, method=Image.FASTOCTREE), 'PNG')))
                except Exception:
                    pass
            else:
                cands = [(exts[fmt], 'q%d' % q, _encode(cur, fmt, q)) for q in qualities]
            for newext, tag, blob in cands:
                if len(blob) <= MAX_IMG_BYTES:
                    lost = '，透明通道已丢失' if (has_alpha and newext == 'jpg') else ''
                    print('  zip   %-18s %.0f KB -> %.0f KB (%s%s, 宽 %d%s)'
                          % (label, len(data) / 1024, len(blob) / 1024,
                             newext, ' ' + tag if tag else '', cur.width, lost))
                    return blob, newext
                if len(blob) < best_size:
                    best_size, best_blob, best_ext = len(blob), blob, newext

    print('  warn  %-18s 压到极限还有 %.0f KB（已缩到 1000px），先按这个用'
          % (label, best_size / 1024))
    return best_blob, best_ext


def fetch_remote_images(products):
    """把 gallery 里的外链下载到 images/details/<key>-<序号>.<后缀>

    返回 True 表示某款产品的 gallery 被改成了本地文件名（需要回写 json）。
    """
    total = sum(1 for p in products for g in p['gallery'] if is_img_url(g))
    if not total:
        return False
    os.makedirs(IMG_DIR, exist_ok=True)
    print('  fetch: %d 张外链图片 -> images/details/' % total)
    changed = False
    for p in products:
        before = list(p['gallery'])
        gallery = []
        for i, g in enumerate(before):
            if not is_img_url(g):
                gallery.append(g)
                continue
            stem = '%s-%d' % (p['key'], i + 1)
            old_name, old_path = _existing_variants(stem)
            url = 'https:' + g.lstrip('/') if g.startswith('//') else g
            try:
                data, ext = _download(url)
            except Exception as e:
                if old_name:
                    print('  warn  %-18s 抓取失败（%s），沿用已有文件' % (stem, e))
                    gallery.append(old_name)
                else:
                    print('  warn  %-18s 抓取失败（%s），这张先用外链顶着' % (stem, e))
                    gallery.append(g)
                continue
            data, ext = shrink_image(data, ext, stem)     # 超过 300KB 自动压
            name = '%s.%s' % (stem, ext)
            dest = os.path.join(IMG_DIR, name)
            same = os.path.exists(dest) and open(dest, 'rb').read() == data
            if not same:
                open(dest, 'wb').write(data)
                print('  img   %-18s <- %s (%.0f KB)' % (name, url, len(data) / 1024))
            if old_path and old_name != name:
                try:
                    os.remove(old_path)
                    print('  img   %-18s 格式变了，删掉旧的 %s' % (stem, old_name))
                except OSError:
                    pass
            gallery.append(name)
        if gallery != before:
            p['gallery'] = gallery
            changed = True
    return changed


def money(v):
    return '$' + ('%.2f' % float(v))


# ---------------- 各区块渲染 ----------------

def render_thumbs(p):
    name = esc(p['name'])
    out = []
    for i, g in enumerate(p['gallery']):
        cls = 'detail-thumb active' if i == 0 else 'detail-thumb'
        out.append(
            '<img class="%s" src="%s" onclick="pickImg(%d)" '
            'alt="%s view %d">' % (cls, img_src(g, '../../'), i, name, i + 1)
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
            '<img src="%s" alt="%s" loading="lazy"></div></a>'
            '<a href="../%s/"><div class="card-info"><div class="card-title">%s</div>'
            '<div class="card-sub">%s</div><div class="price">%s</div></div></a></div>'
            % (q['key'], img_src(q['gallery'][0], '../../'), esc(q['name']), q['key'], esc(q['name']),
               esc(q.get('sub', '')), money(q['price']))
        )
    return ('<div class="rel-sec"><div class="sec-head" style="text-align:left;margin:0 0 26px;">'
            '<div class="eyebrow">You May Also Like</div><h2>More Vanities</h2></div>'
            '<div class="rel-grid">%s</div></div>' % cards)


def render_page(p, products):
    tpl = open(TPL, encoding='utf-8').read()
    url = '%s/product/%s/' % (SITE, p['key'])
    og_img = img_abs(p['gallery'][0])

    raw_desc = p.get('desc', '')
    # Walmart 的描述是分段的，单行 <p> 里换行会丢；双换行转成新段落
    desc_html = (esc(raw_desc, quote=False)
                 .replace('\n\n', '</p><p class="detail-desc">')
                 .replace('\n', ' '))
    desc_meta = re.sub(r'\s+', ' ', raw_desc).strip()

    repl = {
        '{{TITLE}}': esc('%s | Eclife Bathroom Vanities' % p['name']),
        '{{META_DESC}}': esc(desc_meta[:300]),
        '{{CANONICAL}}': url,
        '{{OG_TITLE}}': esc(p['name']),
        '{{OG_DESC}}': esc(desc_meta[:200]),
        '{{OG_IMAGE}}': og_img,
        '{{NAME}}': esc(p['name']),
        '{{SUB}}': esc(p.get('sub', '')),
        '{{BADGE}}': esc(p.get('badge') or 'Eclife Collection'),
        '{{STARS}}': (star_html(p['stars']) + '<span>%.1f &middot; %d reviews</span>'
                      % (float(p['stars']), p.get('reviewCount') or 0)) if p.get('reviewCount')
                     else '<span>New arrival &middot; Eclife collection</span>',
        '{{PRICE}}': render_price(p),
        '{{MAIN_IMG}}': img_src(p['gallery'][0], '../../'),
        '{{THUMBS}}': render_thumbs(p),
        '{{SWATCHES}}': render_swatches(p),
        '{{FEATURES}}': render_features(p),
        '{{DESC}}': desc_html,
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

    # 0) gallery 里的外链 -> 下载进 images/details/，并换成本地文件名
    if '--no-fetch' not in sys.argv and fetch_remote_images(products):
        with open(DATA, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
            f.write('\n')
        print('  data/products.json: 外链已换成本地文件名')

    # 1) 生成产品页
    for p in products:
        out_dir = os.path.join(ROOT, 'product', p['key'])
        os.makedirs(out_dir, exist_ok=True)
        open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8', newline='\n').write(
            render_page(p, products))

        # 检查图片是否存在（外链跳过，抓取失败时才会留外链）
        missing = [g for g in p['gallery']
                   if not is_img_url(g)
                   and not os.path.exists(os.path.join(IMG_DIR, local_file(g)))]
        flag = '' if not missing else '  !! 缺图: ' + ','.join(missing)
        print('  page  %-14s %d imgs%s' % (p['key'], len(p['gallery']), flag))

    # 2) 同步首页 products 数组
    idx_path = os.path.join(ROOT, 'index.html')
    src = open(idx_path, encoding='utf-8').read()
    new_arr = 'const products = ' + json.dumps(slim_index(products), ensure_ascii=False, separators=(',', ':')) + ';'
    src2, n = re.subn(r'const products\s*=\s*\[.*?\];', lambda m: new_arr, src, count=1, flags=re.S)
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
