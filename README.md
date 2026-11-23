# Eclife 浴室柜独立站

纯静态电商站，正式域名 **https://yange.asia**

托管可选 **GitHub Pages**（推荐，改完推上去自动上线）或 **Cloudflare Pages**（手动传 zip）。

---

## 目录结构

```
eclife-store/
├─ index.html              首页（产品列表、品牌故事、购物车入口）
├─ products.xlsx           ★ 产品表（推荐改这个，上传即可自动上线）
│                            5 张表：products / images / specs / reviews / 说明
├─ new-product-template.xlsx  新品填写模板（与产品表结构完全一致，数据是 1 行示例）
├─ data/products.json      ★ 数据源：所有产品信息（Excel 会自动转换成它）
├─ excel_to_products.py    Excel → JSON 转换器（build.py 自动调用，合并 4 张数据表）
├─ make_products_xlsx.py   从 JSON 反向导出两个表格（两张表共用同一套结构）
├─ walmart_import.py       批量导入 Walmart 表格 → data/walmart_new.json（售价=平台价×1.8）
├─ merge_walmart.py        把 walmart_new.json 并入 products.xlsx / 生成 new-products-*.xlsx
├─ fetch_images.py         并发抓外链图片并压到 300KB 内（统一转 JPEG）
├─ templates/product.html  产品详情页模板（含占位符，一般不用改）
├─ build.py                ★ 构建脚本：抓图压缩 / 生成详情页 / 同步首页 / 更新 sitemap
├─ product/<key>/index.html  自动生成的产品详情页，不要手改
├─ images/details/         产品图片（jpg，建议 1400px 宽以内）
├─ 404.html               404 页
├─ favicon.svg            站点图标
├─ robots.txt / sitemap.xml   SEO 文件（sitemap 自动生成）
├─ CNAME                   GitHub Pages 自定义域名（内容：yange.asia）
├─ .nojekyll               告诉 GitHub Pages 不要用 Jekyll 处理
├─ .github/workflows/deploy-pages.yml   推送后自动构建并发布
├─ _headers               Cloudflare 缓存与安全响应头（GitHub 不识别）
├─ _redirects             Cloudflare 跳转规则（GitHub 不识别）
└─ pack.py                打包成可上传 Cloudflare 的 zip
```

> `product/` 下的页面和 `sitemap.xml` 都是 `build.py` 生成的，**直接改会被下次构建覆盖**。

---

## 改内容：两条路，选一条

### 路线 1（推荐）：改 `products.xlsx`

仓库根目录的 `products.xlsx` 一共有 5 张表：

- **products** —— 一行一款产品，填标题、价格、卖点
- **images** —— 一行一款产品的图片：`key | Image 1 … Image 15`，至少 5 张，Image 1 是主图
- **specs** —— 规格参数，长表：`key | attribute | value`
- **reviews** —— 客户评价，长表：`key | rating | title | author | date | body | helpful`
- **说明** —— 每列怎么填都写在里面

`new-product-template.xlsx` 和它的**表结构完全一致**（同一套表、同一套列、同一套说明），只是数据换成了一行示例 `bv390`，照着复制即可。

改完保存，**上传到 GitHub 覆盖旧文件**，剩下的全自动：

```
products.xlsx 上传 → Actions 运行 excel_to_products.py（products + images + specs + reviews 合并）
                    → 生成 data/products.json
                    → 下载 images 表里的外链图片，超过 300KB 自动压到 300KB 以内（自动回提交）
                    → build.py 重建所有详情页 → 发布
```

上传入口（收藏这几个链接）：

- 产品表：https://github.com/romainyang/eclife-store/upload/main
- 产品图：https://github.com/romainyang/eclife-store/upload/main/images/details
- 看构建进度：https://github.com/romainyang/eclife-store/actions

> **图片统一填在 `images` 表**，一行一款产品，第一列是 `key`：
> ① 本地文件名 `bv390-main`（先把图传到 `images/details/`）；
> ② 图片链接 `https://cdn.xxx.com/bv390-main.jpg` —— **不用自己传图**，构建时会自动下载进 `images/details/`，
> 存成 `<key>-序号.<后缀>`，页面改用仓库里的这张本地图。
> 两种可以在同一行混着填，空格子会被跳过、图片按顺序往前排。
> 链接必须是**图片直链**（浏览器打开就是一张图），网盘分享页、商品详情页抓不下来，
> 这种情况那张图会先退回直用外链，并在构建日志里给警告。
> 下载下来的图如果超过 300KB，会自动压到 300KB 以内：长边先缩到 1400px，再逐级降质量重编码，
> 日志里会写成 `zip bv390-1 1375 KB -> 207 KB (jpg q90, 宽 1400)`。

