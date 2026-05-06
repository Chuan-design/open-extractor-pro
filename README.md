# 🗂️ Open Extractor Pro

> 社交平台内容提取工具集 — 将小红书帖子、MakerWorld 3D 模型等平台内容一键提取为 Obsidian 笔记。

## ✨ 支持平台

| 平台 | 工具 | 功能 |
|------|------|------|
| 📕 **小红书** | `xhs_extract.py` | 帖子正文、图片、互动数据 → Obsidian 笔记 |
| 🖨️ **MakerWorld** | `makerworld_extract.py` | 3D 模型信息、打印参数、图片 → Obsidian 笔记 |
| 🔜 更多 | 敬请期待 | 按需扩展... |

## 🚀 快速开始

### 前置要求

- Python 3.8+
- Obsidian（可选，笔记输出为 Markdown 可在任何编辑器查看）

### 安装

```bash
git clone https://github.com/Chuan-design/open-extractor-pro.git
cd open-extractor-pro
```

两个脚本均使用 Python 标准库，**无需额外安装依赖**。

### 使用方法

#### 📕 小红书帖子提取

```bash
python3 xhs_extract.py <帖子链接>
python3 xhs_extract.py <链接1> <链接2> ...  # 批量提取
python3 xhs_extract.py --batch <文件>      # 从文件读取链接列表
```

**前置步骤**（只需一次）：
1. 登录小红书网页版
2. 打开 Chrome DevTools → Application → Cookies → 导出为 `~/cookies.json`
3. 格式：Chrome 扩展 [EditThisCookie](https://www.editthiscookie.com/) 导出的标准 JSON

#### 🖨️ MakerWorld 模型提取

**方式 1：本地文件解析（推荐，无反爬限制）**

在浏览器打开 MakerWorld 模型页面 → 右键查看页面源码 → 全选复制 → 保存为 `.html` 或 `.txt` 文件：

```bash
python3 makerworld_extract.py 保存的文件.html
# 也支持 RTF 格式（直接从浏览器复制粘贴保存的）
python3 makerworld_extract.py 1111.rtf
# 桌面文件可用简写
python3 makerworld_extract.py 1111.txt
```

**方式 2：直接 URL 抓取**

```bash
python3 makerworld_extract.py https://makerworld.com.cn/models/xxx
```

### 输出目录

所有笔记默认输出到：
```
/Volumes/archive/Obsidian/Clippings/
```

在 Obsidian 中通过 `obsidian://open?vault=Obsidian&file=Clippings%2F{标题}` 访问。

如需修改，编辑脚本中的 `OUTPUT_DIR` 变量。

## 📄 输出示例

### 小红书笔记

```yaml
---
title: 笔记标题
created: 2026-05-06
tags: [clippings]
---
# 笔记标题
正文内容...
> [!tip]- 详情
> - 作者、标签、互动数据
> [!info]- 笔记属性
> - 来源、链接、类型
```

### MakerWorld 模型

```yaml
---
title: Bambu Lab A1-打印热床刮刀
tags: [clippings, makerworld, 3d打印]
---
# 模型名称
模型描述...
> [!tip]- 模型详情
> - 作者、分类、打印参数、材料、图片
> [!info]- 笔记属性
> - 来源、模型ID、互动数据
```

## 📦 项目结构

```
open-extractor-pro/
├── xhs_extract.py           # 小红书帖子提取工具
├── makerworld_extract.py    # MakerWorld 3D 模型提取工具
├── requirements.txt         # 依赖说明（标准库，免安装）
├── LICENSE                  # MIT 许可证
└── .gitignore
```

## ⚙️ 技术原理

两个工具的核心思路一致：

1. **获取页面数据**：从 URL 抓取或读取本地 HTML 文件
2. **提取内嵌 JSON**：解析页面中的 `__INITIAL_STATE__`（小红书）或 `__NEXT_DATA__`（MakerWorld）
3. **结构化输出**：将原始数据映射为 Obsidian 友好的 Markdown 格式
4. **质量检查**：自动修复 YAML 格式、callout 嵌套、HTML 残留等常见问题

## ⚠️ 注意事项

- **小红书**：需要 cookies 认证，cookies 会过期，过期后重新导出即可
- **MakerWorld**：直接 URL 抓取可能被 Cloudflare 拦截，推荐使用本地文件解析模式
- 本工具仅供个人学习和研究使用，请遵守各平台服务条款
- 提取的内容请妥善保管，注意隐私保护

## 📝 更新计划

- [ ] 支持更多平台（知乎、B站等）
- [ ] 统一入口脚本
- [ ] 批量处理优化

## 📄 许可证

[MIT](LICENSE)

---

**⭐ 如果这个项目对你有帮助，欢迎给个 Star！**
