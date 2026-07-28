# XiaoJu Survey — 数据模型 & 题型规格（供 Python 复刻）

> 来源：对 `xiaoju-survey`（Vue3 + NestJS）代码的探查结果，作为本项目 `survey/` 模块的移植依据。含 `file:line` 引用。

## 关键 ID 约定（先内化）

- **题目 ID = `field`**，形如 `"data458"`。生成规则 `data${0..999}`（`web/src/management/utils/index.js:8-11`, `getNewField :30-39`）。
- **选项 ID = `hash`**，6 位随机数字串如 `"115019"`（`web/src/materials/questions/common/utils/index.js:14-18`, `getNewHash :5-11`）。
- 逻辑规则用 `field` 引用题目、用 `hash` 引用选项。选项级目标用复合串 `"<field>-<hash>"`（如 `"data517-106374"`，`web/src/common/logicEngine/ruleConf.ts:34`）。

---

## (a) 题型清单

规范枚举 —— 前后端一致：`web/src/common/typeEnum.ts:2-25`、`server/src/enums/question.ts:4-41`

| type key | 枚举常量 | UI 标题 | 中文标签(typeTagLabels) | widget 目录 |
|---|---|---|---|---|
| `text` | `TEXT` | 单行输入框 | 单行输入框 | `InputModule` |
| `textarea` | `TEXTAREA` | 多行输入框 | 多行输入框 | `TextareaModule` |
| `radio` | `RADIO` | 单项选择(单选) | 单选 | `RadioModule` |
| `checkbox` | `CHECKBOX` | 多项选择(多选) | 多选 | `CheckboxModule` |
| `binary-choice` | `BINARY_CHOICE` | 判断题 | 判断题 | `BinaryChoiceModule` |
| `radio-star` | `RADIO_STAR` | 评分 | 评分 | `StarModule` |
| `radio-nps` | `RADIO_NPS` | nps评分 | **NPS评分** | `NpsModule` |
| `vote` | `VOTE` | 投票 | 投票 | `VoteModule` |
| `cascader` | `CASCADER` | 多级联动 | 多级联动 | `CascaderModule` |

题型分组（`typeEnum.ts:27-45`）：`INPUT=[text,textarea]`；`NORMAL_CHOICES=[radio,checkbox]`；`CHOICES=[radio,checkbox,binary-choice,vote]`；`RATES=[radio-star,radio-nps]`；`ADVANCED=[cascader]`。

**移植注意：**
- `MultilevelModule/meta.js` 定义了 `multilevel` 但**不在枚举/菜单**里，是 cascader 的无用副本，忽略。
- `SelectMoreModule/meta.js` **为空**，非真实题型。
- NPS 标签不一致：菜单/meta 标题是 `"nps评分"`，但文本格式/AI 标签是 `"NPS评分"`（`typeEnum.ts:22`）。文本解析用 `"NPS评分"`。
- UI 菜单分组/图标在 `web/src/management/config/questionMenuConfig.js`。

### 各题型区分属性（来自各 `widgets/*/meta.js` 的 `attrs[]`）

所有题型共享基础属性：`field, title, type, isRequired(bool,true), showIndex(bool,true), showType(bool,true), showSpliter(bool,true)`。

- **text / textarea**（`InputModule/meta.js:50-92`, `TextareaModule/meta.js:50-91`）：`placeholder`, `valid`（`''|'m'|'idcard'|'n'|'e'|'licensePlate'` = mobile/idcard/number/email/车牌，:100-126）, `numberRange {max/min:{placeholder,value}}`, `textRange {max/min:{placeholder,value}}`（字数限制）。
- **radio**（`RadioModule/meta.js:50-84`）：`options[]`, `layout('vertical'|'horizontal')`, `quotaDisplay(bool)`；选项支持 `quota`。
- **checkbox**（`CheckboxModule/meta.js:50-89`）：`options[]`, `minNum(0)`, `maxNum(0)`, `layout`。
- **binary-choice**（`BinaryChoiceModule/meta.js:50-78`）：`options[]` 默认 `对`/`错`（:56,64）, `layout`。
- **radio-star**（`StarModule/meta.js:50-73`）：`starMin(1)`, `starMax(5)`, `starStyle('star'|'love'|'number')`, `rangeConfig({})`。
- **radio-nps**（`NpsModule/meta.js:51-81`）：`min(1)`, `max(10)`, `minMsg('极不满意')`, `maxMsg('十分满意')`, `rangeConfig({})`。
- **vote**（`VoteModule/meta.js:50-84`）：`options[]`, `minNum`, `maxNum`, `innerType('radio'|'checkbox')`（:99-113）。
- **cascader**（`CascaderModule/meta.js:39-75`）：`cascaderData {placeholder:[{text,hash}], children:[{text,hash,children:[]}]}`。cascader 的 meta 省略 `field`/`title`，构建时注入。