> 只要有 `products.xlsx`，它就是老大：每次构建都会覆盖 `data/products.json`。想改用 JSON 手改，先把这个文件从仓库删掉（或本地 `python build.py --from-json`）。
>
> Excel 写错了不会把站点搞坏：构建会直接失败并在 Actions 里用中文列出「第几行哪一列错了」，线上保持上一版。

### 路线 2（进阶）：直接改 `data/products.json`

适合批量替换、或想精确控制 JSON 字段。改完执行：

```bash
python build.py
```

就会重新生成全部详情页、同步首页产品列表、刷新 sitemap。

### 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `key` | ✅ | 网址标识，决定 `/product/<key>/`，只能用英文小写和连字符 |
| `id` | ✅ | 内部编号，如 `p13`，购物车用它关联，不能重复 |
| `name` | ✅ | 产品全名，会显示在标题、详情页、卡片 |
| `sub` | ✅ | 副标题，一行卖点摘要，用 `·` 分隔 |
| `size` / `type` | ✅ | 尺寸（如 `48`）与类型（`single` / `double`），用于首页筛选 |
| `price` | ✅ | 售价（数字，不带 $） |
| `was` | ⬜ | 划线原价，不填就不显示 |
| `badge` | ⬜ | 角标，如 `New` / `Sale` / `Best Seller`；留空显示 `Eclife Collection` |
| `stars` | ✅ | 评分，如 `4.7` |
| `sw` | ✅ | 色板颜色数组，如 `["#f4f1ea","#292722"]` |
| `gallery` | ✅ | 图片数组：本地文件名**或图片链接**，可混用；链接会被自动下载（>300KB 自动压缩）进 `images/details/`；第一张作主图。Excel 里对应 `images` 表 |
| `features` | ✅ | 卖点列表 |
| `desc` | ✅ | 详细介绍，同时用作 SEO 描述 |
| `specs` | ⬜ | 规格表，格式 `[["Height","33.5 in"], ...]`；不填则不显示规格区 |
| `reviewCount` | ⬜ | 评价数量（数字） |
| `ratingDist` | ⬜ | 星级分布 `[[75,75],[16,16],[5,5],[2,2],[2,2]]`，前一个是条形宽度、后一个是百分比 |
| `reviews` | ⬜ | 评价内容数组，见下 |

单条评价的格式：

```json
{
  "title": "Stunning centerpiece",
  "body": "\"This is the focal point of our renovation...\"",
  "author": "Olivia S.",
  "date": "Jun 2026",
  "helpful": 8,
  "rating": 5
}
```

`body` 里的引号用 `\"` 转义；`rating` 是这一条自己的星级（1–5）。

---

## 新增一款产品

### 方式 A：Excel 表（最快，手机上也能做完）

> 懒人版：先下载仓库根目录的 `new-product-template.xlsx`（结构和 `products.xlsx` 完全一致，数据是 1 行完整示例 + 下拉 + 填写说明），
> 照着把 `products` / `images` / `specs` / `reviews` 四张表的示例行改成你的产品，再整行复制到 `products.xlsx` 对应表的末尾即可。
> 模板本身不要上传，它只是格式样本。

1. **准备图片（二选一）**
   - 传图：https://github.com/romainyang/eclife-store/upload/main/images/details → 拖入 → Commit。
     命名 `bv999-1.jpg`、`bv999-2.jpg`（英文小写、数字、连字符；宽 1400px 以内）。
   - 不传图：直接拿图片直链（如 `https://cdn.xxx.com/bv999-1.jpg`），第 3 步填进 `images` 表，
     构建时会自动下载到 `images/details/`，超过 300KB 还会自动压缩，不用手动处理。
