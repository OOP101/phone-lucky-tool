# -*- coding: utf-8 -*-
"""JD 关键词匹配：拿一份岗位 JD 对照你的简历数据源，看技能词覆盖情况。

用法：
    python scripts/jd_match.py jd.txt                       # JD 存为文本文件
    python scripts/jd_match.py jd.txt --md report.md        # 额外导出 Markdown 报告
    python scripts/jd_match.py jd.txt --lexicon my.txt      # 追加自定义词表
    python scripts/jd_match.py jd.txt --data other.yaml     # 指定其他数据源

原理与边界（先说清楚，免得误用）：
    1. 关键词来自两处：内置技能词表（中英混合，含常见别名，如
       「智能体 / AI 智能体 → agent」）+ JD 中的英文技术词自动抽取；
    2. 中文不做无监督分词（避免引入 jieba 等依赖与噪音），词表没覆盖的
       中文新词抓不到 —— 用 --lexicon 补你所在领域的词；
    3. 「缺失」≠ 一定要写进简历。缺失只说明 JD 提了、你的简历没提：
       真会 → 补进数据源；不会 → 当学习方向，面试别硬接。
    本工具是投递前的自查参考，不代表任何真实 ATS 系统的评分。
"""
import argparse
import io
import os
import re
import sys

try:
    import yaml
except ImportError:
    print('缺 PyYAML —— 请先 pip install pyyaml')
    raise SystemExit(2)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402  复用 ROOT / DATA

# ---------------------------------------------------------------- 词表
# canonical → [别名...]；匹配时任一别名命中即算命中，英文按词边界、中文按子串。
BUILTIN_LEXICON = {
    # --- 大模型 / Agent ---
    'llm': ['llm', 'large language model', '大模型', '大语言模型'],
    'agent': ['agent', '智能体'],
    'multi-agent': ['multi-agent', 'multi agent', '多智能体', '多 agent'],
    'rag': ['rag', '检索增强', '检索增强生成', '知识库问答'],
    'mcp': ['mcp', 'model context protocol'],
    'a2a': ['a2a'],
    'langchain': ['langchain'],
    'langgraph': ['langgraph'],
    'llamaindex': ['llamaindex', 'llama index'],
    'crewai': ['crewai'],
    'autogen': ['autogen'],
    'dify': ['dify'],
    'coze': ['coze', '扣子'],
    'fastgpt': ['fastgpt'],
    'ragflow': ['ragflow'],
    'prompt': ['prompt', '提示词', 'prompt工程', '提示词工程'],
    '上下文工程': ['上下文工程', 'context engineering'],
    'function calling': ['function calling', 'tool calling', '工具调用', '函数调用'],
    '微调': ['微调', 'fine-tune', 'fine-tuning', 'finetune', 'sft', 'lora', 'qlora'],
    'rlhf': ['rlhf', '强化学习'],
    'vllm': ['vllm'],
    'ollama': ['ollama'],
    '推理优化': ['推理优化', '推理加速', '模型压缩', '量化部署'],
    'transformer': ['transformer', '注意力机制', 'attention'],
    '多模态': ['多模态', 'multimodal', '多模态大模型'],
    'graphrag': ['graphrag', 'graph rag'],
    # --- RAG / 检索 ---
    'embedding': ['embedding', '向量化', '词向量'],
    'rerank': ['rerank', '重排序', '精排', 'reranker'],
    'bm25': ['bm25'],
    'rrf': ['rrf'],
    '向量数据库': ['向量数据库', '向量库', 'vector database', 'vector db'],
    'chromadb': ['chromadb', 'chroma'],
    'milvus': ['milvus'],
    'faiss': ['faiss'],
    'pgvector': ['pgvector'],
    'weaviate': ['weaviate'],
    '知识图谱': ['知识图谱', 'knowledge graph'],
    '文档解析': ['文档解析', '文档抽取'],
    '语义切分': ['语义切分', '分块', 'chunking', '切片'],
    '评测集': ['评测集', '评测体系', 'benchmark', 'eval set'],
    '意图识别': ['意图识别', '意图分类', 'intent'],
    '多轮对话': ['多轮对话', '多轮会话'],
    '记忆管理': ['记忆管理', '会话记忆', '长期记忆'],
    '结构化输出': ['结构化输出', 'json容错', 'structured output'],
    '数据标注': ['数据标注', '标注'],
    '数据清洗': ['数据清洗', '清洗'],
    'ocr': ['ocr'],
    # --- 后端 / 工程化 ---
    'python': ['python'],
    'fastapi': ['fastapi'],
    'flask': ['flask'],
    'django': ['django'],
    'java': ['java'],
    'spring': ['spring', 'springboot', 'spring boot'],
    'go': ['go', 'golang'],
    'javascript': ['javascript', 'js'],
    'typescript': ['typescript', 'ts'],
    'react': ['react'],
    'vue': ['vue'],
    'mysql': ['mysql'],
    'postgresql': ['postgresql', 'postgres'],
    'redis': ['redis'],
    'mongodb': ['mongodb', 'mongo'],
    'elasticsearch': ['elasticsearch', 'es'],
    'kafka': ['kafka'],
    'rabbitmq': ['rabbitmq'],
    '消息队列': ['消息队列', 'mq'],
    'spark': ['spark'],
    'flink': ['flink'],
    'etl': ['etl', '数据管道'],
    'docker': ['docker', '容器化', '容器部署'],
    'kubernetes': ['kubernetes', 'k8s'],
    'nginx': ['nginx'],
    'linux': ['linux'],
    'git': ['git'],
    'ci/cd': ['ci/cd', '持续集成', '持续交付'],
    'grpc': ['grpc'],
    'websocket': ['websocket', '长连接'],
    'sse': ['sse', '流式输出', '流式'],
    'restful': ['restful', 'rest api', '接口开发'],
    'jwt': ['jwt'],
    '微服务': ['微服务'],
    '高并发': ['高并发', '并发处理'],
    '分布式': ['分布式'],
    '熔断': ['熔断'],
    '降级': ['降级', '容灾'],
    '限流': ['限流', '流控'],
    '可观测性': ['可观测性', '监控告警', '监控'],
    '链路追踪': ['链路追踪', 'tracing'],
    # --- 测试 / 质量 ---
    '单元测试': ['单元测试', 'unit test'],
    '自动化测试': ['自动化测试', 'automation test'],
    '冒烟测试': ['冒烟测试'],
    '回归测试': ['回归测试', '回归验证'],
    '端到端测试': ['端到端测试', 'e2e测试', 'e2e'],
    '接口测试': ['接口测试'],
    '性能测试': ['性能测试'],
    '压力测试': ['压力测试', '压测'],
    '测试用例': ['测试用例', '用例设计'],
    '根因分析': ['根因分析', '根因定位'],
}