空题对象构建：`getQuestionByType(type)` 载入 meta，把每个 `attr.defaultValue` 拷进以 `attr.name` 为键的 schema 对象，分配新 `field`，重生成选项 `hash`（`web/src/management/utils/index.js:41-63`）。

---

## (b) 规范 Survey / Question / Option JSON schema

### 顶层 survey schema

持久化为 `SurveyConf.code`（jsonb 列）+ `pageId` 列（`server/src/models/surveyConf.entity.ts:5-11`）。接口 `SurveySchemaInterface`（`server/src/interfaces/survey.ts:173-180`）。最完整实例：`server/src/modules/survey/template/surveyTemplate/templateBase.json:1-69`：

```jsonc
{
  "bannerConf": {                          // 问卷头 (survey.ts:15-18)
    "titleConfig": { "mainTitle": "<h3>…HTML…</h3>", "subTitle": "<p>…</p>" },
    "bannerConfig": { "bgImage": "", "bgImageAllowJump": false, "bgImageJumpLink": "",
                      "videoLink": "", "postImg": "" }
  },
  "dataConf": { "dataList": [ /* 题目数组，见下 */ ] },   // survey.ts:91-93
  "submitConf": {                          // survey.ts:108-112
    "submitTitle": "提交",
    "confirmAgain": { "is_again": true, "again_text": "确认要提交吗？" },
    "msgContent": { "msg_200":"提交成功","msg_9001":"…","msg_9002":"…","msg_9003":"…","msg_9004":"…" },
    "link": ""
  },
  "baseConf": {                            // survey.ts:131-150
    "beginTime":"2024-01-01 00:00:00","endTime":"2034-01-01 00:00:00",
    "answerBegTime":"00:00:00","answerEndTime":"23:59:59",
    "tLimit":0,"language":"chinese",
    "passwordSwitch":false,"password":"",
    "whitelistType":"ALL","whitelist":[],"memberType":"MOBILE",
    "fillAnswer":false,"fillSubmitAnswer":false
  },
  "skinConf": {                            // survey.ts:152-166
    "skinColor":"#4a4c5b","inputBgColor":"#ffffff",
    "backgroundConf":{"color":"#b8dbff","type":"color","image":""},
    "themeConf":{"color":"#ffa600"},"contentConf":{"opacity":100}
  },
  "bottomConf": { "logoImage":"/imgs/Logo.webp","logoImageWidth":"60%" },  // survey.ts:168-171
  "pageConf": [],                          // 分页（不在 TS 接口里）
  "logicConf": { "showLogicConf": [], "jumpLogicConf": [] }  // 逻辑（不在 TS 接口里）
}
```

注意：`pageConf`/`logicConf` 在持久化 JSON 里存在，但**不在 `SurveySchemaInterface`**——以 JSON 模板为准。`whitelistType ∈ {ALL, MEMBER, CUSTOM}`，`memberType ∈ {MOBILE, EMAIL}`（`survey.ts:115-129`）。

### 题目对象（`DataItem`，`server/src/interfaces/survey.ts:50-79`）

接口是所有题型字段的并集；某题只带与其 `type` 相关的字段：

```
field: string            // 题目 id "dataNNN"（必需，逻辑/答案的连接键）
title: string            // 题干（可含 HTML）
type: string             // 上表 type key 之一
isRequired: boolean       // 是否必填（注意字段名是 isRequired，不是 required）
showIndex: boolean        // 显示自动序号
showType: boolean         // 显示题型标签
showSpliter: boolean      // 显示分割线
placeholder: string       // 输入提示（输入类）
placeholderDesc: string
valid?: string            // 输入格式约束键
randomSort?: boolean       // 选项乱序
checked: boolean
minNum: string            // 最少可选（checkbox/vote）
maxNum: string            // 最多可选
star: number              // 评分（注意 meta 实际用 starMin/starMax/starStyle）
starStyle?: string
nps?: { leftText, rightText }   // 接口字段（meta 实际用 min/max/minMsg/maxMsg）
textRange?: { min:{placeholder,value:number}, max:{placeholder,value:number} }
rangeConfig?: any         // 高级评分/nps 配置
options?: Option[]        // 选择类
cascaderData: { placeholder:[{hash,text}], children: CascaderItem[] }   // CascaderItem = {hash,text,children?}
innerType?: string        // vote: 'radio'|'checkbox'
exclude?: boolean
quotaDisplay?: boolean
importKey?, importData?, cOption?, cOptions?   // 选项导入辅助
```

