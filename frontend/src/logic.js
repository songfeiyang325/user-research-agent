// 显示逻辑求值（Python research_agent/survey/logic.py 的前端镜像）
// operator：in=选了任一 / eq=选了全部 / nin=有未选 / neq=都没选

function selected(v) {
  if (v === undefined || v === null || v === '') return new Set()
  if (Array.isArray(v)) return new Set(v.map(String))
  return new Set([String(v)])
}

function evalCond(cond, answers) {
  const a = answers[cond.field]
  if (a === undefined || a === null || a === '' || (Array.isArray(a) && !a.length)) return false
  const ans = selected(a)
  const vals = (cond.value || []).map(String)
  const op = cond.operator || 'in'
  if (op === 'in') return vals.some((x) => ans.has(x))
  if (op === 'eq') return vals.every((x) => ans.has(x))
  if (op === 'nin') return vals.some((x) => !ans.has(x))
  if (op === 'neq') return vals.every((x) => !ans.has(x))
  return false
}

export function isVisible(field, showLogic, answers) {
  const rules = (showLogic || []).filter(
    (r) => r.target === field && (r.scope || 'question') === 'question'
  )
  if (!rules.length) return true
  for (const r of rules) {
    const res = (r.conditions || []).map((c) => evalCond(c, answers))
    const ok = r.comparor === 'or' ? res.some(Boolean) : res.every(Boolean)
    if (ok) return true
  }
  return false
}

export function visibleQuestions(schema, answers) {
  const list = schema?.dataConf?.dataList || []
  const sl = schema?.logicConf?.showLogicConf || []
  return list.filter((q) => isVisible(q.field, sl, answers))
}