# JD 英文词抽取时的停用词（非技能词），小写。
STOPWORDS = set('''
the a an and or of to for with you your our we they is are be been was were
will would as at by on in from that this it its not do does doing done have
has had can could should may might must about into over under more most other
some such only own same than too very also based using use used new
ai api app web system systems platform solution solutions service services
experience work working works team teams candidate candidates job jobs role
roles position positions company companies year years month months
preferred requirement requirements required responsibility responsibilities
qualification qualifications benefit benefits salary interview resume hiring
apply strong excellent good great best plus etc via per
ability abilities skill skills knowledge understanding learning opportunity
environment related include includes including like well both each between
within across give given take make made help need needs let
design develop developer developing developed implement implemented
implementing maintain managed managing build building built join
bachelor master degree major computer science software
bad case
'''.split())

# 英文别名归一： 抽到的词 → canonical（与词表 canonical 对齐时自动合并）
_EN_WORD = re.compile(r'[a-z][a-z0-9+#./]{1,30}')


def normalize(text):
    """全角 → 半角、小写、去 HTML 标签、压缩空白。"""
    if not isinstance(text, str):
        return ''
    text = re.sub(r'<[^>]+>', ' ', text)                     # 去 HTML 标签
    out = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            ch = ' '
        elif 0xFF01 <= code <= 0xFF5E:
            code -= 0xFEE0
            ch = chr(code)
        out.append(ch)
    text = ''.join(out).lower()
    return re.sub(r'[ \t]+', ' ', text)


def _alias_pattern(alias):
    """英文别名按「非字母数字」定界，避免 go 误命中 good；中文直接子串。"""
    if re.fullmatch(r'[a-z0-9+#./\- ]+', alias):
        return re.compile(r'(?<![a-z0-9])' + re.escape(alias) + r'(?![a-z0-9])')
    return re.compile(re.escape(alias))


