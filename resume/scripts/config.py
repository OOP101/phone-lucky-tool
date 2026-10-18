# -*- coding: utf-8 -*-
"""集中配置：路径、解释器候选、浏览器候选。

想换数据文件 / 模板目录 / 输出目录，或者本机 Python / 浏览器装在非常规位置，
改这一个文件即可，不用动构建脚本。
"""
import os
import shutil
import sys

# 项目根 = scripts/ 的上一级
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA = os.path.join(ROOT, 'resume_data.yaml')          # 内容数据源
TPLDIR = os.path.join(ROOT, 'resume_templates')        # Jinja2 模板目录
OUTPUT_DIR = os.path.join(ROOT, 'output')              # HTML / PDF 产物目录

# 生成器需要的解释器（需已安装 PyYAML + Jinja2）。
# 按顺序探测，谁 `import yaml, jinja2` 成功就用谁。
# 本机解释器装在非常规位置时，把绝对路径追加在列表最前即可，例如：
#   r'D:\software\Python311\python.exe'
PYTHON_CANDIDATES = [
    sys.executable,   # 当前运行 build_all.py 的解释器优先
    'python',
    'python3',
    'py',
]

# 导出 PDF 的浏览器（Chromium 内核，支持 --headless --print-to-pdf 即可）。
# 按顺序取第一个存在的；都不在 PATH/常见路径时，把绝对路径放最前。
BROWSER_CANDIDATES = [
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
]


def find_browser():
    """返回第一个可用的浏览器路径，找不到返回 None。"""
    for p in BROWSER_CANDIDATES:
        if p and os.path.exists(p):
            return p
    for name in ('msedge', 'chrome', 'chromium', 'chromium-browser', 'google-chrome'):
        w = shutil.which(name)
        if w:
            return w
    return None