**评分/NPS 的运行时字段名与接口不一致** —— 以 `meta.js` attrs 为准（star → `starMin/starMax/starStyle`；nps → `min/max/minMsg/maxMsg`），`nps.json` 用 `starMin/starMax` 印证。

真实题目对象样例 —— `server/.../survey/normal.json:5-61`：

```jsonc
{ "type":"text","field":"data458","title":"标题1","isRequired":true,
  "showIndex":true,"showType":true,"showSpliter":true,"valid":"","placeholder":"",
  "numberRange":{"max":{"placeholder":"1000","value":1000},"min":{"placeholder":"0","value":0}},
  "textRange":{"min":{"placeholder":"0","value":0},"max":{"placeholder":"500","value":500}} }
,
{ "type":"radio","field":"data515","title":"标题2","isRequired":true,
  "showIndex":true,"showType":true,"showSpliter":true,
  "options":[ {"text":"选项1","others":false,"mustOthers":false,"othersKey":"","placeholderDesc":"","hash":"115019"},
              {"text":"选项2","others":false,"mustOthers":false,"othersKey":"","placeholderDesc":"","hash":"115020"} ] }
```

### 选项对象（`Option`，`server/src/interfaces/survey.ts:81-89`）

```
text: string             // 选项文案
hash: string             // 选项 id（6 位）——被逻辑规则引用
others: boolean          // 是否「其他/填空」选项
mustOthers?: boolean      // 填空是否必填
othersKey?: string        // 填空文本的答案键
placeholderDesc: string   // 填空框 placeholder
quota?: number           // 单选项配额（radio/checkbox）
```

（文本导入路径每选项还会带 `limit`、`score` 字段，见下。）

---

## (c) 文本格式语法（`web/src/management/utils/textToSchema.ts`，已读全文）

这是 AI 生成器输出、并由 `textToSchema(text)` 解析回题目对象的格式。

**语法：**
1. **块**以一个或多个空行分隔：`text.trim().split(/\n\s*\n/)`（:10）。一块 = 一题。
2. 块内：行 trim，丢空行（:14）。
3. **首行 = 题头**，须匹配 `/^(.*?)\[(.+?)\]$/`（:19）→ `title` = 结尾 `[...]` 前的文本，`type` = 括号内标签（:22-23）。首行不匹配的块被跳过（:20）。
4. 括号标签须是 `typeTagLabels` 的中文值；经 `textTypeMap`（:4-8）映射 标签→typekey，再由 `getQuestionByType` 造空题（:26）。然后 `question.title=title`，`question.showIndex = options.showIndex ?? true`（:27-28）。
5. **余下行**（`content`，:24）按题型解释（:31-61）：
   - `单行输入框`,`多行输入框`,`评分`,`多级联动` → 无题体，原样 push（:32-37）。
   - `单选`,`多选`,`投票`,`判断题` → 每行经 `getMultiOptionByText(content.join('\n'))` 变选项（:42-47）。
   - `NPS评分` → 若首行含 `-`，按 `-` 切成 `minMsg`(左)/`maxMsg`(右)（:49-57）。

**选项行解析** `getMultiOptionByText`（`web/src/materials/questions/common/utils/index.js:32-76`）：按 `\n` 切行，每行按 **TAB `\t`** 切列，固定列序（:20-29）：`text, others, mustOthers, limit, score, othersKey, placeholderDesc, hash`。无 tab 的普通行如 `选项1` 得：

```jsonc
{ "text":"选项1", "others":false, "mustOthers":false, "limit":"", "score":0,
  "othersKey":"", "placeholderDesc":"", "hash":"<随机6位>" }
```

`others`/`mustOthers` 仅当该列非空且 ≠`"false"` 时为真；`score`→int（默认 0）；`hash`→给了则 int 否则随机；文本字段做 XSS 转义（:44-66）。

**AI 系统提示词格式**（`server/src/modules/survey/services/ai-generate.service.ts:6-67`）—— LLM 被要求正好输出该文本语法（DeepSeek 风格调用，流式，temp 0.7，`max_tokens 512`，模型取自 env `AImodel_MODEL`，:99-105）：