def load_lexicon(extra_path=None):
    """内置词表 + 可选自定义词表（每行 canonical|别名1|别名2，# 开头为注释）。"""
    lex = {k: list(v) for k, v in BUILTIN_LEXICON.items()}
    if extra_path:
        with io.open(extra_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if not parts:
                    continue
                canonical = parts[0].lower()
                lex.setdefault(canonical, [])
                lex[canonical] = lex[canonical] + [p.lower() for p in parts]
    return lex


def yaml_all_text(data):
    """递归收集 YAML 里所有字符串值，拼成一份简历全文。"""
    buf = []

    def walk(node):
        if isinstance(node, str):
            buf.append(node)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return normalize(' '.join(buf))


def extract_jd_keywords(jd_text, lexicon):
    """返回 OrderedDict: canonical → JD 提及次数（含别名合计）。"""
    text = normalize(jd_text)
    found = {}

    # 1) 词表（中英别名）
    for canonical, aliases in lexicon.items():
        count = 0
        for alias in aliases:
            count += len(_alias_pattern(alias).findall(text))
        if count:
            found[canonical] = count

    # 2) JD 里的英文技术词自动抽取（词表之外的兜底）
    for word in _EN_WORD.findall(text):
        if word in STOPWORDS or len(word) < 2:
            continue
        # 已被词表覆盖（本身或作为别名）则跳过
        covered = any(word == c or word in al for c, al in lexicon.items())
        if covered:
            continue
        found.setdefault(word, 0)
        found[word] += 1

    return found


def main():
    ap = argparse.ArgumentParser(description='JD 关键词匹配：简历数据源 vs 岗位 JD')
    ap.add_argument('jd_file', help='岗位 JD 文本文件（txt/md 均可）')
    ap.add_argument('--data', default=config.DATA, help='简历数据源 YAML（默认 resume_data.yaml）')
    ap.add_argument('--lexicon', default=None, help='自定义词表文件，每行 canonical|别名1|别名2')
    ap.add_argument('--md', default=None, help='额外导出 Markdown 报告到指定路径')
    args = ap.parse_args()

    if not os.path.exists(args.jd_file):
        print('JD 文件不存在:', args.jd_file)
        return 2
    if not os.path.exists(args.data):
        print('数据源不存在:', args.data)
        return 2

    jd_text = io.open(args.jd_file, encoding='utf-8').read()
    with io.open(args.data, encoding='utf-8') as f:
        data = yaml.safe_load(f)

    lexicon = load_lexicon(args.lexicon)
    resume_text = yaml_all_text(data)
    jd_keywords = extract_jd_keywords(jd_text, lexicon)

    hits, misses = [], []
    for canonical, count in jd_keywords.items():
        patterns = [_alias_pattern(a) for a in lexicon.get(canonical, [canonical])]
        if any(p.search(resume_text) for p in patterns):
            hits.append((canonical, count))
        else:
            misses.append((canonical, count))

    hits.sort(key=lambda x: -x[1])
    misses.sort(key=lambda x: -x[1])
    total = len(hits) + len(misses)
    rate = (100.0 * len(hits) / total) if total else 0.0

    person = (data.get('person') or {}).get('name', '?')
    lines = []
    lines.append('=' * 64)
    lines.append('JD 关键词匹配报告')
    lines.append('=' * 64)
    lines.append('简历数据源 : %s（%s）' % (os.path.basename(args.data), person))
    lines.append('JD 文件    : %s' % os.path.basename(args.jd_file))
    lines.append('覆盖率     : %.1f%%（命中 %d / %d）' % (rate, len(hits), total))
    lines.append('')
    lines.append('OK 已覆盖 %d 个（括号 = JD 提及次数）' % len(hits))
    lines.append('   ' + '  '.join('%s(%d)' % (c, n) for c, n in hits) if hits else '   （无）')
    lines.append('')
    lines.append('XX 未覆盖 %d 个（按 JD 提及频次降序）' % len(misses))
    lines.append('   ' + '  '.join('%s(%d)' % (c, n) for c, n in misses) if misses else '   （无）')
    lines.append('')
    lines.append('提示：缺失 ≠ 一定要写进简历。')
    lines.append('  · 真会 → 补进 resume_data.yaml 的技能区或相关项目；')
    lines.append('  · 不会 → 当作学习方向，面试别硬接。')
    report = '\n'.join(lines)
    print(report)

    if args.md:
        md = ['# JD 关键词匹配报告', '',
              '| 项目 | 内容 |', '|---|---|',
              '| 简历数据源 | %s（%s） |' % (os.path.basename(args.data), person),
              '| JD 文件 | %s |' % os.path.basename(args.jd_file),
              '| 覆盖率 | %.1f%%（命中 %d / %d） |' % (rate, len(hits), total), '',
              '## 已覆盖（%d）' % len(hits), '',
              '| 关键词 | JD 提及次数 |', '|---|---|'] + \
             ['| %s | %d |' % (c, n) for c, n in hits] + \
             ['', '## 未覆盖（%d）' % len(misses), '',
              '| 关键词 | JD 提及次数 |', '|---|---|'] + \
             ['| %s | %d |' % (c, n) for c, n in misses] + \
             ['', '> 缺失 ≠ 一定要写进简历：真会再补，不会当学习方向。']
        io.open(args.md, 'w', encoding='utf-8', newline='\n').write('\n'.join(md) + '\n')
        print('\nMarkdown 报告: %s' % args.md)

    return 0


if __name__ == '__main__':
    sys.exit(main())
