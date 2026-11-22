# Eclife 浴室柜独立站

纯静态电商站，托管在 Cloudflare Pages，正式域名 **https://yange.asia**

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
├─ _headers               Cloudflare 缓存与安全响应头
├─ _redirects             www → 主域 跳转
└─ pack.py                打包成可上传的 zip
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

## 新增一款产品（4 步）

1. **放图片**：把图片复制进 `images/details/`，命名成 `bv999-1.jpg`、`bv999-2.jpg` 这种有规律的英文名
2. **加数据**：在 `data/products.json` 里复制一段现成的产品块，改字段（`key` / `id` 不能和已有的重复）
3. **构建**：`python build.py`
4. **提交**：`git add -A && git commit -m "add bv999" && git push`

构建会自动生成 `product/bv999/index.html`、把它加进首页列表和 sitemap。

---

## 本地预览

```bash
python -m http.server 8080
```

浏览器打开 http://localhost:8080 （不要直接双击 index.html，相对路径会失效）

---

## 打包上传（手动部署用）

```bash
python pack.py
```

生成 `../eclife-site.zip`，只含站点文件（不含 build.py、data、templates 等工具文件）。把它拖到 Cloudflare Pages 的 Upload assets 即可。

---

## 部署

推荐用 Cloudflare Pages 的 Git 集成：仓库一改，自动部署，不用再手动传 zip。

- 构建命令：**留空**
- 输出目录：**`/`**
- 框架预设：**None**

因为生成好的 HTML 已经提交在仓库里，Cloudflare 不需要再跑构建。

---

## 注意

- 购物车和订单存在浏览器 localStorage，纯静态站无法跨设备同步
- 图片建议控制在 1400px 宽、200KB 以内，单文件不能超过 25MB（Pages 限制）
- 改完 `data/products.json` 忘了跑 `build.py`，页面不会更新
