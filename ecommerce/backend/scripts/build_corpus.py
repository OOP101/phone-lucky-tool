"""知识库语料构建脚本：为文件库批量生产真实商品档案 + 领域知识文章。

数据源
------
1. 真实商品（products）：HuggingFace 公开数据集 ``cvnberk/amazon-products``
   （Amazon 美国站真实在售商品，23,993 条；字段：标题/类目/描述/售价/规格含 ASIN），
   经 qwen-turbo 批量翻译整理为中文商品知识文件。
2. 领域知识（knowledge）：qwen-turbo 按预置主题清单批量生成
   FAQ / 政策合规 / 跨境物流 / 平台运营 / Listing 文案五类中文文章。

用法
----
    python scripts/build_corpus.py products  [--limit 750] [--workers 5] [--refresh]
    python scripts/build_corpus.py knowledge [--workers 5]
    python scripts/build_corpus.py all

所有 API 响应均缓存到 data/raw/cache/，中断后重跑自动续传、不重复计费。
"""
import argparse
import concurrent.futures as futures
import hashlib
import json
import random
import re
import ssl
import sys
import time
from pathlib import Path

import httpx


def _build_ssl_context():
    """构建信任 Windows 系统证书库（含企业代理根证书）的 SSLContext。

    venv 内 httpx 默认只认 OpenSSL/certifi 自带根证书，企业网络的 TLS 代理
    会导致 CERTIFICATE_VERIFY_FAILED；这里把 Windows ROOT 证书库显式装入。
    若系统证书库不可用（非 Windows 等），回退 verify=False。
    """
    ctx = ssl.create_default_context()
    loaded = 0
    try:
        for der_bytes, _enc, _trust in ssl.enum_certificates("ROOT"):
            ctx.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(der_bytes))
            loaded += 1
    except Exception:  # noqa: BLE001
        pass
    return ctx if loaded else False


_SSL_CONTEXT = _build_ssl_context()


def http_client(timeout: float = 60.0) -> httpx.Client:
    return httpx.Client(timeout=timeout, verify=_SSL_CONTEXT)

# 允许以脚本方式运行时导入 app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

BACKEND_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BACKEND_DIR / "data" / "knowledge"
RAW_DIR = BACKEND_DIR / "data" / "raw"
CACHE_DIR = RAW_DIR / "cache"

LLM_BASE_URL = settings.LLM_BASE_URL.rstrip("/")
LLM_API_KEY = settings.LLM_API_KEY
LLM_MODEL = "qwen-turbo"  # 批量任务用 turbo：便宜、快

DATASET = "cvnberk/amazon-products"
ROWS_API = "https://datasets-server.huggingface.co/rows"
PAGES_CACHE = RAW_DIR / "raw_products_pages.jsonl"
SELECTED_CACHE = RAW_DIR / "selected_products.json"
TOTAL_ROWS = 23993

ASIN_RE = re.compile(r"B[0-9A-Z]{9}")

# 数据集中规格串里的标签（原数据空格被整体剥离，如 ProductDimensions:3x10x15inches）
SPEC_LABELS = {
    "productdimensions": "产品尺寸",
    "itemweight": "商品重量",
    "shippingweight": "发货重量",
    "domesticshipping": "美国境内配送",
    "internationalshipping": "国际配送",
    "asin": "ASIN",
    "itemmodelnumber": "型号",
    "itemmodel": "型号",
    "manufacturerrecommendedage": "建议适用年龄",
    "manufacturersuggestedage": "建议适用年龄",
    "batteries": "电池要求",
    "datefirstavailable": "首次上架日期",
    "department": "适用人群",
    "manufacturer": "制造商",
    "brandname": "品牌",
    "bestsellersrank": "畅销榜排名",
    "customerreviews": "客户评分",
    "language": "语言",
    "materialtype": "材质",
    "color": "颜色",
    "size": "尺寸",
    "numberofitems": "件数",
    "assemblyrequired": "是否需组装",
    "warranty": "质保",
}


