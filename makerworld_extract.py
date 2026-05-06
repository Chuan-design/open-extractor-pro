#!/usr/bin/env python3
"""
MakerWorld 模型提取工具（类似 xhs_extract.py）
用法: python3 makerworld_extract.py <HTML文件/RTF文件/MakerWorld链接>

从 MakerWorld 模型页面提取信息，生成 Obsidian 笔记。
支持：
  - 直接 URL 抓取（需要网络）
  - 本地 HTML 文件解析（浏览器保存的页面源码）
  - 本地 RTF 文件解析（复制粘贴保存的格式）
"""

import json
import re
import datetime
import sys
import os
import urllib.request
import ssl
import urllib.parse
import subprocess

# === 配置 ===
OUTPUT_DIR = '/Volumes/archive/Obsidian/Clippings'


def convert_rtf_to_text(filepath):
    """将 .rtf 文件转换为纯文本"""
    txt_path = filepath + '.converted.txt'
    try:
        subprocess.run(['textutil', '-convert', 'txt', filepath, '-output', txt_path],
                       capture_output=True, timeout=30)
        if os.path.exists(txt_path):
            return txt_path
    except Exception:
        pass
    return None


def parse_next_data(content):
    """从 HTML 内容解析 __NEXT_DATA__"""
    idx = content.find('__NEXT_DATA__')
    if idx < 0:
        return None, "未找到 __NEXT_DATA__，请确认复制了完整的页面 HTML"

    start = content.index('>', idx) + 1
    end = content.index('</script>', start)
    raw = content[start:end].strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"JSON 解析失败: {e}"

    design = data.get('props', {}).get('pageProps', {}).get('design')
    if not design:
        return None, "未找到模型数据（pageProps.design 为空）"

    return design, None


def load_html_from_file(filepath):
    """从本地文件加载 HTML 内容（支持 .html/.txt/.rtf）"""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.rtf':
        print(f"  ⚡ 检测到 RTF 格式，正在转换...")
        txt_path = convert_rtf_to_text(filepath)
        if not txt_path:
            return None
        with open(txt_path, 'r', errors='ignore') as f:
            content = f.read()
        os.unlink(txt_path)
        return content

    with open(filepath, 'r', errors='ignore') as f:
        return f.read()


