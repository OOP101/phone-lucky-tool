# -*- coding: utf-8 -*-
"""简历一键构建：YAML → 各版本 HTML → 批量导出 PDF → 结构/页数校验。

用法：
    双击 build.bat                     # Windows 最省事
    python scripts/build_all.py
    python scripts/build_all.py --no-pdf   # 只生成 + 校验，不导出 PDF

数据流：
    resume_data.yaml（内容） + resume_templates/*.j2（版式）
        -- scripts/gen_from_data.py --> output/*.html -- Edge/Chrome 无头 --> output/*.pdf
    改内容只改 YAML；改样式只改模板；不要手改产出的 HTML。
"""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

PROJ = pathlib.Path(config.ROOT)
GEN_SCRIPT = pathlib.Path(__file__).resolve().parent / 'gen_from_data.py'

# 参与构建的目录（相对项目根）
TARGET_DIRS = ['output']


def _w(s):
    """按显示宽度算（中文/全角算 2）"""
    return sum(2 if unicodedata.east_asian_width(c) in 'WFA' else 1 for c in s)


def pad(s, width):
    return s + ' ' * max(0, width - _w(s))


def _resolve(exe):
    """裸命令名（python/py 等）转绝对路径；已是路径则原样返回。"""
    if os.path.isabs(exe) or os.sep in exe:
        return exe if os.path.exists(exe) else None
    return shutil.which(exe)


def find_gen_python():
    """找一个装了 PyYAML + Jinja2 的解释器"""
    seen = set()
    for exe in config.PYTHON_CANDIDATES:
        real = _resolve(exe)
        if not real or real.lower() in seen:
            continue
        seen.add(real.lower())
        r = subprocess.run([real, '-c', 'import yaml, jinja2'], capture_output=True)
        if r.returncode == 0:
            return real
    return None


def run_generate(dry=False):
    """跑生成器：YAML + 模板 → output/*.html，返回 (ok, 行列表)"""
    exe = find_gen_python()
    if not exe:
        return False, [('生成', '', '找不到装了 PyYAML/Jinja2 的解释器，'
                                    '先 `pip install pyyaml jinja2`，'
                                    '或在 scripts/config.py 的 PYTHON_CANDIDATES 里指定路径')]
    if dry:
        return True, [('生成', '', 'dry-run（解释器 %s）' % os.path.basename(exe))]
    r = subprocess.run([exe, str(GEN_SCRIPT), '--check'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    out = [('生成', '', l) for l in (r.stdout or '').strip().splitlines() if l.strip()]
    if r.returncode != 0:
        out.append(('生成', '', '失败:\n' + (r.stderr or '')[-600:]))
        return False, out
    return True, out


def collect_html():
    files = []
    for d in TARGET_DIRS:
        dd = PROJ / d
        if not dd.is_dir():
            continue
        for f in sorted(dd.glob('*.html')):
            if re.search(r'(\.bak|_probe|_hdr_check|_shot)', f.name):
                continue
            files.append(f)
    return files


def check_html(p):
    s = p.read_text(encoding='utf-8', errors='replace')
    body = s[s.index('<body'):] if '<body' in s else s
    depth = body.count('<div') - body.count('</div>')
    photo = s.count('<img class="photo"')
    secs = len(re.findall(r'<h2[^>]*>', s))
    return depth, photo, secs


def export_pdf(html, pdf, browser):
    pdf.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([browser, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                        '--print-to-pdf=' + str(pdf), html.as_uri()],
                       capture_output=True, timeout=180)
    if not pdf.exists():
        return None, (r.stderr or b'').decode('utf-8', 'replace')[-200:]
    d = pdf.read_bytes()
    cnt = sorted(set(int(x) for x in re.findall(rb'/Count\s+(\d+)', d)))
    pages = len(re.findall(rb'/Type\s*/Page[^s]', d))
    return (cnt, pages), ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-pdf', action='store_true', help='不导出 PDF')
    args = ap.parse_args()

    browser = config.find_browser()
    print('项目根 :', PROJ)
    print('浏览器 :', browser if browser else
          'NOT FOUND —— 请安装 Edge/Chrome，或在 scripts/config.py 配置路径')
    print('=' * 78)

    ok, lines = run_generate(dry=args.no_pdf)
    for kind, name, msg in lines:
        print(f'[{kind}] {name}{": " if name else ""}{msg}')
    print('=' * 78)
    print(pad('文件', 56) + pad('div', 6) + pad('照片', 6) + pad('章节', 6) + '   PDF')
    print('-' * 78)

    n = 0
    for h in collect_html():
        depth, photo, secs = check_html(h)
        rel = h.relative_to(PROJ)
        pdf_info = '—'
        if not args.no_pdf:
            if not browser:
                pdf_info = '跳过（无可用浏览器）'
            else:
                info, err = export_pdf(h, h.with_suffix('.pdf'), browser)
                pdf_info = f'{info[0][0]} 页' if info else '导出失败 ' + err
                if not info:
                    ok = False
        flag = '' if depth == 0 else '  <-- div 不闭合'
        ok = ok and depth == 0
        print(pad(str(rel), 56) + pad(str(depth), 6) + pad(str(photo), 6)
              + pad(str(secs), 6) + '   ' + pdf_info + flag)
        n += 1

    print('-' * 78)
    print(f'共 {n} 个文件 | {"全部通过" if ok else "有失败项，见上"}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
