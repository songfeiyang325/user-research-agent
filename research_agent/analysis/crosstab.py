"""交叉分析（原 xiaoju-survey 无此能力，从零实现）。

给定两道"分类型"题目（单选/多选/判断/投票/评分），统计它们的联合分布（列联表），
并算卡方与 Cramér's V（关联强度）。多选题按数组展开成多个 (A,B) 组合计数。
"""
from __future__ import annotations

import numpy as np
from scipy.stats import chi2_contingency

_CHOICE = {"radio", "checkbox", "binary-choice", "vote"}


def categories(q: dict) -> list[tuple[str, str]]:
    """返回题目的类别 [(值, 展示文案)]。选项用 hash，评分用分值。"""
    if q["type"] in _CHOICE:
        return [(o["hash"], o["text"]) for o in q.get("options", [])]
    if q["type"] == "radio-star":
        hi = int(q.get("starMax", 5) or 5)
        return [(str(v), f"{v}星") for v in range(1, hi + 1)]
    if q["type"] == "radio-nps":
        lo, hi = int(q.get("min", 0) or 0), int(q.get("max", 10) or 10)
        return [(str(v), str(v)) for v in range(lo, hi + 1)]
    return []


def _values(q: dict, r: dict) -> list[str]:
    v = r.get(q["field"])
    if v in (None, "", []):
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def crosstab(qa: dict, qb: dict, responses: list[dict]) -> dict:
    cats_a, cats_b = categories(qa), categories(qb)
    idx_a = {h: i for i, (h, _) in enumerate(cats_a)}
    idx_b = {h: i for i, (h, _) in enumerate(cats_b)}

    matrix = np.zeros((len(cats_a), len(cats_b)), dtype=int)
    for r in responses:
        avs = [a for a in _values(qa, r) if a in idx_a]
        bvs = [b for b in _values(qb, r) if b in idx_b]
        for a in avs:
            for b in bvs:
                matrix[idx_a[a], idx_b[b]] += 1

    result: dict = {
        "rowLabels": [t for _, t in cats_a],
        "colLabels": [t for _, t in cats_b],
        "matrix": matrix.tolist(),
        "rowTitle": qa["title"],
        "colTitle": qb["title"],
    }

    # 卡方 + Cramér's V（需无零边际、且行列均≥2）
    if (
        matrix.sum() > 0
        and matrix.shape[0] > 1
        and matrix.shape[1] > 1
        and (matrix.sum(axis=1) > 0).all()
        and (matrix.sum(axis=0) > 0).all()
    ):
        chi2, p, _dof, _exp = chi2_contingency(matrix)
        n = int(matrix.sum())
        k = min(matrix.shape) - 1
        result["chi2"] = round(float(chi2), 3)
        result["pValue"] = round(float(p), 4)
        result["cramersV"] = round(float((chi2 / (n * k)) ** 0.5), 3) if k > 0 else None
    return result
