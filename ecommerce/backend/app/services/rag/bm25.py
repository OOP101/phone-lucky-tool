"""纯 Python 实现的 BM25 关键词检索，无需外部依赖。"""
import math
from collections import Counter
from typing import List


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: List[List[str]] = []
        self.doc_len: List[int] = []
        self.avgdl: float = 0.0
        self.df: dict = {}
        self.idf: dict = {}
        self.N: int = 0

    def fit(self, corpus: List[List[str]]) -> None:
        self.corpus = corpus
        self.N = len(corpus)
        self.doc_len = [len(d) for d in corpus]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.df = {}
        # 预计算每文档词频与倒排表，避免 get_scores 重复构造 Counter（千级语料热点）
        self.tf: List[Counter] = [Counter(d) for d in corpus]
        self.postings: dict = {}
        for i, tfc in enumerate(self.tf):
            for term in tfc:
                self.df[term] = self.df.get(term, 0) + 1
                self.postings.setdefault(term, []).append((i, tfc[term]))
        self.idf = {
            t: math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)
            for t, df in self.df.items()
        }

    def get_scores(self, query_tokens: List[str]) -> List[float]:
        scores = [0.0] * self.N
        for term in query_tokens:
            idf = self.idf.get(term, 0.0)
            if idf == 0.0:
                continue
            for i, tf in self.postings.get(term, ()):
                denom = tf + self.k1 * (1 - self.b + self.b * self.doc_len[i] / self.avgdl)
                scores[i] += idf * (tf * (self.k1 + 1)) / denom
        return scores
