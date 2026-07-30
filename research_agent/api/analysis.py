"""分析 API：整份洞察报告 + 按两字段的交叉分析。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from ..agents import AnalystAgent
from ..analysis.crosstab import crosstab as _crosstab
from ..analysis.export import build_workbook
from ..storage import repo

router = APIRouter(prefix="/api")


@router.get("/surveys/{sid}/analysis")
def analysis(sid: str) -> dict:
    sv = repo.get_survey(sid)
    if not sv:
        raise HTTPException(404, "问卷不存在")
    responses = [r.data for r in repo.list_responses(sid)]
    report = AnalystAgent().build_report(sv.schema_data, responses)
    report["title"] = sv.title
    return report


@router.get("/surveys/{sid}/crosstab")
def crosstab_api(sid: str, a: str, b: str) -> dict:
    sv = repo.get_survey(sid)
    if not sv:
        raise HTTPException(404, "问卷不存在")
    data_list = sv.schema_data.get("dataConf", {}).get("dataList", [])
    qa = next((q for q in data_list if q["field"] == a), None)
    qb = next((q for q in data_list if q["field"] == b), None)
    if not qa or not qb:
        raise HTTPException(400, "字段不存在")
    responses = [r.data for r in repo.list_responses(sid)]
    return _crosstab(qa, qb, responses)


@router.get("/surveys/{sid}/export.xlsx")
def export_xlsx(sid: str) -> Response:
    sv = repo.get_survey(sid)
    if not sv:
        raise HTTPException(404, "问卷不存在")
    rows = [
        {"data": r.data, "created_at": r.created_at.isoformat()}
        for r in repo.list_responses(sid)
    ]
    content = build_workbook(sv.schema_data, sv.title, rows)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="survey_{sid}.xlsx"'},
    )
