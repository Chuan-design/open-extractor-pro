#!/usr/bin/env python3
"""
Open Extractor Pro — Unified CLI Entry Point
用法:
  python3 extract.py <URL或文件路径>
  python3 extract.py <链接1> <链接2> ...
  python3 extract.py --batch <文件>
  pbpaste | python3 extract.py --stdin          # 从剪贴板读取 HTML
  python3 extract.py --stdin < 页面源码.html     # 从文件重定向

支持的平台:
  - 小红书 (https://www.xiaohongshu.com/explore/...)
  - MakerWorld (https://makerworld.com.cn/models/...)
  - 本地 HTML/RTF 文件（MakerWorld 页面源码）

快速提取 MakerWorld（浏览器 → 终端，2 步）:
  1. 在 MakerWorld 页面打开 DevTools Console，粘贴:
     copy(document.getElementById('__NEXT_DATA__').textContent)
  2. 终端运行:
     pbpaste | python3 extract.py --stdin
"""

import sys
import os
import re
import time
import tempfile

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

# MakerWorld 快速提取的浏览器 snippet
MW_SNIPPET = (
    "// 在 MakerWorld 页面 DevTools Console 运行，把数据复制到剪贴板\n"
    "copy(document.getElementById('__NEXT_DATA__').textContent)"
)


def detect_platform(url_or_path):
    if url_or_path.startswith(('http://', 'https://')):
        if 'xiaohongshu.com' in url_or_path or 'xhslink.com' in url_or_path:
            return 'xhs'
        elif 'makerworld.com' in url_or_path:
            return 'makerworld'
        return None

    if os.path.isfile(url_or_path):
        ext = os.path.splitext(url_or_path)[1].lower()
        if ext in ('.html', '.htm', '.txt', '.rtf'):
            return 'makerworld'

    return None


def detect_platform_from_html(html):
    """从 HTML 内容推断平台"""
    if '__NEXT_DATA__' in html or 'makerworld' in html[:2000].lower():
        return 'makerworld'
    if '__INITIAL_STATE__' in html:
        return 'xhs'
    return 'makerworld'  # 默认


def extract_xhs(urls, delay=2):
    from xhs_extract import load_cookies, extract_single, extract_batch
    cookies = load_cookies()

    if len(urls) == 1:
        ok, msg = extract_single(urls[0], cookies)
        print(msg)
        return (1, 0) if ok else (0, 1)
    else:
        return extract_batch(urls, cookies, delay)


def extract_makerworld(items):
    from makerworld_extract import fetch_from_url, load_html_from_file, parse_next_data, extract

    success = 0
    fail = 0

    for i, item in enumerate(items):
        item = item.strip()
        if not item:
            continue

        print(f"[{i+1}/{len(items)}] 处理: {os.path.basename(item) if os.path.isfile(item) else item[:60]}...", end=' ', flush=True)

        if item.startswith(('http://', 'https://')):
            design, error = fetch_from_url(item)
            if error:
                print(f"❌ {error}")
                print(f"\n💡 MakerWorld 有 Cloudflare 保护，快速提取方法:")
                print(f"   1. 浏览器打开页面 → DevTools Console")
                print(f"   2. 粘贴运行后复制结果:")
                print(f"      {MW_SNIPPET}")
                print(f"   3. 终端运行:")
                print(f"      pbpaste | python3 extract.py --stdin")
                fail += 1
                continue
            out = extract(design, item)
            print(f"✓ 已保存: {out}")
            success += 1
        else:
            filepath = item
            if not os.path.exists(filepath):
                desktop_path = os.path.expanduser(f"~/Desktop/{filepath}")
                if os.path.exists(desktop_path):
                    filepath = desktop_path
                else:
                    print(f"❌ 文件不存在: {item}")
                    fail += 1
                    continue

            html = load_html_from_file(filepath)
            if html is None:
                print(f"❌ 无法读取文件")
                fail += 1
                continue

            design, error = parse_next_data(html)
            if error:
                print(f"❌ {error}")
                fail += 1
                continue

            out = extract(design)
            print(f"✓ 已保存: {out}")
            success += 1

        if i < len(items) - 1:
            time.sleep(1)

    return success, fail


