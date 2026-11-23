#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发抓取 gallery 里的外链图片 -> images/details/<key>-<序号>.<后缀>
超过 300KB 的自动压到 300KB 以内（复用 build.py 的 shrink_image）。

优先向 CDN 要 JPEG（社交平台分享预览、部分老浏览器不认 AVIF），
所以 Accept 头不带 avif，比 build.py 里的串行抓取更适合一次导入几百张。

用法：
    python fetch_images.py            # 抓 data/products.json 里还没本地化的外链
    python fetch_images.py --force    # 连本地文件名也重新抓（按原 key-序号 覆盖）
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import build as B

DATA = os.path.join(ROOT, 'data', 'products.json')
IMG_DIR = os.path.join(ROOT, 'images', 'details')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0 Safari/537.36')
# 只要 JPEG/PNG：社交分享预览（og:image）和部分老浏览器不认 AVIF/WEBP
ACCEPT = 'image/jpeg,image/png;q=0.9,*/*;q=0.1'


def download(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': ACCEPT,
                                               'Accept-Language': 'en-US,en;q=0.9'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(B.MAX_BYTES + 1)
    if len(data) > B.MAX_BYTES:
        raise ValueError('超过 %d MB' % (B.MAX_BYTES // 1048576))
    ext = B.sniff_ext(data)
    if not ext:
        raise ValueError('不是图片（Content-Type: %s）' % r.headers.get('Content-Type'))
    return data, ext


def to_jpeg_if_needed(data, ext):
    """CDN 仍可能回 webp/avif；统一转成 JPEG，保证 og:image 在各平台都能显示"""
    if ext in ('jpg', 'png'):
        return data, ext
    if not B.HAVE_PIL:
        return data, ext
    try:
        import io
        im = B.Image.open(io.BytesIO(data))
        im.load()
        if getattr(im, 'n_frames', 1) > 1:
            return data, ext
        im = im.convert('RGB')
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=88, optimize=True, progressive=True)
        return buf.getvalue(), 'jpg'
    except Exception:
        return data, ext


def one(stem, url):
    for attempt in (1, 2):
        try:
            data, ext = download(url)
            data, ext = to_jpeg_if_needed(data, ext)
            data, ext = B.shrink_image(data, ext, stem)
            name = '%s.%s' % (stem, ext)
            with open(os.path.join(IMG_DIR, name), 'wb') as f:
                f.write(data)
            # 清掉同 stem 的其他后缀（之前可能存成 avif）
            for e in B.IMG_EXTS:
                p = os.path.join(IMG_DIR, '%s.%s' % (stem, e))
                if os.path.exists(p) and '%s.%s' % (stem, e) != name:
                    os.remove(p)
            return name, len(data), None
        except Exception as e:
            err = e
    return None, 0, err


def main():
    force = '--force' in sys.argv
    products = json.load(open(DATA, encoding='utf-8'))
    os.makedirs(IMG_DIR, exist_ok=True)

    jobs = []
    done = {}
    for p in products:
        for i, g in enumerate(p['gallery']):
            if not B.is_img_url(g):
                continue
            stem = '%s-%d' % (p['key'], i + 1)
            old_name, _ = B._existing_variants(stem)
            if old_name and not force:
                done[(p['key'], i)] = old_name      # 已经有这张图，直接复用
                continue
            jobs.append((p['key'], i, g))
    print('%d 张外链待抓（%d 张已有文件可复用）' % (len(jobs), len(done)))

    fail = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(one, '%s-%d' % (k, i + 1), u): (k, i) for k, i, u in jobs}
        for n, f in enumerate(as_completed(futs), 1):
            key, i = futs[f]
            name, size, err = f.result()
            if name:
                done[(key, i)] = name
                print('[%3d/%3d] %-24s %5.0f KB' % (n, len(jobs), name, size / 1024))
            else:
                fail.append((key, i, err))
                print('[%3d/%3d] FAIL %s-%d %s' % (n, len(jobs), key, i + 1, err))

    for p in products:
        g = [done.get((p['key'], i), v) for i, v in enumerate(p['gallery'])]
        p['gallery'] = g

    with open(DATA, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('ok %d 张，失败 %d 张' % (len(done), len(fail)))
    for key, i, err in fail:
        print('  ! %s-%d %s' % (key, i + 1, err))


if __name__ == '__main__':
    main()
