#!/usr/bin/env python3
"""
小紅書帖子提取工具
用法: python3 xhs_extract.py <链接1> [链接2] [链接3] ...
      python3 xhs_extract.py --batch <包含链接列表的文件>

Cookies 文件: ~/cookies.json
输出目录: /Volumes/archive/Obsidian/Chuan Wiki/raw/011.我的自媒体/小红书
"""

import json
import urllib.request
import ssl
import re
import datetime
import sys
import os
import time
import urllib.parse
from datetime import timezone

# === 配置 ===
COOKIES_PATH = os.path.expanduser('~/cookies.json')
OUTPUT_DIR = '/Volumes/archive/Obsidian/Clippings'

def load_cookies():
    """加载 cookies 文件"""
    if not os.path.exists(COOKIES_PATH):
        print(f"❌ Cookies 文件不存在: {COOKIES_PATH}")
        print("请先从小红书导出 cookies 保存到该文件。")
        sys.exit(1)
    with open(COOKIES_PATH) as f:
        return json.load(f)

def fetch_note(url, cookies):
    """请求帖子页面并解析数据"""
    cookie_str = '; '.join(f"{c['name']}={c['value']}" for c in cookies)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url)
    req.add_header('Cookie', cookie_str)
    req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None, None, f"请求失败: {e}"

    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*</script>', html, re.DOTALL)
    if not m:
        return None, None, "未找到 __INITIAL_STATE__，cookies 可能已过期"

    raw = m.group(1).replace('undefined', 'null')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, None, f"JSON 解析失败: {e}"

    note_map = data.get('note', {}).get('noteDetailMap', {})
    if not note_map:
        return None, None, "未找到帖子数据"

    for post_id, val in note_map.items():
        return post_id, val.get('note', {}), None

    return None, None, "帖子数据为空"

def generate_content(url, post_id, note):
    """生成 Markdown 内容"""
    title = note.get('title', '')
    desc = note.get('desc', '')
    note_type = note.get('type', '')
    time_ms = note.get('time', 0)
    interact = note.get('interactInfo', {})
    user = note.get('user', {})
    images = note.get('imageList', [])
    video = note.get('video', {})

    dt = datetime.datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
    date_str = dt.strftime('%Y-%m-%d')
    user_name = user.get('nickname', '未知')
    liked = interact.get('likedCount', '')
    collected = interact.get('collectedCount', '')
    commented = interact.get('commentCount', '')

    # 视频时长
    duration = ''
    if note_type == 'video' and video:
        try:
            dur_ms = video.get('media', {}).get('stream', {}).get('h264', [{}])[0].get('duration', 0)
            duration = f" ({dur_ms / 1000:.0f}s)"
        except:
            pass

    # 标签提取
    tags_raw = re.findall(r'#(\S+?)\[话题\]', desc)
    tags_list = ', '.join(dict.fromkeys(tags_raw))

    # 清理描述
    desc_clean = re.sub(r'#\S+?\[话题\]', '', desc)
    desc_clean = re.sub(r'[💥⚡😭✨🎨🔥💯📈🎯🐍🐱🌱👻📱👜🤣🤓😂]', '', desc_clean)
    desc_clean = re.sub(r'\d+️', '', desc_clean)
    desc_clean = re.sub(r'\[[^\]]*\]', '', desc_clean)
    desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()

    # 判断是否为纯视觉帖
    if not desc_clean or desc_clean.replace('#', '').replace(' ', '').replace(',', '') == '':
        desc_clean = tags_list if tags_list else 'AIGC 生成的視覺作品。'
        is_visual = True
    else:
        is_visual = ('头像' in desc or 'AIGC' in desc or len(desc_clean) < 100) and note_type == 'video'

    # 图片 Markdown（最多 5 张）
    images_md = ''
    for j, img in enumerate(images[:5]):
        url_img = img.get('urlDefault', '')
        images_md += f"> ![圖{j + 1}]({url_img})\n> \n"

    # Obsidian 链接
    obs_title = urllib.parse.quote(title)
    obsidian_link = f"obsidian://open?vault=Obsidian&file=Clippings%2F{obs_title}"

    # 类型标签
    type_label = f"video{duration}" if note_type == 'video' else f"圖文 ({len(images)} 張圖)"

    # 互动数据
    interact_parts = []
    if liked:
        interact_parts.append(f"{liked} 贊")
    if collected:
        interact_parts.append(f"{collected} 收藏")
    if commented:
        interact_parts.append(f"{commented} 評論")
    interact_str = ' / '.join(interact_parts) if interact_parts else 'N/A'

    # 内容生成
    if is_visual:
        body = desc_clean if desc_clean else "AIGC 生成的視覺作品。"
        rel = "你在做 AI Agent 相關項目，這種低門檻創意工具的爆發正是你所在領域的應用側。"
        worth = "否。純視覺展示帖，無方法論或技術細節。"
    else:
        body = desc_clean
        rel = "你在做 AI Agent 相關項目，AI 生成可執行腳本解決實際痛點是 Agent 應用的典型模式。"
        worth = "是。DIY 和創意項目展示了 AI 工具落地的實用路徑，值得研究。"

    # Clean source URL: strip xsec_token and xsec_source params
    clean_url = re.sub(r'[?&]xsec_token=[^&]*', '', url)
    clean_url = re.sub(r'[?&]xsec_source=[^&]*', '', clean_url)

    # YAML tags: clippings + extracted tags
    yaml_tags = ['clippings'] + tags_raw
    tags_yaml = '\n  - '.join(yaml_tags)

    content = f"""---
title: {title}
source: {clean_url}
created: {datetime.datetime.now().strftime('%Y-%m-%d')}
description: "{desc_clean[:150].replace(chr(10), ' ').replace('"', "'")}"
tags:
  - {tags_yaml}
---
# {title}

{body}

**與我的关联：** {rel}

**值得深挖吗：** {worth}

> [!tip]- 詳情
> - **作者**: {user_name}
> - **內容摘要**: {body[:100]}
> - **工具**: AI 工具 (待確認)
> - **標籤**: {tags_list}
>
{images_md}
> [!info]- 筆記屬性
> - **來源**: 小紅書 · {user_name}
> - **帖子ID**: {post_id}
> - **鏈接**: {url}
> - **Obsidian**: [{title}]({obsidian_link})
> - **日期**: {date_str}
> - **類型**: {type_label}
> - **互動**: {interact_str}
> - **標籤**: {tags_list}
"""

    return content, title

