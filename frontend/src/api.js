// 轻量 API 封装

export async function api(path, opts) {
  const r = await fetch(path, opts)
  const j = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(j.detail || r.statusText)
  return j
}

export function post(path, body) {
  return api(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
}

export function get(path) {
  return api(path)
}

// 读取 SSE 流：对每个 data 事件回调 onEvent(obj)
export async function streamSSE(path, body, onEvent) {
  const resp = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
  const reader = resp.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const line = chunk.split('\n').find((l) => l.startsWith('data:'))
      if (line) onEvent(JSON.parse(line.slice(5).trim()))
    }
  }
}
