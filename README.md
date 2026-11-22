# Eclife 浴室柜独立站

纯静态电商站，正式域名 **https://yange.asia**

托管可选 **GitHub Pages**（推荐，改完推上去自动上线）或 **Cloudflare Pages**（手动传 zip）。

---

## 目录结构

```
eclife-store/
├─ index.html              首页（产品列表、品牌故事、购物车入口）
├─ data/products.json      ★ 唯一数据源：所有产品信息都写在这里
├─ templates/product.html  产品详情页模板（含占位符，一般不用改）
├─ build.py                ★ 构建脚本：生成详情页 / 同步首页 / 更新 sitemap
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

## 改内容：只动一个文件

所有产品信息都在 `data/products.json`，改完执行：

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
| `gallery` | ✅ | 图片文件名数组（不含路径和 `.jpg`），第一张作主图 |
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

### 方式 A：全程在 GitHub 网页上做（不用命令行）

1. **上传图片**
   打开 https://github.com/romainyang/eclife-store/tree/main/images/details → 右上 **Add file → Upload files** → 拖入图片 → **Commit changes**。
   命名规则：`bv999-1.jpg`、`bv999-2.jpg`（英文小写、数字、连字符，别用空格和中文）。
2. **改数据**
   打开 https://github.com/romainyang/eclife-store/blob/main/data/products.json → 点右上铅笔图标进入编辑。
   在数组最后一项后面补一个英文逗号 `,`，把下面的「产品块」粘进去改成你的内容 → **Commit changes**。
3. **等 1 分钟**
   打开 https://github.com/romainyang/eclife-store/actions ，会看到一次 `Build & deploy to GitHub Pages` 在跑，变绿勾即上线。
4. **访问新网址** `https://yange.asia/product/bv999/`

### 方式 B：本地改（发布前能预览）

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
- `gallery` 只写文件名，不带 `images/details/` 前缀、不带 `.jpg` 后缀，第一张是主图
- JSON 语法：最后一项后面**不能**有多余逗号，引号必须是英文 `"`
- 图片要先 commit，再改 JSON（或两者一起提交），否则构建时图片还不存在

### 修改 / 删除已有产品

- **改文案、价格、图片**：直接改 `data/products.json` 对应字段。**不要改 `key`**——改了等于换了网址，之前分享出去的链接会 404
- **给已有产品加图**：上传图片后，在它的 `gallery` 数组里加文件名
- **删除产品**：从数组里删掉那一块（注意前后逗号），再手动删掉 GitHub 上的 `product/<key>/` 目录和图片。构建不会替你清理旧目录
- **改完都在 Actions 里确认变绿**，失败时点开看红色步骤的日志，八成是 JSON 逗号或引号写错了

---

## 本地预览

```bash
python -m http.server 8080
```

浏览器打开 http://localhost:8080 （不要直接双击 index.html，相对路径会失效）

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