def quality_check(content, filepath):
    """質量檢查並自動修復常見問題"""
    issues = []
    original = content
    basename = os.path.basename(filepath)

    # 1. Fix # # # in description
    desc_match = re.search(r'(description: ")(.*?)(")', content)
    if desc_match:
        desc_val = desc_match.group(2)
        # Check for unescaped double quotes inside description
        if '"' in desc_val:
            clean = desc_val.replace('"', "'")
            content = content[:desc_match.start()] + f'description: "{clean}"' + content[desc_match.end():]
        # Check for # # # remnants
        if '# #' in desc_val or re.match(r'^#+$', desc_val.strip()):
            tags_match = re.search(r'> - \*\*標籤\*\*: (.+?)\n', content)
            tags_str = tags_match.group(1).strip() if tags_match else ''
            clean = re.sub(r'\s*#(\s*#\s*)*$', '', desc_val)
            clean = re.sub(r'\s*#\s*#', '', clean)
            clean = clean.strip()
            if not clean:
                clean = tags_str
            content = content[:desc_match.start(1)] + f'description: "{clean}"' + content[desc_match.end(2)-1:]

    # 2. Fix # # # in body text
    content = re.sub(r' # # # # # # # # # #', '', content)
    content = re.sub(r' # # # # # # # # #', '', content)
    content = re.sub(r' # # # # # # # #', '', content)
    content = re.sub(r' # # # # # # #', '', content)
    content = re.sub(r' # # # # # #', '', content)
    content = re.sub(r' # # # # #', '', content)
    content = re.sub(r' # # # #', '', content)
    content = re.sub(r' # # #', '', content)
    content = re.sub(r'(?<!#) # # # # # # # # # #', '', content)
    content = re.sub(r'(?<!#) # # # # # # # # #', '', content)
    content = re.sub(r'(?<!#) # # # # # # # #', '', content)
    content = re.sub(r'(?<!#) # # # # # # #', '', content)
    content = re.sub(r'(?<!#) # # # # # #', '', content)
    content = re.sub(r'(?<!#) # # # # #', '', content)
    content = re.sub(r'(?<!#) # # # #', '', content)
    content = re.sub(r'(?<!#) # # #', '', content)
    content = re.sub(r' +$', '', content, flags=re.MULTILINE)

    # 3. Fix callout formatting - add > prefix to lines inside callout
    lines = content.split('\n')
    new_lines = []
    in_tip = False
    in_content_summary = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if '> [!tip]- 詳情' in stripped:
            in_tip = True
            new_lines.append(line)
            continue
        if in_tip and stripped.startswith('> [!info]'):
            in_tip = False
            in_content_summary = False
            new_lines.append(line)
            continue
        if in_tip:
            if stripped.startswith('> - **內容摘要**'):
                in_content_summary = True
                new_lines.append(line)
                continue
            if in_content_summary:
                if stripped == '' or stripped == '>':
                    new_lines.append('> ')
                    continue
                if stripped.startswith('> - **'):
                    in_content_summary = False
                    new_lines.append(line)
                    continue
                if not line.lstrip().startswith('>'):
                    new_lines.append('> ' + stripped)
                    continue
        new_lines.append(line)
    content = '\n'.join(new_lines)

    # 4. Fix image count in type field
    img_lines = [l for l in content.split('\n') if '![' in l and '](' in l and '.xhscdn.com' in l]
    actual = len(img_lines)
    type_match = re.search(r'> - \*\*類型\*\*: 圖文 \(\d+ 張圖\)', content)
    if type_match:
        content = re.sub(r'> - \*\*類型\*\*: 圖文 \(\d+ 張圖\)',
                         f'> - **類型**: 圖文 ({actual} 張圖)',
                         content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    # Report remaining issues
    if '# #' in content:
        issues.append(f"[{basename}] 仍有 # # # 殘留")
    if '待補充' in content or '待評估' in content:
        issues.append(f"[{basename}] 待補充/待評估 未填寫")
    if '"' in content.split('description: "')[1].split('"')[0] if 'description: "' in content else '':
        issues.append(f"[{basename}] description 中有未轉義的引號")

    return issues

def extract_single(url, cookies, output_dir=None):
    """提取单个帖子"""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    post_id, note, error = fetch_note(url, cookies)
    if error:
        return False, f"提取失败: {error}"

    content, title = generate_content(url, post_id, note)

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 保存文件
    filepath = os.path.join(output_dir, f"{title}.md")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 質量檢查
    issues = quality_check(content, filepath)
    if issues:
        return False, f"質量檢查未通過: {'; '.join(issues)}"

    return True, f"已保存: {title} [{note.get('type', '')}]"

def extract_batch(urls, cookies, delay=2, output_dir=None):
    """批量提取多个帖子"""
    if output_dir is None:
        output_dir = OUTPUT_DIR
    success = 0
    fail = 0
    results = []

    for i, url in enumerate(urls):
        url = url.strip()
        if not url:
            continue

        print(f"[{i + 1}/{len(urls)}] 提取: {url[:60]}...", end=' ', flush=True)
        ok, msg = extract_single(url, cookies, output_dir)
        print(msg)
        if ok:
            success += 1
            results.append(f"  ✓ {msg}")
        else:
            fail += 1
            results.append(f"  ✗ {msg}")

        if i < len(urls) - 1:
            time.sleep(delay)

    print(f"\n{'=' * 40}")
    print(f"成功: {success} | 失败: {fail}")
    print(f"{'=' * 40}")
    for r in results:
        print(r)

    return success, fail

def main():
    cookies = load_cookies()

    if len(sys.argv) < 2:
        print("用法: python3 xhs_extract.py <链接1> [链接2] ...")
        print("      python3 xhs_extract.py --batch <文件路径>")
        print("\nCookies 文件: ~/cookies.json")
        print(f"输出目录: {OUTPUT_DIR}")
        sys.exit(1)

    if sys.argv[1] == '--batch' and len(sys.argv) >= 3:
        # 从文件读取链接列表
        batch_file = sys.argv[2]
        with open(batch_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip().startswith('https://')]
        if not urls:
            print("文件中未找到小红书链接")
            sys.exit(1)
        print(f"从 {batch_file} 读取 {len(urls)} 个链接")
        extract_batch(urls, cookies)
    else:
        # 命令行参数作为链接
        urls = sys.argv[1:]
        if len(urls) == 1:
            ok, msg = extract_single(urls[0], cookies)
            print(msg)
        else:
            extract_batch(urls, cookies)

if __name__ == '__main__':
    main()