def fetch_from_url(url):
    """直接从 MakerWorld URL 抓取页面"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None, f"请求失败: {e}"

    return parse_next_data(html)


def clean_html(html_text):
    """清理 HTML 标签，提取纯文本"""
    text = re.sub(r'<img[^>]*>', '', html_text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_content(design, source_url=''):
    """生成 Obsidian 笔记 Markdown"""
    title = design.get('title', '')
    if not title:
        title = f"MakerWorld模型_{design.get('id', '')}"
    slug = design.get('slug', '')
    model_id = design.get('id', '')

    if not source_url:
        source_url = f"https://makerworld.com.cn/models/{model_id}-{slug}"

    # 创作者
    creator = design.get('designCreator', {})
    creator_name = creator.get('name', '未知')
    creator_handle = creator.get('handle', '')
    creator_str = f"{creator_name} (@{creator_handle})" if creator_handle else creator_name

    # 分类
    categories = design.get('categories', [])
    category_names = ' > '.join(c.get('name', '') for c in categories) if categories else '未分类'

    # 标签
    tags = design.get('tags', [])

    # 描述
    summary_html = design.get('summary', '')
    summary_text = clean_html(summary_html)
    desc_short = summary_text[:200] if summary_text else '(无描述)'

    # 日期
    create_time = design.get('createTime', '')
    date_str = create_time[:10] if create_time else datetime.datetime.now().strftime('%Y-%m-%d')
    update_time = design.get('updateTime', '')
    update_str = update_time[:10] if update_time else ''

    # 互动数据
    likes = design.get('likeCount', 0)
    collects = design.get('collectionCount', 0)
    downloads = design.get('downloadCount', 0)
    prints = design.get('printCount', 0)
    comments = design.get('commentCount', 0)

    interact_parts = []
    if likes: interact_parts.append(f"{likes} 赞")
    if collects: interact_parts.append(f"{collects} 收藏")
    if downloads: interact_parts.append(f"{downloads} 下载")
    if prints: interact_parts.append(f"{prints} 打印")
    if comments: interact_parts.append(f"{comments} 评论")
    interact_str = ' / '.join(interact_parts) if interact_parts else 'N/A'

    license_type = design.get('license', '')

    # 打印实例
    instances = design.get('instances', [])
    instance_details = []
    for inst in instances:
        inst_title = inst.get('title', '未知配置')
        weight = inst.get('weight', 0)
        prediction = inst.get('prediction', 0)
        need_ams = inst.get('needAms', False)

        filaments = inst.get('instanceFilaments', [])
        filament_info = []
        for f in filaments:
            ftype = f.get('type', '')
            fcolor = f.get('color', '')
            fg = f.get('usedG', '')
            part = ftype
            if fcolor:
                part += f" ({fcolor})"
            if fg:
                part += f" - {fg}g"
            filament_info.append(part)

        ext = inst.get('extention', {})
        model_info = ext.get('modelInfo', {}) if isinstance(ext, dict) else {}
        compatibility = model_info.get('compatibility', {}) if isinstance(model_info, dict) else {}
        printer = compatibility.get('devProductName', '') if isinstance(compatibility, dict) else ''

        # 解析层高/墙/填充
        m_h = re.search(r'([\d.]+)\s*mm?\s*层高', inst_title)
        m_w = re.search(r'(\d+)\s*层墙', inst_title)
        m_i = re.search(r'(\d+)%\s*填充', inst_title)
        layer_h = m_h.group(1) if m_h else ''
        wall = m_w.group(1) if m_w else ''
        infill = m_i.group(1) if m_i else ''

        instance_details.append({
            'title': inst_title, 'printer': printer,
            'layer_h': layer_h, 'wall': wall, 'infill': infill,
            'weight': weight, 'prediction': prediction,
            'filaments': filament_info, 'need_ams': need_ams,
        })

    # 图片
    pictures = []
    for inst in instances:
        for pic in inst.get('pictures', []):
            if pic.get('url'):
                pictures.append(pic['url'])
    cover = design.get('coverUrl', '')
    if cover and cover not in pictures:
        pictures.insert(0, cover)

    # 正文
    body = summary_text if summary_text else '(无描述)'

    # YAML tags
    yaml_tags = ['clippings', 'makerworld', '3d打印']
    for t in tags:
        if t not in ('3D打印', '3d打印'):
            yaml_tags.append(t)

    # Obsidian 链接
    obs_title = urllib.parse.quote(title)
    obsidian_link = f"obsidian://open?vault=Obsidian&file=Clippings%2F{obs_title}"

    # 图片 Markdown
    images_md = ''
    for i, img_url in enumerate(pictures[:5]):
        images_md += f"> ![图{i + 1}]({img_url})\n> \n"

    # 打印参数
    print_params = ''
    for inst in instance_details:
        parts = []
        if inst['printer']: parts.append(f"打印机: {inst['printer']}")
        if inst['layer_h']: parts.append(f"层高: {inst['layer_h']}mm")
        if inst['wall']: parts.append(f"墙数: {inst['wall']}")
        if inst['infill']: parts.append(f"填充: {inst['infill']}%")
        if inst['weight']: parts.append(f"重量: {inst['weight']}g")
        if inst['prediction']: parts.append(f"预估: {inst['prediction']}mm")
        if inst['filaments']: parts.append(f"材料: {'; '.join(inst['filaments'])}")
        if inst['need_ams']: parts.append("需 AMS")
        params_str = ' / '.join(parts) if parts else '未提供'
        print_params += f"> - **{inst['title']}**: {params_str}\n"

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d')

    # 热度标签
    hot_tag = f'高热度：{collects} 收藏 / {downloads} 下载' if (collects > 50 or downloads > 50) else ''

    content = f"""---
title: {title}
source: {source_url}
created: {timestamp}
description: "{desc_short.replace(chr(10), ' ').replace('"', "'")}"
tags:
  - {chr(10).join(f'  - {t}' for t in yaml_tags)}
---

# {title}

{body}