2. **填表**
   打开 `products.xlsx` → **products** 表最后一行往下加：

   ```
   key     bv999            ← 决定网址 /product/bv999/，只能用 a-z 0-9 连字符
   name    Eclife 30" Bathroom Vanity with Sink
   sub     Solid Wood · Soft-Close · Freestanding
   size    30               ← 首页按尺寸筛选靠它
   type    single           ← 有下拉：single / double
   price   529.99
   was     649.99           ← 不促销就留空
   badge   New              ← 有下拉，也可以留空
   stars   4.6
   sw      white            ← 可写 #f4f1ea，也可写 white / sage / oak
   Feature 1..6              ← 一行一条卖点
   desc    ...              ← 详情页正文 + SEO 描述
   ```

3. **加图片**
   切到 **images** 表，最后一行往下加：第一列填 `bv999`，后面 `Image 1` 起依次填
   `bv999-1`、`bv999-2`……（至少 5 张，最多 15 张，Image 1 是主图；文件名和图片链接可以混填）。
   规格去 **specs** 表加行（`bv999 | Height | 33.5 in`），评价去 **reviews** 表加行。
4. **上传覆盖** https://github.com/romainyang/eclife-store/upload/main → 拖入 `products.xlsx` → **Commit changes**（提示覆盖就确认）。
5. **等 1 分钟** https://github.com/romainyang/eclife-store/actions 变绿勾即上线，打开 `https://yange.asia/product/bv999/` 检查。

### 方式 B：全程在 GitHub 网页上改 JSON（不装 Excel 也能做）

1. **上传图片**
   打开 https://github.com/romainyang/eclife-store/tree/main/images/details → 右上 **Add file → Upload files** → 拖入图片 → **Commit changes**。
   命名规则：`bv999-1.jpg`、`bv999-2.jpg`（英文小写、数字、连字符，别用空格和中文）。
2. **改数据**
   打开 https://github.com/romainyang/eclife-store/blob/main/data/products.json → 点右上铅笔图标进入编辑。
   在数组最后一项后面补一个英文逗号 `,`，把下面的「产品块」粘进去改成你的内容 → **Commit changes**。
3. **等 1 分钟**
   打开 https://github.com/romainyang/eclife-store/actions ，会看到一次 `Build & deploy to GitHub Pages` 在跑，变绿勾即上线。
4. **访问新网址** `https://yange.asia/product/bv999/`

### 方式 C：本地改（发布前能预览）

```bash
cd C:/Users/romai/WorkBuddy/2026-11-17-19-59-27/eclife-store
# 1. 图片放进 images/details/
# 2. 编辑 data/products.json
python build.py                # 生成产品页 + 同步首页 + 更新 sitemap
python -m http.server 8080     # 浏览器打开 http://localhost:8080 预览
git add -A && git commit -m "add bv999" && git push
```

### 可直接复制的产品块

```json
{
  "id": "p13",
  "key": "bv999",
  "name": "Eclife 30\" Bathroom Vanity with Sink",
  "sub": "Solid Wood · Soft-Close · Freestanding",
  "size": "30",
  "type": "single",
  "price": 529.99,
  "was": 649.99,
  "badge": "New",
  "stars": 4.6,
  "sw": ["#f4f1ea"],
  "gallery": ["bv999-1", "bv999-2", "bv999-3"],
  "features": [
    "Solid wood frame: kiln-dried hardwood resists warping in humid bathrooms.",
    "Soft-close doors: adjustable hinges keep mornings quiet.",
    "Pre-drilled top: faucet and drain ready, installs in under an hour."
  ],
  "desc": "One or two paragraphs describing the vanity, its materials and who it suits.",
  "specs": [["Height", "33.5 in"], ["Width", "30 in"], ["Cabinet material", "Manufactured Wood"]],
  "reviewCount": 0,
  "ratingDist": [],
  "reviews": []
}
```

`was`（划线价）、`badge`（角标）、`specs`（规格表）、`reviews`（评价）都可以省略。没有评价时 `reviewCount` 写 `0`、`ratingDist` 和 `reviews` 留空数组，详情页会自动不渲染评价区。

### 提交前自查 5 点

