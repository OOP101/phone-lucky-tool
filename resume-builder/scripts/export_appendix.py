# -*- coding: utf-8 -*-
"""把一页「技术附录」HTML 导出为 PDF，并可合并到主简历 PDF 末尾（合并需 pymupdf）。

用法：
    pip install pymupdf   # 仅 --merge 需要

    python scripts/export_appendix.py --appx appendix/技术附录.html
        # 只导出附录 PDF（与 HTML 同名同目录）

    python scripts/export_appendix.py --appx appendix/技术附录.html \
        --main output/张三_AI应用开发工程师.pdf
        # 导出后合并：产出 *_含项目附录.pdf

合并时会自动把附录页头的「求职意向」替换成主简历同名 HTML 里的意向，保证口径一致。
"""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402


def edge_print(html_path, pdf_path):
    browser = config.find_browser()
    if not browser:
        sys.exit('未找到 Edge/Chrome，请安装或在 scripts/config.py 配置路径')
    pdf_path = pathlib.Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([browser, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                        '--print-to-pdf=' + str(pdf_path), html_path.as_uri()],
                       capture_output=True, timeout=180)
    if not pdf_path.exists():
        sys.exit('导出失败: ' + (r.stderr or b'').decode('utf-8', 'replace')[-300:])
    return pdf_path


def main_intent(main_pdf):
    """从主简历同目录同名 HTML 里取「求职意向」整行（无 HTML 则返回 None）"""
    h = main_pdf.with_suffix('.html')
    if not h.exists():
        return None
    m = re.search(r'求职意向[^<]*', h.read_text(encoding='utf-8', errors='replace'))
    return m.group(0).strip() if m else None


def do_merge(main_pdf, appx_html):
    main_pdf = pathlib.Path(main_pdf)
    if not main_pdf.exists():
        sys.exit('主简历不存在: ' + str(main_pdf))
    intent = main_intent(main_pdf)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='appx_'))
    try:
        html = pathlib.Path(appx_html).read_text(encoding='utf-8')
        if intent and '求职意向：' in html:
            cur = re.search(r'求职意向[^<]*', html).group(0)
            if cur.strip() != intent:
                html = html.replace(cur, intent)
                print('意向已同步:', intent)
        tmp_html = tmp / 'appx.html'
        tmp_html.write_text(html, encoding='utf-8')
        tmp_pdf = edge_print(tmp_html, tmp / 'appx.pdf')

        import pymupdf
        merged_path = main_pdf.with_name(main_pdf.stem + '_含项目附录.pdf')
        doc = pymupdf.open(main_pdf)
        n_main = doc.page_count
        doc.insert_pdf(pymupdf.open(str(tmp_pdf)))
        doc.save(str(merged_path), garbage=3, deflate=True)
        doc.close()
        chk = pymupdf.open(str(merged_path))
        print('合并完成: %s（主简历 %d 页 + 附录 %d 页 = %d 页）'
              % (merged_path.name, n_main, chk.page_count - n_main, chk.page_count))
        chk.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--appx', required=True, help='附录 HTML 路径（相对项目根或绝对路径）')
    ap.add_argument('--merge', action='store_true', help='导出后合并进主简历')
    ap.add_argument('--main', help='主简历 PDF 路径（相对项目根或绝对路径）')
    args = ap.parse_args()

    root = pathlib.Path(config.ROOT)
    appx_html = pathlib.Path(args.appx)
    if not appx_html.is_absolute():
        appx_html = root / appx_html
    if not appx_html.exists():
        sys.exit('找不到附录 HTML: ' + str(appx_html))

    appx_pdf = appx_html.with_suffix('.pdf')
    edge_print(appx_html, appx_pdf)
    try:
        import pymupdf
        d = pymupdf.open(str(appx_pdf))
        box = d[0].rect
        print('附录导出: %s（%d 页，页面 %.0f×%.0f pt）'
              % (appx_pdf.name, d.page_count, box.width, box.height))
        d.close()
    except ImportError:
        print('附录导出完成（未装 pymupdf，跳过页数校验）')

    if args.merge:
        if not args.main:
            sys.exit('--merge 需要同时指定 --main 主简历 PDF 路径')
        main_pdf = pathlib.Path(args.main)
        if not main_pdf.is_absolute():
            main_pdf = root / main_pdf
        do_merge(main_pdf, appx_html)


if __name__ == '__main__':
    main()