**与我的关联：** 你在做 AI Agent 與設計教學，MakerWorld 上的 3D 打印模型可作為產品設計、原型製作的商業案例參考，尤其在下游工具鏈和用戶反饋分析方面有借鑒價值。

**值得深挖吗：** {'视模型质量和应用场景而定——可分析设计语言、打印工艺与用户反馈的关联。 ' + hot_tag if hot_tag else '视模型质量和应用场景而定——可分析设计语言、打印工艺与用户反馈的关联。'}

> [!tip]- 模型详情
> - **作者**: {creator_str}
> - **分类**: {category_names}
> - **标签**: {', '.join(tags)}
> - **许可**: {license_type}
>
> **打印配置：**
{print_params}
> **图片：**
{images_md}
> [!info]- 笔记属性
> - **来源**: MakerWorld · {creator_name}
> - **模型ID**: {model_id}
> - **链接**: {source_url}
> - **Obsidian**: [{title}]({obsidian_link})
> - **日期**: {date_str}
> - **更新**: {update_str if update_str and update_str != date_str else 'N/A'}
> - **类型**: 3D 模型
> - **互动**: {interact_str}
"""

    return content, title


def quality_check(filepath):
    """質量檢查"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content
    issues = []

    # Fix unescaped double quotes in description
    desc_match = re.search(r'(?:^|\n)description: (")(.*?)(")(?:\n)', content)
    if desc_match:
        desc_val = desc_match.group(2)
        if '"' in desc_val:
            content = (content[:desc_match.start(2)] +
                      desc_val.replace('"', "'") +
                      content[desc_match.end(2):])

    # Fix callout missing > prefix
    lines = content.split('\n')
    new_lines = []
    in_callout = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('> [!') and stripped.endswith(']'):
            in_callout = True
            new_lines.append(line)
            continue
        if in_callout:
            if re.match(r'^> \[!(?:info|tip|warning|note|danger)', stripped):
                new_lines.append(line)
                continue
            if not line.startswith('>') and stripped:
                new_lines.append('> ' + stripped)
                continue
        new_lines.append(line)
    content = '\n'.join(new_lines)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    if '待补充' in content or '待评估' in content:
        issues.append("有待补充/待评估 未填写")

    return issues


def extract(design, source_url=''):
    """从 design 字典提取并保存笔记"""
    content, title = generate_content(design, source_url)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{title}.md")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)

    issues = quality_check(out_path)

    creator = design.get('designCreator', {}).get('name', '')
    tags = design.get('tags', [])
    likes = design.get('likeCount', 0)
    dl = design.get('downloadCount', 0)

    print(f"  ✓ {title}")
    print(f"    作者: {creator}  |  标签: {', '.join(tags)}")
    print(f"    互动: {likes} 赞 / {dl} 下载")

    if issues:
        print(f"  ⚠  {'; '.join(issues)}")

    return out_path


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 makerworld_extract.py <HTML/RTF文件>")
        print("  python3 makerworld_extract.py <MakerWorld链接>")
        print(f"\n输出目录: {OUTPUT_DIR}")
        sys.exit(1)

    arg = sys.argv[1]

    # URL 模式
    if arg.startswith('http://') or arg.startswith('https://'):
        print(f"🌐 正在抓取: {arg}")
        design, error = fetch_from_url(arg)
        if error:
            print(f"❌ {error}")
            print("提示: MakerWorld 可能有 Cloudflare 保护，建议用 '保存页面为 HTML' 方式再试")
            sys.exit(1)
        out = extract(design, arg)
        print(f"✓ 已保存: {out}")

    # 本地文件模式
    else:
        filepath = arg
        if not os.path.exists(filepath):
            desktop_path = os.path.expanduser(f"~/Desktop/{filepath}")
            if os.path.exists(desktop_path):
                filepath = desktop_path
            else:
                print(f"❌ 文件不存在: {arg}")
                sys.exit(1)

        print(f"📄 正在解析: {filepath}")
        html = load_html_from_file(filepath)
        if html is None:
            print("❌ 无法读取文件")
            sys.exit(1)

        design, error = parse_next_data(html)
        if error:
            print(f"❌ {error}")
            sys.exit(1)

        out = extract(design)
        print(f"✓ 已保存: {out}")


if __name__ == '__main__':
    main()
