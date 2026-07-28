# XiaoJu Survey — 答卷存储、统计 & API 规格（供 Python 复刻）

> 来源：对 `xiaoju-survey` 代码的探查结果，作为本项目 `analysis/`、`storage/`（及可选对接）模块的移植依据。含 `file:line` 引用。

后端为 **NestJS + TypeORM over MongoDB**（尽管列注解写 `jsonb`，仓库实为 `MongoRepository`）。两个集合关键：`surveySubmit`（答卷）与 `surveyPublish`（发布态 schema）。

## (a) 答卷数据模型 / JSON 形状

**实体：`server/src/models/surveyResponse.entity.ts:5-40`** —— 集合 `surveySubmit`：
- `pageId`(string) — surveyId（指向 `surveyPublish.pageId`）
- `surveyPath`(string) — 答题页用的短公开路径
- `data`(`Record<string, any>`) — **答案对象，核心载荷**
- `diffTime`(number, ms)、`clientTime`(number)
- `secretKeys`(string[]) — `data` 中哪些键被加密（RSA 插件；见 `@BeforeInsert`/`@AfterLoad` 钩子调 `encryptResponseData`/`decryptResponseData`）
- `optionTextAndId`(`Record<string, Array<{hash,text}>>`) — **提交时刻的选项文本↔hash 快照**，使日后改选项文案不破坏历史行（`surveyResponse.controller.ts:270-297` 填充）
- `channelId`(string)

**`data` 如何键控** —— 每题有稳定 `field` id 如 `data458`、`data515`（`mockResponseSchema.ts:88,119`、`interfaces/survey.ts:50-79` 的 `DataItem.field`）。`data` 的键即这些 field id，外加派生子键：

| 题型（`enums/question.ts:4-41`） | `data[field]` 存的值 |
|---|---|
| `text` / `textarea` | 原始字符串 |
| `radio` / `binary-choice` | 单个选项 **hash** 串（如 `"115019"`） |
| `checkbox` / `vote` | **选项 hash 数组**（如 `["115019","115020"]`） |
| `radio-star` | **数字** 1–5 |
| `radio-nps` | **数字** 0–10 |
| `cascader` | **逗号连接的 hash 路径**串（如 `"h1,h2"`），在 `dataStatistic.service.ts:96-103` 解码 |

**额外/派生子键**（同一扁平 `data`）：
- 选项「其他」填空 → 键为该选项的 `othersKey` id（`utils/index.ts:44-51`；`Option.othersKey`）。推送工具读作 `data[`${field}_${optionHash}`]`（`messagePushing.ts:43-46`）。
- 评分/NPS「原因」文本 → `data[`${field}_custom`]`，由 `data[`${field}_${selectedNumber}`]` 重建（`dataStatistic.service.ts:71-77`）。

答卷文档内**无逐条 diff/optionCount**。选项计数在**独立 `Counter` 集合**，键 `{surveyPath, key=field, type:'option'}`，`data = { [optionHash]: count, total: n }`，每次提交事务性自增，用于配额（`counter.service.ts:73-163`，尤见 `:114-141` 的 `optionCountData[val]++`/`total`）。

mock schema 的 `data` 例：
```json
{ "data458": "13800000000", "data515": "115019", "data450": "...", "data770": "a@b.com" }
```

## (b) 统计 & 交叉分析 —— 算法 + 输出形状

全文：**`server/src/modules/survey/services/dataStatistic.service.ts`**。两种操作：

### 1. 扁平数据表 —— `getDataTable`（`dataStatistic.service.ts:21-119`）
分页原始行，**选项 hash 已还原为文本**。对每条把 `data[field]` 经 `keyBy(options,'hash')` → `text`（数组用 `,` 连）（:79-89），解码 cascader 路径（:91-104），为 star/nps 填 `_custom`（:71-77），追加 `diffTime`（秒，2 位小数）与格式化 `createdAt`（:106-113）。列头来自 `getListHeadByDataList`（`utils/index.ts:32-71`）。输出：`{ total, listHead, listBody }`。

