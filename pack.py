#!/usr/bin/env python3
"""把站点打包成可上传 Cloudflare Pages 的 zip（不含构建工具与数据源）"""
import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(ROOT), 'eclife-site.zip')

EXCLUDE_DIRS = {'.git', '.github', 'data', 'templates', '__pycache__', '.wrangler', '_site'}
EXCLUDE_FILES = {'build.py', 'pack.py', 'README.md', '.gitignore', '.gitattributes',
                 '_p.js', '_products_new.json'}


def main():
    count = 0
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if f in EXCLUDE_FILES:
                    continue
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, ROOT))
                count += 1
    size = os.path.getsize(OUT) / 1048576
    print('%d files -> %s (%.2f MB)' % (count, OUT, size))

    # 快速自检
    with zipfile.ZipFile(OUT) as z:
        names = z.namelist()
        for need in ('index.html', '_redirects', '_headers', '404.html', 'sitemap.xml'):
            print('  %-12s %s' % (need, 'OK' if need in names else 'MISSING'))
        print('  product pages:', len([n for n in names if n.startswith('product/')]))


if __name__ == '__main__':
    main()