```
问题内容[单行输入框]

问题内容[单选]
选项1
选项2

问题内容[判断题]
肯定判断设定
否定判断设定

问题内容[评分]

问题内容[NPS评分]
低分设定-高分设定

问题内容[投票]
选型1
选项2
```

其规则（:62-67）：每题标题须以 `[类型]` 结尾；标题编号；标题内无换行；题间 ≥1 空行；只输出题目。注意该提示词覆盖 8 个标签（无 `多级联动`/cascader）。创建流程通过 `createMethod ∈ {copy, textImport, AIGenerate, ExcelImport}` + 可选 `questionList` 接入（`server/.../dto/createSurvey.dto.ts:26-49`）。

---

## (d) 逻辑规则（显示逻辑 / 跳转逻辑）如何存储

存在 survey 上：`logicConf: { showLogicConf: Rule[], jumpLogicConf: Rule[] }`（`templateBase.json:65-68`）。两数组**同一 Rule 形状**，由两个引擎实例加载（`web/src/management/stores/composables/useLogicEngine.ts:8-13` → `new RuleBuild().fromJson(...)`）。

**Rule JSON 形状** —— `RuleBuild.toJson()`/`.fromJson()` 与 yup schema（`web/src/common/logicEngine/RuleBuild.ts:74-104`, `:130-142`）：

```jsonc
{
  "target": "data648",        // 题目 field id；选项级：`"data517-106374"`(field-hash)
  "scope":  "question",       // "question" | "option"  (BasicType.ts:19-22)
  "conditions": [
    { "field": "data515",     // 驱动题的 field id
      "operator": "in",       // "in" | "eq" | "nin" | "neq"  (BasicType.ts:7-12)
      "value": ["115019"] }   // 选项 hash 数组（字符串）
  ]
}
```

规范样例数组：`web/src/common/logicEngine/ruleConf.ts:2-36`。

**操作符**（`BasicType.ts:1-12`）：`in`=Include(选了任一), `eq`=Equal(选了全部), `nin`=NotInclude(未选任一), `neq`=NotEqual(未选全部/「填写了」)。

**求值语义**（`web/src/common/logicEngine/RulesMatch.ts:19-63`, `:86-110`）—— facts = `field → 作答值` 的映射：
- 缺 `field` 的 fact ⇒ 条件 false（:22-25）。
- `eq`：`value[]` 每个值都被答案包含；`in`：某个值被包含；`nin`：某个值未被包含；`neq`：都未包含/字符串化答案 ≠ value（:27-58）。
- 多条件默认 AND，`comparor==='or'` 时 OR（:86-106）。无规则的目标默认**显示**（:186-188）。

**两数组语义：** `showLogicConf` 控制目标题/选项的条件可见性；`jumpLogicConf` 控制跳转流。两者结构相同 `{target, scope, conditions[]}`，无额外「跳到哪」字段，跳转目标经同一 `target` 表达。两个并行引擎类：`RuleBuild`（编辑/序列化）与 `RuleMatch`（运行时匹配）。

---

## Python 复刻清单（最小集）

1. **枚举**：9 个 type key（见 a 表）。
2. **Question 数据类**：基础字段 + 各型载荷（options / ranges / star / nps / cascaderData）——照 `meta.js` 默认值。
3. **Option 数据类**：`text, hash, others, mustOthers, othersKey, placeholderDesc, quota?`。
4. **Survey 包裹**：`bannerConf, dataConf.dataList[], submitConf, baseConf, skinConf, bottomConf, pageConf[], logicConf{showLogicConf,jumpLogicConf}`。
5. **ID 生成**：`field="data"+rand(0..999)`；`hash=6位随机`，均带冲突重试。
6. **text↔schema**：实现 (c) 的 块/`[标签]`/TAB 语法；LLM 系统提示词沿用（把 DeepSeek 换成 GLM 即可）。
7. **逻辑引擎**：`{target,scope,conditions:[{field,operator,value[]}]}` + 4 操作符 + (d) 的 AND/OR 与成员语义。

**最关键的参考文件**：`web/src/common/typeEnum.ts`、`server/src/interfaces/survey.ts`、`server/src/modules/survey/template/surveyTemplate/templateBase.json`（+ `survey/normal.json`, `survey/nps.json`）、`web/src/management/utils/textToSchema.ts`、`web/src/materials/questions/common/utils/index.js`、`web/src/management/utils/index.js`、`web/src/common/logicEngine/{RuleBuild,BasicType,RulesMatch,ruleConf}.ts`、各 `web/src/materials/questions/widgets/*/meta.js`。