- `key` 必须唯一，决定网址 `/product/<key>/`，只能英文小写、数字、连字符
- `id` 必须唯一，购物车靠它区分产品，重复会导致加购串产品
- `gallery`（JSON 字段）只写文件名，不带 `images/details/` 前缀、不带 `.jpg` 后缀，第一张是主图；Excel 里对应 `images` 表的 Image 1–15
- JSON 语法：最后一项后面**不能**有多余逗号，引号必须是英文 `"`
- 图片要先 commit，再改 JSON（或两者一起提交），否则构建时图片还不存在
- 用 Excel 的话：上面 5 条同样适用，另外别删第 2 行灰色说明行（程序会自动跳过它），也别改已有的 `id`

### 修改 / 删除已有产品

- **改文案、价格、图片**：直接改 `data/products.json` 对应字段。**不要改 `key`**——改了等于换了网址，之前分享出去的链接会 404
- **给已有产品加图**：上传图片后，在它的 `gallery` 数组里加文件名
- **删除产品**：从数组里删掉那一块（注意前后逗号），再手动删掉 GitHub 上的 `product/<key>/` 目录和图片。构建不会替你清理旧目录
- **改完都在 Actions 里确认变绿**，失败时点开看红色步骤的日志，八成是 JSON 逗号或引号写错了

---

## 本地预览

```bash
python build.py                # 先构建（有 products.xlsx 会自动从表格读数据）
python -m http.server 8080
```

浏览器打开 http://localhost:8080 （不要直接双击 index.html，相对路径会失效）

> 本机没装 openpyxl 时先 `python -m pip install openpyxl`；不想用它就 `python build.py --from-json` 直接读 JSON。

---

## 部署到 GitHub Pages（推荐）

仓库里已经有 `.github/workflows/deploy-pages.yml`，push 到 `main` 就会自动：跑 `build.py` → 把生成物提交回仓库 → 发布到 Pages。**在 GitHub 网页上改 `products.json` 也能自动上线**，不用碰本地命令。

首次配置（只做一次）：

1. 建一个空仓库（不要勾 README / gitignore），推到 GitHub
2. 仓库 **Settings → Pages → Source** 选 **GitHub Actions**
3. 首次 push 后等 Action 跑完，Pages 会自动为该域名签发 HTTPS 证书，然后在 Pages 页面勾上 **Enforce HTTPS**
4. 仓库必须是 **Public**（私有仓库用 Pages 需要付费的 GitHub Pro）

Cloudflare DNS 里把域名指向 GitHub（**记录必须设为 DNS only 灰云**，橙云会导致证书签发失败）：

| 类型 | 名称 | 内容 |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `你的用户名.github.io` |

> 从 Cloudflare Pages 迁过来时，先在新仓库 Settings → Pages 里填好 Custom domain `yange.asia`，再去 Cloudflare 改 DNS，避免中途域名无解析。
>
> **务必同时删掉 `AAAA` 记录**（如果有）。Cloudflare 开代理时会自动生成指向 `2606:4700::/32` 的 IPv6 记录；只删 A 记录不删 AAAA，支持 IPv6 的网络会继续连到 Cloudflare，表现就是 `There isn't a GitHub Pages site here` 的 404。用 `nslookup yange.asia` 检查是否还有 `2606:4700:` 开头的地址。
>
> `www` 不用单独做跳转：GitHub Pages 绑定自定义域后会自动把 `www` 301 到主域。

---

## 部署到 Cloudflare Pages（备选，手动传包）

```bash
python pack.py
```

生成 `../eclife-site.zip`，只含站点文件（不含 build.py、data、templates 等工具文件）。把它拖到 Cloudflare Pages 的 **Upload assets** 即可（注意不要点 Workers 的上传入口，那里只收 HTML/CSS/JS）。

Cloudflare 的「连接 Git」也能用，构建命令留空、输出目录填 `/`，因为生成好的 HTML 已经提交在仓库里。

---

## 注意

- 购物车和订单存在浏览器 localStorage，纯静态站无法跨设备同步
- 图片建议控制在 1400px 宽、200KB 以内
- 改完 `data/products.json` 忘了跑 `build.py`（或忘了 push 让 Action 跑），页面不会更新
- GitHub Pages 不识别 `_headers` 和 `_redirects`：图片缓存头、安全响应头、www 自动跳转会失效；需要这些就留在 Cloudflare
- GitHub Pages 免费额度：仓库建议 1GB 以内、每月约 100GB 流量、单文件 100MB（本站 9MB / 71 文件，余量很大）
- 国内访问 GitHub Pages 可能偏慢，客户主要在海外则影响不大