### 2. 分题聚合「分题统计」—— `aggregationStatis`（`dataStatistic.service.ts:121-177`）
单条 MongoDB 聚合 + **`$facet`** —— 每个可选字段一个分支。各分支（:122-136）：
```
$match { data.<field>: { $nin: [ [], '', null ] } }   // 去空
$group { _id: "$data.<field>", count: { $sum: 1 } }    // 相同答案计数
$project { count, data.<field>: "$_id" }
```
外层 `$match` 过滤 `pageId===surveyId && isDeleted!=true`（:139-146），`maxTimeMS:30000, allowDiskUse:true`。

由于 checkbox/vote 答案是**数组**，`$group` 会按*整个数组组合*分组；**`transformAndMergeArrayFields`（`utils/index.ts:73-107`）随后拆开数组、按单个选项值重新求和** —— 这是复刻的关键。每字段 `submitionCount` = 该字段所有分支计数之和（:152-161）。

服务层每字段输出：
```json
{ "field": "data515",
  "data": { "aggregation": [ { "id": "115019", "count": 12 }, ... ],
            "submitionCount": 20 } }
```

控制器再按题型经 **`handleAggretionData`（`utils/index.ts:109-203`）** 后处理：
- **radio / checkbox / vote / binary-choice**：投影回*完整选项列表*，使 0 计数选项也出现，附 `text` —— `{ id, text, count }`（:115-137）。
- **radio-star / radio-nps**：建固定桶数组（star `1..5`，nps `0..10`）带计数，加 **`summary`**（:141-176）：
  - `average` = Σ(值·计数)/Σ计数，2 位小数（`getAverage :226-240`）
  - `median` = 把计数展开成有序表，取中位/双中均值（`getMedian :242-261`）
  - `variance` = Σ(值−均)²/(n−1)，即**样本方差**（`getVariance :263-277`）
  - 仅 NPS：`nps` = (推荐者≥9 − 贬损者≤6)/总数 ×100，形如 `"NN.NN%"`（`getNps :279-295`）
- **cascader**：把树摊成叶子路径（`id`=逗号连 hash 路径，`text`=`-` 连标签）经 `getTextPaths(:205-224)`，仅留 `count>0`（:177-195）。

控制器（`dataStatistic.controller.ts:107-133`）只聚合：`RADIO, CHECKBOX, BINARY_CHOICE, RADIO_STAR, RADIO_NPS, VOTE, CASCADER`。文本/多行**不聚合**（落到 `utils/index.ts:196-202` 的 `else`）。

### 交叉分析（交叉分析）—— 未实现
仓库中**无任何交叉制表**。`grep 交叉|cross|CrossAnalysis` 在 `server/` 只命中 `package.json`/脚本里的 `cross-env`，`web/` **零命中**。因此 Python 侧的交叉分析（如 Q1×Q2 列联表）**从零构建** —— 原料是扁平 `data`（连接两字段的 hash 并对 pair 计数；checkbox 数组则如 `transformAndMergeArrayFields` 般交叉展开值）。

## (c) 表格导出形状（「一行一份答卷」）

**`server/src/modules/survey/services/downloadTask.service.ts`** —— 异步任务：`createDownloadTask`(:34-63) 持久化 `DownloadTask`，`processDownloadTask`/`executeTask`(:131-154) 串行队列，`handleDownloadTask`(:156-272) 构建 xlsx。

规范扁平化（:185-216）：**复用 `getDataTable`** 逐页（pageSize 200），故**导出行模型 == 已还原的 `listBody` 行**（hash 已转文本）。然后：
- 表头 = `listHead[].title`，用 cheerio `load(title).text()` 去 HTML（:193-199）。
- 每行 = 对每个 head `field` 取 `get(bodyItem, field, '')`，字符串则去 HTML（:200-214）。
- 列序遵循 `getListHeadByDataList`：**每题一列** + 每选项「其他」列（`othersCode`，`utils/index.ts:36-58`）+ 末尾 **`diffTime`(「答题耗时（秒）」)** 与 **`createdAt`(「提交时间」)**（`utils/index.ts:60-69`）。
- 用 `node-xlsx` 构建 `[header, ...rows]`（:216-219），经 `FileService` 上传；脱敏在实时表路径经 `maskData` 钩子先做（`dataStatistic.controller.ts:68-73`），导出文件名标注脱敏/原始（:47）。

即「一行一份答卷」= **`{ <field>: <文本>, <field>_<optionHash>: <其他文本>, ..., diffTime, createdAt }`**，列序按发布 schema 的 `dataList`。

## (d) 可对接的 REST 端点（方法 + 路径 + 用途）

