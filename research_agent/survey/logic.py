"""显示逻辑：从简化描述构造规则 + 求值。

规则结构对齐 xiaoju-survey：{target, scope, conditions:[{field, operator, value[]}]}。
本模块是 Python 侧（供构造/测试/校验）；前端 frontend/src/logic.js 是等价镜像。
operator：in=选了任一 / eq=选了全部 / nin=有未选的 / neq=都没选。
"""
from __future__ import annotations

from .schema import Condition, LogicRule, Question

_OPS = {"in", "nin", "eq", "neq"}


def build_show_logic(questions: list[Question], logic_spec: list[dict] | None) -> list[LogicRule]:
    """把简化逻辑 [{show, when, op, options}] 转成 LogicRule 列表（用题目序号+选项文本）。"""
    rules: list[LogicRule] = []
    n = len(questions)
    for item in logic_spec or []:
        try:
            show = int(item["show"])
            when = int(item["when"])
        except (KeyError, TypeError, ValueError):
            continue
        op = item.get("op", "in")
        if op not in _OPS or not (1 <= show <= n) or not (1 <= when <= n) or show == when:
            continue
        target, driver = questions[show - 1], questions[when - 1]
        opt_texts = set(item.get("options") or [])
        value = [o.hash for o in driver.options if o.text in opt_texts]
        if not value:
            continue
        rules.append(
            LogicRule(
                target=target.field,
                scope="question",
                conditions=[Condition(field=driver.field, operator=op, value=value)],
            )
        )
    return rules


def _selected(v) -> set[str]:
    if v is None or v == "":
        return set()
    if isinstance(v, list):
        return {str(x) for x in v}
    return {str(v)}


def _get(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _eval_condition(cond, answers: dict) -> bool:
    field = _get(cond, "field")
    if answers.get(field) in (None, "", []):
        return False
    ans = _selected(answers.get(field))
    vals = {str(x) for x in (_get(cond, "value") or [])}
    op = _get(cond, "operator", "in")
    if op == "in":
        return bool(vals & ans)
    if op == "eq":
        return vals.issubset(ans)
    if op == "nin":
        return bool(vals - ans)
    if op == "neq":
        return not (vals & ans)
    return False


def is_visible(field: str, show_logic: list, answers: dict) -> bool:
    """给定作答 answers，判断某题是否应显示。无规则→显示；有规则→满足才显示。"""
    rules = [
        r for r in (show_logic or [])
        if _get(r, "target") == field and _get(r, "scope", "question") == "question"
    ]
    if not rules:
        return True
    for r in rules:
        conds = _get(r, "conditions") or []
        comparor = _get(r, "comparor", "and")
        res = [_eval_condition(c, answers) for c in conds]
        if (any(res) if comparor == "or" else all(res)):
            return True
    return False
