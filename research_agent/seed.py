"""灌入一份示例问卷 + 随机答卷，用于演示分析。

用法：
  # docker 环境（推荐）
  docker compose exec backend python -m research_agent.seed 40
  # 本地（需能连到 Mongo）
  MONGO_URL=mongodb://localhost:27017 uv run python -m research_agent.seed 40
"""
from __future__ import annotations

import random
import sys

from .storage import repo
from .storage.db import init_db
from .survey import build_survey

SPEC = [
    {"type": "radio", "title": "您使用平台的频率？", "options": ["每天", "每周几次", "偶尔", "第一次"]},
    {"type": "radio-star", "title": "对整体体验的评分", "starMax": 5},
    {"type": "radio-nps", "title": "推荐给同行的意愿", "min": 0, "max": 10,
     "minMsg": "绝不推荐", "maxMsg": "强烈推荐"},
    {"type": "checkbox", "title": "您最看重哪些方面？",
     "options": ["派单效率", "收入", "客服", "规则透明", "导航"]},
    {"type": "radio", "title": "您的车龄？", "options": ["1年内", "1-3年", "3年以上"]},
    {"type": "textarea", "title": "还有什么想吐槽或建议？"},
]
OPEN = [
    "派单太远了", "收入还行但抽成偏高", "客服响应慢", "规则经常变不透明",
    "导航偶尔不准", "希望多点奖励活动", "整体还算满意", "夜间派单少",
]


def run(n: int = 40) -> None:
    init_db()
    _proj, survey = repo.create_project("网约车司机满意度（示例）", "演示分析用")
    schema = build_survey("网约车司机满意度（示例）", SPEC)
    repo.save_draft(survey, schema)
    repo.publish_survey(survey)

    data_list = schema.dataConf.dataList
    for _ in range(n):
        data: dict = {}
        for q in data_list:
            if q.type == "radio":
                data[q.field] = random.choice(q.options).hash
            elif q.type == "checkbox":
                k = random.randint(1, 3)
                data[q.field] = [o.hash for o in random.sample(q.options, k)]
            elif q.type == "radio-star":
                data[q.field] = random.randint(1, 5)
            elif q.type == "radio-nps":
                data[q.field] = random.randint(0, 10)
            elif q.type == "textarea":
                if random.random() < 0.6:
                    data[q.field] = random.choice(OPEN)
        repo.add_response(survey.id, data, {"diffTime": round(random.uniform(20, 120), 1)}, "seed")

    print(f"已生成示例问卷 survey_id={survey.id}，灌入 {n} 份答卷")
    print(f"报告页： http://localhost:8080/report/{survey.id}")
    print(f"分享页： http://localhost:8080/r/{survey.share_path}")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 40)