前缀来自 `@Controller(...)`。管理路由需 `Authentication`(Bearer) + `SurveyGuard`；公开答题路由无守卫。

**编辑 / 发布** —— `survey.controller.ts`(`/api/survey`) & `surveyMeta.controller.ts`：
- `POST /api/survey/createSurvey` — 建问卷(meta+conf) `:71`
- `POST /api/survey/updateConf` — 保存 schema/题目(`configData.dataConf.dataList`) `:132`
- `POST /api/survey/publishSurvey` — 发布 → 写 `surveyPublish`(ResponseSchema) `:395`
- `GET  /api/survey/getSurvey` — 取 meta+conf 供编辑 `:310`
- `GET  /api/survey/getPreviewSchema` — 预览 schema `:365`
- `POST /api/survey/updateMeta` — 更新 meta `surveyMeta.controller.ts:43`
- `GET  /api/survey/getList` — 问卷列表 `surveyMeta.controller.ts:82`
- `POST /api/survey/pausingSurvey`/`deleteSurvey`/`recoverSurvey`/`completeDeleteSurvey` — 生命周期 `:211-308`

**公开答题流** —— `surveyResponse` 模块：
- `GET  /api/responseSchema/getSchema?surveyPath=` — 取发布 schema 渲染（剔除密码/白名单） `responseSchema.controller.ts:32`
- `POST /api/responseSchema/:surveyPath/validate` — 密码/白名单预校验 `:73`
- `GET  /api/clientEncrypt/getEncryptInfo` — 取 RSA 公钥 + sessionId（可选加密） `clientEncrpt.controller.ts:16`
- `POST /api/surveyResponse/createResponse` — **提交答卷**（body: `surveyPath, data, clientTime, diffTime, encryptType?, sessionId?`；需 `sign`，见 `checkSign` `surveyResponse.controller.ts:57,109-127`） `:50`
- `POST /api/surveyResponse/createResponseWithOpen` — 经 Open API 提交（OAuth 守卫，需 `channelId`） `:77`
- `GET  /api/counter/queryOptionCountInfo?surveyPath=&fieldList=` — 实时选项计数 `counter.controller.ts:12`

**读取结果 / 统计** —— `/api/survey/dataStatistic` & `/api/downloadTask`：
- `GET  /api/survey/dataStatistic/dataTable?surveyId=&isMasked=&page=&pageSize=` — 分页扁平答卷(`listHead`,`listBody`,`total`) `dataStatistic.controller.ts:37`
- `GET  /api/survey/dataStatistic/aggregationStatis?surveyId=` — 分题聚合(计数/百分比 + star/nps summary/nps) `dataStatistic.controller.ts:85`
- `POST /api/downloadTask/createTask` — 启动异步 xlsx 导出(body `surveyId, isMasked`) → `{taskId}` `downloadTask.controller.ts:42`
- `GET  /api/downloadTask/getDownloadTask?taskId=` — 轮询任务状态 + 下载 `url` `:124`
- `GET  /api/downloadTask/getDownloadTaskList` — 导出任务列表 `:75`

### Python agent 对接备注（若日后需要）
- **推送生成的问卷**：`createSurvey` → `updateConf`（送符合 `SurveySchemaInterface` 的 `configData`，题目为带 `field`/`type`/`options[].hash/text` 的 `dataList`）→ `publishSurvey`。鉴权 Bearer JWT。
- **拉取答卷**：`dataStatistic/dataTable`（已扁平、文本还原，最易消费）或 `downloadTask` 取 xlsx。要原始 hash 需 DB 访问；HTTP 面只暴露还原/聚合数据。
- **程序化提交**：`createResponse` 需签名（`checkSign`）——机器路径应走 Open API 变体 `createResponseWithOpen`（OAuth + `channelId`）。
- **可复刻的统计**：`utils/index.ts:109-295` 全是纯算术（均值/中位数/样本方差/NPS + 多选计数展开），Python/pandas 易复现。交叉分析无参考实现。

**移植时保持打开的关键文件**：`server/src/models/surveyResponse.entity.ts`、`server/src/modules/survey/services/dataStatistic.service.ts`、`server/src/modules/survey/utils/index.ts`、`server/src/modules/surveyResponse/controllers/surveyResponse.controller.ts`、`server/src/utils/messagePushing.ts`。
