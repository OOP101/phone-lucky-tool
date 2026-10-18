"""知识库导入脚本：将 data/knowledge 下的文档批量向量化入库。

用法：python scripts/ingest.py
"""
import sys
import time
from pathlib import Path

# 允许以脚本方式运行时导入 app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.services import knowledge as kb_service  # noqa: E402

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"


def main():
    init_db()
    db = SessionLocal()
    files = sorted(KNOWLEDGE_DIR.glob("*")) if KNOWLEDGE_DIR.exists() else []
    supported = [f for f in files if f.is_file() and f.suffix.lower() in kb_service.SUPPORTED_EXT]

    if not supported:
        print(f"未在 {KNOWLEDGE_DIR} 找到可导入文档，请放入 txt/md/csv/pdf/docx 文件。")
        return

    payload = [(f.name, f.read_bytes()) for f in supported]
    print(f"开始批量导入 {len(payload)} 个文档（解析→分块→统一向量化→一次入库）...")

    start = time.time()

    def _progress(done, total, filename):
        if done % 100 == 0 or done == total:
            print(f"  解析进度 {done}/{total}")

    result = kb_service.add_documents_bulk(db, payload, progress=_progress)
    elapsed = time.time() - start

    print(
        f"导入完成：成功 {result['indexed']} 个文档 / {result['total_chunks']} 个分块，"
        f"耗时 {elapsed:.1f}s。"
    )
    for filename, reason in result["skipped"]:
        print(f"  ✘ {filename} 跳过：{reason}")


if __name__ == "__main__":
    main()
