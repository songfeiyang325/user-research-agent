"""问卷 Pydantic 模型 —— 结构对齐 xiaoju-survey 的 Survey/Question/Option，
以便未来可选导出到小桔问卷平台。参考：server/src/interfaces/survey.ts、templateBase.json
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .types import QuestionType


class Option(BaseModel):
    text: str
    hash: str = ""
    others: bool = False           # 是否「其他/填空」选项
    mustOthers: bool = False
    othersKey: str = ""
    placeholderDesc: str = ""


class Question(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    field: str = ""               # 题目 id "dataNNN"（连接键）
    title: str
    type: QuestionType
    isRequired: bool = True
    showIndex: bool = True
    showType: bool = True
    showSpliter: bool = True

    # 输入类
    placeholder: str = ""
    valid: str = ""               # '' | m(手机) | idcard | n(数字) | e(邮箱) | licensePlate

    # 选择类
    options: list[Option] = Field(default_factory=list)
    minNum: int = 0               # 多选/投票最少可选（0=不限）
    maxNum: int = 0               # 多选/投票最多可选
    innerType: str = ""           # 投票内部类型 radio|checkbox

    # 评分（star）
    starMin: int = 1
    starMax: int = 5
    starStyle: str = "star"       # star|love|number

    # NPS
    min: int = 1
    max: int = 10
    minMsg: str = "极不满意"
    maxMsg: str = "十分满意"
    rangeConfig: dict = Field(default_factory=dict)

    # 多级联动
    cascaderData: dict = Field(
        default_factory=lambda: {"placeholder": [], "children": []}
    )


class Condition(BaseModel):
    field: str
    operator: str = "in"          # in | eq | nin | neq
    value: list[str] = Field(default_factory=list)


class LogicRule(BaseModel):
    target: str                   # 目标题 field；选项级用 "field-hash"
    scope: str = "question"       # question | option
    conditions: list[Condition] = Field(default_factory=list)


# ---- 各配置块默认值（对齐 templateBase.json，保证 schema 完整、可导出）----
def _default_banner() -> dict:
    return {
        "titleConfig": {"mainTitle": "", "subTitle": ""},
        "bannerConfig": {
            "bgImage": "", "bgImageAllowJump": False, "bgImageJumpLink": "",
            "videoLink": "", "postImg": "",
        },
    }


def _default_submit() -> dict:
    return {
        "submitTitle": "提交",
        "confirmAgain": {"is_again": True, "again_text": "确认要提交吗？"},
        "msgContent": {"msg_200": "提交成功", "msg_9001": "", "msg_9002": "",
                       "msg_9003": "", "msg_9004": ""},
        "link": "",
    }


def _default_base() -> dict:
    return {
        "beginTime": "2024-01-01 00:00:00", "endTime": "2034-01-01 00:00:00",
        "answerBegTime": "00:00:00", "answerEndTime": "23:59:59",
        "tLimit": 0, "language": "chinese",
        "passwordSwitch": False, "password": "",
        "whitelistType": "ALL", "whitelist": [], "memberType": "MOBILE",
        "fillAnswer": False, "fillSubmitAnswer": False,
    }


def _default_skin() -> dict:
    return {
        "skinColor": "#4a4c5b", "inputBgColor": "#ffffff",
        "backgroundConf": {"color": "#f2f4f7", "type": "color", "image": ""},
        "themeConf": {"color": "#faa600"}, "contentConf": {"opacity": 100},
    }


class DataConf(BaseModel):
    dataList: list[Question] = Field(default_factory=list)


class LogicConf(BaseModel):
    showLogicConf: list[LogicRule] = Field(default_factory=list)
    jumpLogicConf: list[LogicRule] = Field(default_factory=list)


class SurveySchema(BaseModel):
    bannerConf: dict = Field(default_factory=_default_banner)
    dataConf: DataConf = Field(default_factory=DataConf)
    submitConf: dict = Field(default_factory=_default_submit)
    baseConf: dict = Field(default_factory=_default_base)
    skinConf: dict = Field(default_factory=_default_skin)
    bottomConf: dict = Field(
        default_factory=lambda: {"logoImage": "", "logoImageWidth": "60%"}
    )
    logicConf: LogicConf = Field(default_factory=LogicConf)

    @property
    def title(self) -> str:
        return self.bannerConf.get("titleConfig", {}).get("mainTitle", "")

    @title.setter
    def title(self, value: str) -> None:
        self.bannerConf.setdefault("titleConfig", {})["mainTitle"] = value

    @property
    def questions(self) -> list[Question]:
        return self.dataConf.dataList