def extract_html_from_stdin(data):
    """从 stdin 读取内容提取（支持 RAW JSON 或 HTML）"""
    data = data.strip()

    from makerworld_extract import extract, parse_next_data

    # 情况 1：已经是 __NEXT_DATA__ 的 JSON（浏览器 snippet 复制出来的）
    if data.startswith('{'):
        try:
            import json
            parsed = json.loads(data)
            # 验证是有效的 __NEXT_DATA__ 格式
            props = parsed.get('props', {}).get('pageProps', {})
            if props.get('design'):
                print(f"  ✓ 检测到 __NEXT_DATA__ JSON ({len(data)} 字节)")
                out = extract(props['design'])
                print(f"  ✓ 已保存: {out}")
                return 1, 0
        except json.JSONDecodeError:
            pass

    # 情况 2：HTML 格式（cat file.html | extract.py --stdin）
    design, error = parse_next_data(data)
    if design:
        out = extract(design)
        print(f"  ✓ 已保存: {out}")
        return 1, 0

    print(f"❌ {error}")
    print(f"💡 MakerWorld 快速提取:")
    print(f"   1. 页面 DevTools Console → 粘贴: {MW_SNIPPET}")
    print(f"   2. 终端: pbpaste | python3 extract.py --stdin")
    return 0, 1


def print_summary(success, fail):
    total = success + fail
    print(f"\n{'=' * 40}")
    print(f"成功: {success} | 失败: {fail} | 总计: {total}")
    print(f"{'=' * 40}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    args = sys.argv[1:]

    # --stdin 模式：从管道读取 HTML
    if args[0] == '--stdin':
        html = sys.stdin.read()
        if not html.strip():
            print("❌ 未读取到数据（stdin 为空）")
            print("用法: pbpaste | python3 extract.py --stdin")
            sys.exit(1)
        print(f"📄 从 stdin 读取 {len(html)} 字节")
        s, f = extract_html_from_stdin(html)
        print_summary(s, f)
        return

    # --safari 模式：通过 Safari AppleScript 抓取 MakerWorld
    if args[0] == '--safari':
        urls = args[1:]
        if not urls:
            print("❌ 请提供 MakerWorld URL")
            print("用法: python3 extract.py --safari <URL1> [URL2] ...")
            sys.exit(1)
        from makerworld_extract import fetch_from_safari, parse_next_data, extract
        success = 0
        fail = 0
        for i, url in enumerate(urls):
            print(f"[{i+1}/{len(urls)}] 🌐 通过 Safari 抓取: {url.split('/')[-1][:40]}...")
            page, error = fetch_from_safari(url)
            if error:
                print(f"  ❌ {error}")
                fail += 1
                continue
            design, error = parse_next_data(page)
            if error:
                print(f"  ❌ {error}")
                fail += 1
                continue
            try:
                extract(design, url)
                success += 1
            except Exception as e:
                print(f"  ❌ 保存出错: {e}")
                fail += 1
        print_summary(success, fail)
        return

    # --snippet 模式：只打印 browser snippet
    if args[0] == '--snippet':
        print(MW_SNIPPET)
        return

    # 批量模式
    if args[0] == '--batch' and len(args) >= 2:
        batch_file = args[1]
        if not os.path.exists(batch_file):
            print(f"❌ 文件不存在: {batch_file}")
            sys.exit(1)
        with open(batch_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        if not urls:
            print("文件中未找到链接")
            sys.exit(1)
        print(f"从 {batch_file} 读取 {len(urls)} 个链接")
    else:
        urls = args

    # 分组
    xhs_urls = []
    mw_items = []

    for u in urls:
        platform = detect_platform(u)
        if platform == 'xhs':
            xhs_urls.append(u)
        elif platform == 'makerworld':
            mw_items.append(u)
        elif platform is None:
            expanded = os.path.expanduser(u)
            if os.path.exists(expanded):
                mw_items.append(expanded)
            else:
                desktop = os.path.expanduser(f"~/Desktop/{u}")
                if os.path.exists(desktop):
                    mw_items.append(desktop)
                else:
                    print(f"⚠ 无法识别: {u[:60]}（跳过）")

    s, f = 0, 0

    if xhs_urls:
        print(f"\n{'=' * 40}")
        print(f"📕 小红书 ({len(xhs_urls)} 个)")
        print(f"{'=' * 40}")
        s1, f1 = extract_xhs(xhs_urls)
        s += s1
        f += f1

    if mw_items:
        print(f"\n{'=' * 40}")
        print(f"🖨️ MakerWorld ({len(mw_items)} 个)")
        print(f"{'=' * 40}")
        s2, f2 = extract_makerworld(mw_items)
        s += s2
        f += f2

    print_summary(s, f)


if __name__ == '__main__':
    main()
