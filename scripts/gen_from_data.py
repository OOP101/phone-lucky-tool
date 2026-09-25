# -*- coding: utf-8 -*-
"""简历生成器：resume_data.yaml + resume_templates/*.j2 → output/*.html

用法（需要 PyYAML + Jinja2）：
    python scripts/gen_from_data.py             # 生成全部 profile
    python scripts/gen_from_data.py --list      # 只列版本
    python scripts/gen_from_data.py ai --check  # 只生成某一版 + 结构校验

平时不用单独跑 —— scripts/build_all.py 会自动带上 生成 + 校验 + 导 PDF。
"""
import argparse
import base64
import io
import os
import sys

try:
    import yaml
    from jinja2 import Environment, FileSystemLoader
except ImportError as e:  # pragma: no cover
    print('缺依赖:', e)
    print('请先安装：pip install pyyaml jinja2')
    sys.exit(2)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ROOT, DATA, TPLDIR  # noqa: E402

# 未配置证件照时的内置占位图（SVG 灰色剪影）
_PLACEHOLDER_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' width='240' height='320'>"
    "<rect width='100%' height='100%' fill='#e8eefb'/>"
    "<circle cx='120' cy='118' r='50' fill='#b9c8e8'/>"
    "<path d='M38 320 Q120 208 202 320 Z' fill='#b9c8e8'/>"
    "</svg>")


def resolve_photo(v):
    """photo 字段三种取值：data: URI 直通 / 空 → 内置占位图 / 本地路径 → base64 内嵌。"""
    v = (v or '').strip()
    if v.startswith('data:'):
        return v
    if not v:
        b64 = base64.b64encode(_PLACEHOLDER_SVG.encode('utf-8')).decode('ascii')
        return 'data:image/svg+xml;base64,' + b64
    p = os.path.join(ROOT, v.replace('/', os.sep))
    raw = open(p, 'rb').read()
    ext = os.path.splitext(p)[1].lstrip('.').lower() or 'jpeg'
    if ext == 'jpg':
        ext = 'jpeg'
    return 'data:image/%s;base64,' % ext + base64.b64encode(raw).decode('ascii')


def build_context(doc, prof):
    person = doc['person']
    variant = doc['variants'][prof['variant']]
    labels = person['contact_labels']
    contact = person['contact']

    order = variant.get('meta_rows') or person['meta_rows']
    meta_rows = []
    for row in order:
        kvs = []
        for i, k in enumerate(row):
            if k == 'base':
                kvs.append({'label': labels['base'].rstrip('：'),
                            'value': ' · '.join(contact[x] for x in row[i:])})
                break
            kvs.append({'label': labels[k].rstrip('：'), 'value': contact[k]})
        meta_rows.append(kvs)

    projects = []
    for pid in doc['project_order']:
        item = doc['projects'][pid]
        body = item[prof['variant']]
        projects.append({
            'name': body['name'], 'role': body['role'], 'date': item['date'],
            'pain': body['pain'], 'solutions': body['solutions'], 'values': body['values'],
        })

    return {
        'doc_title': prof['doc_title'],
        'person': person,
        'photo': resolve_photo(person.get('photo')),
        'intent': prof.get('intent') or variant['intent'],
        'meta_rows': meta_rows,
        'skills': [{'name': g, 'text': t} for g, t in variant['skills']],
        'work': [doc['work_blocks'][wid] for wid in prof['work']],
        'projects': projects,
        'education': doc['education'],
        'summary': variant['summary'],
    }


def check(html):
    problems = []
    body = html[html.index('<body'):]
    depth = body.count('<div') - body.count('</div>')
    if depth != 0:
        problems.append('div 深度差 %d' % depth)
    if html.count('<img class="photo"') != 1:
        problems.append('证件照 img 数 != 1')
    import re
    secs = len(re.findall(r'<h2[^>]*>', html))
    if secs != 5:
        problems.append('h2 章节数 %d != 5' % secs)
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('profile', nargs='?', help='只生成指定 profile（可选）')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--check', action='store_true', help='生成后做结构校验')
    args = ap.parse_args()

    doc = yaml.safe_load(io.open(DATA, encoding='utf-8'))
    env = Environment(loader=FileSystemLoader(TPLDIR), trim_blocks=True, lstrip_blocks=True,
                      keep_trailing_newline=True, autoescape=False)

    profiles = doc['profiles']
    if args.list:
        for k, v in profiles.items():
            print('%-12s %-14s %s' % (k, v.get('template', 'ai'), v['path']))
        return 0

    targets = [args.profile] if args.profile else list(profiles)
    bad = 0
    for key in targets:
        if key not in profiles:
            print('未知 profile:', key)
            return 2
        prof = profiles[key]
        tpl_name = 'layout_%s.html.j2' % prof.get('template', 'ai')
        tpl = env.get_template(tpl_name)
        html = tpl.render(**build_context(doc, prof))
        out = os.path.join(ROOT, prof['path'].replace('/', os.sep))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        io.open(out, 'w', encoding='utf-8', newline='\n').write(html)
        msg = '%-12s %-62s %8s 字符  [%s]' % (key, prof['path'], format(len(html), ','),
                                             prof.get('template', 'ai'))
        if args.check:
            probs = check(html)
            msg += ' | ' + ('结构 OK' if not probs else '；'.join(probs))
            bad += len(probs)
        print(msg)
    if bad:
        print('!! %d 项结构问题' % bad)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