# --------------------------------------------------------------------------
# LLM 调用（JSON 输出 + 重试 + 磁盘缓存）
# --------------------------------------------------------------------------
def chat_json(system_prompt: str, user_prompt: str, tag: str, retries: int = 4):
    """调用 qwen-turbo 返回解析后的 JSON 对象；按 tag 缓存原始响应。"""
    cache_file = CACHE_DIR / f"{tag}.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cache_file.unlink(missing_ok=True)

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    last_err = ""
    for attempt in range(retries):
        try:
            with http_client(timeout=httpx.Timeout(180.0, connect=30.0)) as client:
                resp = client.post(
                    f"{LLM_BASE_URL}/chat/completions", json=payload, headers=headers
                )
            if resp.status_code in (429, 500, 502, 503, 504):
                last_err = f"HTTP {resp.status_code}"
                time.sleep(2 ** attempt * 1.5)
                continue
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                time.sleep(2 ** attempt)
                continue
            content = resp.json()["choices"][0]["message"]["content"]
            data = _loose_json_loads(content)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
            return data
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt * 1.5)
    raise RuntimeError(f"LLM 调用失败 tag={tag}: {last_err}")


def _loose_json_loads(content: str):
    """宽松 JSON 解析：兼容代码块包裹与前后说明文字。"""
    content = content.strip()
    content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


# --------------------------------------------------------------------------
# 1) 真实商品：拉取数据集 -> 分层抽样 -> 翻译 -> 写中文档案
# --------------------------------------------------------------------------
def fetch_raw_pages(workers: int = 4, refresh: bool = False) -> list[dict]:
    if PAGES_CACHE.exists() and not refresh:
        rows = [
            json.loads(line)
            for line in PAGES_CACHE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        print(f"[products] 从缓存加载原始商品 {len(rows)} 条")
        return rows

    # HF /rows 接口 length 上限为 100，步长必须与 length 一致，
    # 否则 offset 按 500 步进只会拉到约 20% 的数据（4800/23993）。
    offsets = list(range(0, TOTAL_ROWS, 100))
    print(f"[products] 在线拉取数据集 {DATASET}，共 {len(offsets)} 页 ...")

    def _fetch(off: int) -> list[dict]:
        params = {
            "dataset": DATASET,
            "config": "default",
            "split": "train",
            "offset": str(off),
            "length": "100",
        }
        url = f"{ROWS_API}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        for attempt in range(4):
            try:
                with http_client() as client:
                    resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                return [r["row"] for r in resp.json()["rows"]]
            except Exception:  # noqa: BLE001
                time.sleep(1.5 * (attempt + 1))
        return []

    all_rows: list[dict] = []
    done = 0
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        tasks = {pool.submit(_fetch, off): off for off in offsets}
        for task in futures.as_completed(tasks):
            all_rows.extend(task.result())
            done += 1
            if done % 8 == 0:
                print(f"  拉取进度 {done}/{len(offsets)} 页，累计 {len(all_rows)} 条")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with PAGES_CACHE.open("w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[products] 拉取完成，共 {len(all_rows)} 条，已缓存到 {PAGES_CACHE}")
    return all_rows


def parse_specs(raw: str) -> dict:
    """把 'ProductDimensions:3x10x15inches|ASIN:B0...' 解析成 {中文标签: 原值}。"""
    out = {}
    for part in (raw or "").split("|"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        label = SPEC_LABELS.get(key.strip().lower())
        value = value.strip()
        if label and value:
            out[label] = value
    return out


def select_products(rows: list[dict], target: int) -> list[dict]:
    """质量过滤 + ASIN 去重 + 按一级类目分层抽样。"""
    seen_asin: set[str] = set()
    candidates: list[dict] = []
    for row in rows:
        name = (row.get("Product Name") or "").strip()
        desc = (row.get("Description") or "").strip()
        specs_raw = row.get("Product Specification") or ""
        m = ASIN_RE.search(specs_raw)
        if not m:
            continue
        asin = m.group(0)
        if asin in seen_asin:
            continue
        if not (8 <= len(name) <= 220 and 40 <= len(desc) <= 1500):
            continue
        seen_asin.add(asin)
        cat = (row.get("Category") or "未分类").strip() or "未分类"
        candidates.append(
            {
                "asin": asin,
                "name": name,
                "category": cat,
                "top_category": cat.split("|")[0].strip(),
                "price": (row.get("Selling Price") or "").strip(),
                "description": desc,
                "specs": parse_specs(specs_raw),
            }
        )

    rng = random.Random(42)
    rng.shuffle(candidates)
    # 类目配额：抑制玩具类目一家独大，保证跨境常见品类覆盖
    caps = {
        "Toys & Games": 380,
        "Home & Kitchen": 95,
        "Sports & Outdoors": 80,
        "Clothing, Shoes & Jewelry": 60,
        "Baby Products": 40,
        "Arts, Crafts & Sewing": 25,
        "Office Products": 18,
        "Tools & Home Improvement": 12,
        "Patio, Lawn & Garden": 10,
        "Electronics": 10,
        "Industrial & Scientific": 10,
        "Video Games": 8,
        "Beauty & Personal Care": 8,
        "Health & Household": 8,
        "Musical Instruments": 6,
        "Pet Supplies": 6,
        "Automotive": 6,
    }
    selected: list[dict] = []
    by_cat: dict[str, list[dict]] = {}
    for item in candidates:
        by_cat.setdefault(item["top_category"], []).append(item)
    for cat, items in by_cat.items():
        selected.extend(items[: min(len(items), caps.get(cat, 6))])

    if len(selected) < target:
        picked_asin = {p["asin"] for p in selected}
        for item in candidates:
            if len(selected) >= target:
                break
            if item["asin"] not in picked_asin:
                selected.append(item)
                picked_asin.add(item["asin"])
    selected = selected[:target]
    selected.sort(key=lambda x: (x["top_category"], x["asin"]))

    SELECTED_CACHE.write_text(
        json.dumps(selected, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    from collections import Counter

    dist = Counter(p["top_category"] for p in selected)
    print(f"[products] 抽样 {len(selected)} 个商品，类目分布：")
    for cat, n in dist.most_common():
        print(f"    {n:4d}  {cat}")
    return selected


PRODUCT_SYS = (
    "你是资深跨境电商商品资料编译专家，负责把 Amazon 美国站英文商品资料整理成规范中文档案。"
    "只做翻译与结构化整理，严禁编造商品不具备的功能、认证或参数；数字、型号、ASIN 必须原样保留。"
    "输出简体中文，术语专业（如 dimensions=尺寸、ounces=盎司、batteries=电池要求）。"
)

PRODUCT_USER_TMPL = """请把下面 {n} 个商品整理为中文资料，严格输出 JSON 对象：
{{"items":[{{"idx":序号,"name_zh":"中文品名（保留品牌/型号原文，20-40字）","brand":"品牌英文名，没有则填未标注","category_zh":"中文类目路径，用 > 连接","specs_zh":["参数名：中文值，每条一个具体参数"],"desc_zh":"商品描述中文，120-220字，保留关键数字与卖点","highlights":["3-5条中文核心卖点，每条15-30字"]}}]}}

要求：
1. specs_zh 从给定规格中提取 4-8 条有信息量的参数（尺寸/重量/型号/年龄/材质/电池等），单位换算为中文习惯写法（如 inches→英寸、ounces→盎司、pounds→磅）；不要包含配送范围类信息。
2. 规格原文普遍缺失空格，请自行正确断词；无意义的模板文字直接丢弃。
3. desc_zh 不要逐条直译，要整理成通顺的中文商品描述。
4. idx 必须与输入商品序号一一对应，不得遗漏。

商品清单：
{items_json}
"""


def translate_batch(batch: list[dict]) -> dict[int, dict]:
    # 缓存键按批次内 ASIN 集合取哈希：抽样规模变化导致序号重排时不会错用旧缓存
    asin_key = hashlib.md5(
        ",".join(p["asin"] for p in batch).encode("utf-8")
    ).hexdigest()[:12]
    data = chat_json(
        PRODUCT_SYS,
        PRODUCT_USER_TMPL.format(
            n=len(batch),
            items_json=json.dumps(
                [
                    {
                        "idx": p["seq"],
                        "name": p["name"],
                        "category": p["category"],
                        "price": p["price"] or "未标注",
                        "specs": p["specs"],
                        "description": p["description"],
                    }
                    for p in batch
                ],
                ensure_ascii=False,
            ),
        ),
        tag=f"products_{asin_key}",
    )
    out = {}
    for item in data.get("items", []):
        try:
            out[int(item["idx"])] = item
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _humanize_shipping(label_cn: str, raw: str) -> str | None:
    """把数据集中缺空格的物流模板句归一化为中文短语。"""
    v = raw.lower().replace(" ", "")
    v = v.replace("learnmore", "")
    if label_cn == "美国境内配送":
        if "cannot" in v or "cannotbeshipped" in v:
            return "不支持美国境内配送"
        if "withinu.s" in v or "withinunitedstates" in v:
            return "支持美国境内配送"
        return None
    if label_cn == "国际配送":
        if "selectcountriesoutside" in v or "countriesoutside" in v:
            return "支持配送至美国以外的部分国家"
        if "cannot" in v or "notavailable" in v:
            return "暂不支持国际配送"
        return None
    return None


def render_product_md(product: dict, zh: dict | None) -> str:
    asin = product["asin"]
    if not zh:
        zh = {}
    name_zh = (zh.get("name_zh") or product["name"]).strip()
    brand = (zh.get("brand") or "未标注").strip() or "未标注"
    category_zh = (zh.get("category_zh") or product["category"]).strip()

    specs_zh = [str(s).strip() for s in (zh.get("specs_zh") or []) if str(s).strip()]
    specs_zh = specs_zh[:8]
    if not specs_zh:
        specs_zh = [f"{k}：{v}" for k, v in list(product["specs"].items())[:6] if k != "ASIN"]

    highlights = [str(s).strip() for s in (zh.get("highlights") or []) if str(s).strip()][:5]
    desc = (zh.get("desc_zh") or "").strip()
    if len(desc) > 320:
        desc = desc[:320].rsplit("。", 1)[0] + "。"

    lines = [
        f"# 商品档案：{name_zh}",
        "",
        "## 基础信息",
        f"- ASIN：{asin}",
        f"- 品牌：{brand}",
        f"- 商品类目：{category_zh}",
        f"- 参考售价：{product['price'] or '未标注'}",
        "- 在售站点：Amazon.com（美国站）",
        "",
        "## 规格参数",
    ]
    lines.extend(f"- {s if ('：' in s or ':' in s) else s}" for s in specs_zh)
    lines.extend(["", "## 商品描述", desc or product["description"][:300]])
    if highlights:
        lines.extend(["", "## 核心卖点"])
        lines.extend(f"- {s}" for s in highlights)

    domestic_raw = product["specs"].get("美国境内配送")
    intl_raw = product["specs"].get("国际配送")
    domestic = _humanize_shipping("美国境内配送", domestic_raw) if domestic_raw else None
    intl = _humanize_shipping("国际配送", intl_raw) if intl_raw else None
    if domestic or intl:
        lines.extend(["", "## 物流备注"])
        if domestic:
            lines.append(f"- 美国境内配送：{domestic}")
        if intl:
            lines.append(f"- 国际配送：{intl}")
    lines.append("")
    return "\n".join(lines)


def build_products(limit: int, workers: int, refresh: bool):
    rows = fetch_raw_pages(refresh=refresh)
    selected = select_products(rows, limit)
    for i, p in enumerate(selected):
        p["seq"] = i

    batches = [selected[i : i + 10] for i in range(0, len(selected), 10)]
    print(f"[products] 开始翻译 {len(selected)} 个商品（{len(batches)} 批，并发 {workers}）...")
    translated: dict[int, dict] = {}
    done = 0
    t0 = time.time()
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        tasks = {pool.submit(translate_batch, b): b for b in batches}
        for task in futures.as_completed(tasks):
            batch = tasks[task]
            try:
                translated.update(task.result())
            except Exception as e:  # noqa: BLE001
                print(f"  ! 批次 {batch[0]['seq']} 失败，将用原文兜底：{e}")
            done += 1
            if done % 10 == 0 or done == len(batches):
                print(f"  翻译进度 {done}/{len(batches)} 批，用时 {time.time()-t0:.0f}s")

    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for p in selected:
        zh = translated.get(p["seq"])
        (KNOWLEDGE_DIR / f"prod_{p['asin']}.md").write_text(
            render_product_md(p, zh), encoding="utf-8"
        )
        written += 1
    print(f"[products] 完成，写入 {written} 个商品档案到 {KNOWLEDGE_DIR}")


# --------------------------------------------------------------------------
# 2) 领域知识文章：预置 250 个主题 -> qwen-turbo 批量生成
# --------------------------------------------------------------------------
KNOWLEDGE_TOPICS: dict[str, list[str]] = {
    "faq": [
        "现货订单处理时效与发货流程",
        "预售与定制商品的交期说明",
        "订单状态查询、改单与拆单规则",
        "取消订单与订单冻结规则",
        "物流单号获取与在途追踪方法",
        "国际快递 DHL、FedEx、UPS 的选择与时效对比",
        "国际专线物流与邮政小包的适用场景",
        "国际空运流程、时效与计费方式",
        "海运拼箱 LCL 的操作流程",
        "海运整柜 FCL 与柜型选择（20GP/40GP/40HQ）",
        "铁运、卡航与多式联运的选择",
        "物流延误、异常件与丢件处理",
        "目的国清关流程与常见扣货原因",
        "商业发票与装箱单的制作要点",
        "正本提单、电放提单与海运单的区别",
        "目的港费用明细与换单流程",
        "关税预缴（DDP）与到付（DDU）的区别",
        "欧洲进口增值税 VAT 与 EORI 号",
        "美国进口关税与 HS 编码查询方法",
        "欧盟 IOSS/OSS 与低价值货物申报",
        "T/T 电汇的流程、比例与风控",
        "信用证 L/C 流程与常见软条款",
        "PayPal 外贸收款的规则与风控",
        "西联汇款与速汇金的使用",
        "贸易术语 EXW、FCA、FOB 的区别",
        "CIF、CFR、DAP、DDP 术语对比",
        "报价单的构成与报价有效期",
        "样品费、打样费与大货抵扣规则",
        "MOQ 起订量与混批拿货规则",
        "阶梯报价、账期与付款方式谈判",
        "CE 认证的适用范围与办理流程",
        "FCC 认证与 SDoC 符合性声明",
        "FDA 注册：食品接触材料、化妆品与医疗器械",
        "RoHS 2.0 有害物质限制要求",
        "REACH 法规与 SVHC 高度关注物质",
        "英国 UKCA 标识与脱欧后合规",
        "日本 PSE、PSC 与电波法认证",
        "美国儿童产品 CPSIA、CPC 证书与 ASTM 测试",
        "加州 65 号提案警示要求",
        "能效合规：美国 DOE、加拿大 NRCan、欧盟 ERP",
        "电池运输的 UN38.3、MSDS 与危包证",
        "化妆品欧盟 CPNP 通报与美国 MoCRA",
        "包装材料要求与木质包装 ISPM15 熏蒸",
        "一般原产地证 CO、FORM 证书与 RCEP 原产地证",
        "第三方质检报告与装船前验货",
        "ISO9001 质量体系与验厂审核",
        "质量异议期与索赔需要的证据",
        "退换货流程与退货运费承担",
        "FBA 退货与海外仓退货的处理方式",
        "补发、补货与折扣补偿的适用场景",
        "退款时效、原路退回与手续费",
        "电子产品保修政策的制定与执行",
        "破损与丢件的保险理赔流程",
        "差评、纠纷升级与平台介入处理",
        "OEM 与 ODM 的区别及定制流程",
        "打样周期、样品确认与封样",
        "LOGO 工艺：丝印、激光雕刻与刺绣",
        "定制包装、彩盒结构与设计规范",
        "贴标、换标与外箱唛头规范",
        "中性包装与白牌产品出口",
        "亚马逊开店资料、注册流程与审核",
        "亚马逊二审、KYC 与视频验证",
        "Listing 上架被拒的常见原因",
        "亚马逊变体关系与合并规则",
        "Buy Box 购物车的赢得条件",
        "账号绩效：ODR、迟发率与取消率",
        "Review 评论政策与 Vine 计划",
        "跟卖的应对方法与品牌备案",
        "FBA 入库要求、箱规与货件限制",
        "FBA 库存移除、弃置与清算",
        "亚马逊多站点运营与各国税务",
        "多账号关联风险与防关联措施",
        "侵权投诉：商标、专利与版权",
        "受限商品与类目审核要求",
        "广告扣费异常与超预算处理",
        "样品试用、红人测评与网红营销",
        "优惠券、促销与秒杀活动申报",
        "黑五网一等 Q4 节日营销节奏",
        "站外引流、Deal 站与折扣发帖",
        "独立站收款与 PayPal 风控冻结",
        "体积重计算与计费重规则",
        "敏感货、带电产品与带磁产品发货",
        "海外仓一件代发流程",
        "本地退货地址与退换货方案",
        "跨境物流保险种类与承保范围",
        "旺季排仓、涨价窗口与备货节奏",
        "美森快船、以星快船与普船的区别",
        "欧洲 VAT 递延与清关行选择",
        "英国脱欧后的清关变化",
        "巴西、墨西哥清关难点与税号",
        "中东清关与 SASO/SABER 认证",
        "东南亚 COD 货到付款模式",
        "跨境电商 B2B 与 B2C 的区别",
        "选品的数据维度与调研方法",
        "单品利润核算：头程、佣金、广告与退货",
        "汇率波动与报价调整策略",
        "外汇结汇方式与合规收款渠道",
        "出口退税的条件与流程",
        "跨境电商团队分工与岗位职责",
        "新手跨境卖家的起步路线图",
        "Temu 全托管与半托管模式的入驻、供货与结算",
        "TikTok Shop 跨境店入驻要求与结算周期",
        "出口信用保险投保与外贸坏账追偿流程",
        "香港公司与离岸账户在跨境收款中的使用",
    ],
    "policy": [
        "欧盟 CE 标志制度总览",
        "欧盟 GPSR 通用产品安全条例（2024 年生效）",
        "欧盟 REACH 法规合规实务",
        "欧盟 RoHS 2.0 指令解读",
        "欧盟 WEEE 电子废弃物回收指令",
        "欧盟 EPR 生产者责任延伸制度（德国/法国包装、电子、纺织）",
        "德国包装法 VerpackG 注册与申报",
        "法国 AGEC 反浪费法与 EPR 义务",
        "欧盟电池法规 EU 2023/1542",
        "欧盟玩具安全指令 2009/48/EC 与 EN 71 测试",
        "欧盟医疗器械法规 MDR",
        "欧盟化妆品法规 EC 1223/2009 与 CPNP",
        "欧盟食品接触材料法规 EC 1935/2004",
        "欧盟无线电设备指令 RED 2014/53/EU",
        "欧盟电磁兼容 EMC 指令 2014/30/EU",
        "欧盟 GDPR 通用数据保护条例",
        "欧盟电子隐私与 Cookie 同意规则",
        "欧盟增值税改革：OSS 与 IOSS 机制",
        "英国 UKCA 合规体系与过渡安排",
        "英国 VAT 注册与 MTD 电子申报",
        "美国 FCC 法规 Part 15 与认证方式",
        "美国 FDA 食品接触材料监管（FCM）",
        "美国 CPSIA 儿童产品安全改进法案",
        "美国加州 65 号提案合规警示",
        "美国 DOE 能效标准与外置电源能效等级",
        "美国 FTC 标签、原产地标识与广告合规",
        "美国海关 ISF 10+2 申报规则",
        "美国 301 关税清单、加征与豁免申请",
        "美国 337 调查与知识产权边境保护",
        "美国 CPSC 召回流程与义务",
        "日本 PSE 认证：菱形与圆形的区别",
        "日本食品卫生法与食品接触肯定列表",
        "日本电波法 GITEKI 技适标志与 METI 备案",
        "日本 JCT 消费税合规与发票制度",
        "加拿大 ISED（原 IC）无线认证",
        "加拿大玩具条例 SOR/2011-17",
        "澳大利亚 RCM、ACMA 与 SAA 认证",
        "新西兰 AS/NZS 标准与合规路径",
        "沙特 SASO、SABER 平台与 IECEE 认可",
        "海湾国家 G-Mark 认证要求",
        "印度 BIS 认证与强制注册 CRS",
        "韩国 KC 认证体系",
        "墨西哥 NOM 强制认证",
        "巴西 INMETRO 与 ANATEL 认证",
        "HS 编码归类实务与争议处理",
        "原产地规则与 RCEP 关税减让安排",
        "跨境知识产权：马德里商标与 PCT 专利",
        "木质包装 ISPM15 与熏蒸证书",
        "危险品运输 IMDG 与 IATA DGR 分类",
        "贸易制裁与出口管制：OFAC 与实体清单",
        "美国低值包裹 de minimis 免税政策调整与跨境小包影响",
        "美国 UFLPA 强迫劳动预防法与供应链尽调要求",
    ],
    "logistics": [
        "FBA 头程物流方案对比与选择",
        "海运整柜操作全流程",
        "海运拼箱计费方式、亏舱费与注意事项",
        "美森、以星快船与普通船的时效和选船策略",
        "国际空运操作流程与计费重计算",
        "国际快递账号体系与折扣获取",
        "中欧班列操作实务",
        "欧洲卡航派送渠道",
        "海外仓选址与多国库存布局",
        "海外仓一件代发操作流程",
        "FBA 入仓规则与货件创建流程",
        "FBA 箱规、托盘要求与超重限制",
        "亚马逊 AGL 全球物流服务",
        "商业发票 Commercial Invoice 制作要点",
        "装箱单、合同与单单一致原则",
        "出口报关单证与报关流程",
        "跨境电商监管方式 9610、9710、9810 对比",
        "清关代理的选择与 POA 授权",
        "关税测算方法与反倾销税",
        "DDP 贸易术语下的清关风险",
        "目的港杂费明细：THC、DO、ORC",
        "滞箱费、滞港费与免柜免堆期",
        "跨境货物保险与理赔流程",
        "带电产品可走的物流渠道",
        "纯电池与移动电源出货要求",
        "液体、粉末等敏感货渠道",
        "超大件家具与健身器材物流",
        "跨境冷链物流简介",
        "出口退运与返修货物流程",
        "旺季物流排仓与备货节奏",
        "物流轨迹节点状态解读",
        "丢件破损索赔的证据链",
        "关税预付与买家拒付的处理",
        "货代报价单的阅读与比价",
        "最后一公里派送商对比：UPS、FedEx、USPS 与 Royal Mail",
        "FBA 货件被分仓的原因与合仓方案",
    ],
    "ops": [
        "亚马逊全球开店的站点规划",
        "亚马逊账号注册资料与防关联",
        "账户健康度（Account Health）指标体系",
        "亚马逊二审、视频验证与地址明信片",
        "亚马逊品牌备案 Brand Registry",
        "Listing 标题规则与写作方法",
        "五点描述与产品详情页规则",
        "后台 Search Terms 关键词填写",
        "A+ 页面与品牌旗舰店搭建",
        "类目审核与安全数据表 SDS",
        "亚马逊变体政策与滥用风险",
        "Listing 合并与僵尸 Listing 风险",
        "亚马逊定价策略与自动定价工具",
        "Buy Box 购物车竞争机制",
        "SP 商品推广广告基础架构",
        "SB 品牌推广与 SD 展示型广告",
        "ACOS 与 TACOS 指标优化",
        "Coupon、Promotion 与 Deal 设置",
        "Prime 专享折扣、LD 与 7DD",
        "Amazon Vine 计划与早期评论",
        "Review 获取的合规边界",
        "站内信规则与 24 小时回复时限",
        "FBA 库存绩效指标 IPI",
        "库存周转与滞销库存清理",
        "FBA 移除订单与清算渠道",
        "FBA 超龄库存附加费",
        "亚马逊危险品审核 Hazmat",
        "受限商品与农药设备误判申诉",
        "账号冻结申诉与 POA 行动计划",
        "侵权投诉与 DMCA 通知应对",
        "跟卖机制与合规驱赶方法",
        "Test Buy 与差评处理的合规边界",
        "BSR 畅销榜排名机制",
        "亚马逊业务报告数据解读",
        "多账号操作的合规风险",
        "欧洲站 VAT 税号上传与代扣代缴",
        "日本站合规要求与 JCT 税号",
        "中东、新加坡与澳洲站点要点",
        "Amazon Business 企业购业务",
        "独立站与亚马逊平台的多渠道布局",
        "Amazon Posts 品牌帖子与免费流量运营",
    ],
    "copy": [
        "亚马逊 Listing 标题写作公式",
        "五点描述（Bullet Points）写作模板",
        "A+ 产品描述文案结构",
        "智能家居类英文 Listing 文案范例",
        "户外露营类英文 Listing 文案范例",
        "3C 电子类英文 Listing 文案范例",
        "母婴用品类英文 Listing 文案范例",
        "美妆个护类英文 Listing 文案范例",
        "家居厨房类英文 Listing 文案范例",
        "宠物用品类英文 Listing 文案范例",
        "工具汽配类英文 Listing 文案范例",
        "服装鞋包类英文 Listing 文案范例",
        "玩具品类英文 Listing 文案范例",
        "B2B 英文开发信模板",
        "外贸询盘回复话术模板",
        "外贸催款邮件模板",
        "售后道歉与补发邮件模板",
        "合规邀评站内信模板",
        "旺季促销社交媒体文案",
        "Facebook 广告文案结构",
        "TikTok 短视频带货口播脚本",
        "跨境电商关键词调研与埋词策略",
        "从竞品差评挖掘产品卖点",
        "品牌故事 Brand Story 的写法",
        "多语言本地化翻译要点",
        "独立站弃购挽回邮件（Abandoned Cart Email）模板",
    ],
}

KNOWLEDGE_SYS = (
    "你是跨境电商行业知识专家，长期服务中国制造企业出海。"
    "请根据指定主题撰写可直接入库的中文知识库文章，要求：内容准确专业、结构清晰、可落地执行；"
    "善用条款号、具体数字、流程步骤、清单与对比；不写空泛套话；"
    "不编造具体公司名称；输出简体中文 Markdown。"
)

KNOWLEDGE_USER_TMPL = """请撰写以下 {n} 篇跨境电商知识库文章，严格输出 JSON 对象：
{{"items":[{{"idx":序号,"content":"文章全文 Markdown，必须以 # 标题 开头"}}]}}

每篇要求：
1. 450-800 字；标题用「# 主题名」开头，正文包含 3-6 个 ## 二级小节；
2. 多用步骤、清单、表格（表格不超过 5 行）、具体数字与法规/认证条款号；
3. 面向中国跨境电商卖家与外贸业务员，直接回答实际怎么做；
4. idx 必须与下列序号一一对应，不得遗漏或合并；
5. JSON 字符串内换行用 \\n 转义。

主题清单：
{topics_json}
"""


def generate_knowledge_batch(prefix: str, batch: list[tuple[int, str]]) -> dict[int, str]:
    start = batch[0][0]
    data = chat_json(
        KNOWLEDGE_SYS,
        KNOWLEDGE_USER_TMPL.format(
            n=len(batch),
            topics_json=json.dumps(
                [{"idx": idx, "topic": title} for idx, title in batch],
                ensure_ascii=False,
            ),
        ),
        tag=f"{prefix}_{start:03d}",
    )
    out = {}
    for item in data.get("items", []):
        try:
            idx = int(item["idx"])
            content = str(item.get("content") or "").strip()
            if content.startswith("#"):
                out[idx] = content
        except (KeyError, TypeError, ValueError):
            continue
    return out


def build_knowledge(workers: int):
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    total = sum(len(v) for v in KNOWLEDGE_TOPICS.values())
    print(f"[knowledge] 计划生成 {total} 篇知识文章（FAQ/政策/物流/运营/文案）")

    all_batches = []
    for prefix, titles in KNOWLEDGE_TOPICS.items():
        indexed = list(enumerate(titles, start=1))
        for i in range(0, len(indexed), 5):
            all_batches.append((prefix, indexed[i : i + 5]))

    contents: dict[tuple[str, int], str] = {}
    done = 0
    t0 = time.time()
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        tasks = {
            pool.submit(generate_knowledge_batch, prefix, batch): (prefix, batch)
            for prefix, batch in all_batches
        }
        for task in futures.as_completed(tasks):
            prefix, batch = tasks[task]
            try:
                result = task.result()
                for idx, content in result.items():
                    contents[(prefix, idx)] = content
            except Exception as e:  # noqa: BLE001
                print(f"  ! {prefix} 批次 {batch[0][0]} 失败：{e}")
            done += 1
            if done % 10 == 0 or done == len(all_batches):
                print(f"  生成进度 {done}/{len(all_batches)} 批，用时 {time.time()-t0:.0f}s")

    # 补缺：对缺失主题做最多两轮单批补生成
    missing = [
        (prefix, idx, title)
        for prefix, titles in KNOWLEDGE_TOPICS.items()
        for idx, title in enumerate(titles, start=1)
        if (prefix, idx) not in contents
    ]
    for repair_round in range(2):
        if not missing:
            break
        print(f"[knowledge] 第 {repair_round+1} 轮补缺 {len(missing)} 篇 ...")
        # 补缺数量通常很小，直接串行补生成
        for prefix, idx, title in missing:
            try:
                result = generate_knowledge_batch(prefix, [(idx, title)])
                if idx in result:
                    contents[(prefix, idx)] = result[idx]
            except Exception:  # noqa: BLE001
                pass
        missing = [
            (prefix, idx, title)
            for prefix, titles in KNOWLEDGE_TOPICS.items()
            for idx, title in enumerate(titles, start=1)
            if (prefix, idx) not in contents
        ]

    written = 0
    for (prefix, idx), content in sorted(contents.items()):
        (KNOWLEDGE_DIR / f"{prefix}_{idx:03d}.md").write_text(
            content.rstrip() + "\n", encoding="utf-8"
        )
        written += 1
    if missing:
        print(f"[knowledge] 警告：仍有 {len(missing)} 篇未生成：{missing[:10]}")
    print(f"[knowledge] 完成，写入 {written} 篇文章到 {KNOWLEDGE_DIR}")


def main():
    parser = argparse.ArgumentParser(description="知识库语料构建")
    parser.add_argument("target", choices=["products", "knowledge", "all"])
    parser.add_argument("--limit", type=int, default=750, help="商品档案数量（默认 750）")
    parser.add_argument("--workers", type=int, default=5, help="LLM 并发数（默认 5）")
    parser.add_argument("--refresh", action="store_true", help="忽略缓存重新拉取数据集")
    args = parser.parse_args()

    if not LLM_API_KEY:
        print("错误：未配置 LLM_API_KEY（backend/.env），无法调用 qwen-turbo。")
        sys.exit(1)

    if args.target in ("products", "all"):
        build_products(args.limit, args.workers, args.refresh)
    if args.target in ("knowledge", "all"):
        build_knowledge(args.workers)


if __name__ == "__main__":
    main()
