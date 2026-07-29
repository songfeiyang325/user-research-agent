// ---- 控制台：对话式设计问卷 + 实时预览 + 发布 ----
const $ = (s) => document.querySelector(s);
const state = { projectId: null, surveyId: null, schema: null, busy: false };

async function api(path, opts) {
  const r = await fetch(path, opts);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || r.statusText);
  return j;
}

async function initProject() {
  const r = await api("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: "未命名调研" }),
  });
  state.projectId = r.project_id;
  state.surveyId = r.survey_id;
  state.schema = r.survey.schema;
  renderPreview();
}

function addMsg(role, text) {
  const hint = $(".hint");
  if (hint) hint.remove();
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.innerHTML = `<div class="bubble"></div>`;
  div.querySelector(".bubble").textContent = text;
  $("#messages").appendChild(div);
  $("#messages").scrollTop = $("#messages").scrollHeight;
  return div.querySelector(".bubble");
}

async function send(preset) {
  if (state.busy) return;
  const text = (preset || $("#input").value).trim();
  if (!text) return;
  if (!preset) $("#input").value = "";
  addMsg("user", text);
  const bubble = addMsg("ai", "");
  bubble.classList.add("loading");
  bubble.textContent = "思考中…";
  state.busy = true;
  $("#sendBtn").disabled = true;

  try {
    const resp = await fetch(`/api/projects/${state.projectId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "", acc = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const line = chunk.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const evt = JSON.parse(line.slice(5).trim());
        if (evt.type === "token") {
          acc += evt.text;
          bubble.classList.remove("loading");
          bubble.textContent = acc;
          $("#messages").scrollTop = $("#messages").scrollHeight;
        } else if (evt.type === "survey") {
          state.schema = evt.survey;
          renderPreview();
          $("#publishBtn").disabled = false;
        } else if (evt.type === "error") {
          bubble.classList.remove("loading");
          bubble.textContent = (acc ? acc + "\n" : "") + "⚠️ " + evt.message;
        }
      }
    }
    if (!acc) { bubble.classList.remove("loading"); bubble.textContent = "（已更新问卷）"; }
  } catch (e) {
    bubble.classList.remove("loading");
    bubble.textContent = "⚠️ " + e.message;
  } finally {
    state.busy = false;
    $("#sendBtn").disabled = false;
  }
}

function renderPreview() {
  const s = state.schema || {};
  const title = ((s.bannerConf || {}).titleConfig || {}).mainTitle || "";
  $("#previewTitle").textContent = title || "问卷预览";
  const html = SurveyRender.questionsHtml(s, false);
  $("#previewBody").innerHTML =
    html || `<div class="empty">左侧对话生成问卷后，这里实时预览 👉</div>`;
}

async function publish() {
  try {
    const r = await api(`/api/surveys/${state.surveyId}/publish`, { method: "POST" });
    const share = $("#share");
    share.classList.remove("hidden");
    share.innerHTML =
      `已发布 · <a href="${r.share_url}" target="_blank">${r.share_url}</a> ` +
      `<button class="btn ghost sm" id="copyBtn">复制链接</button> ` +
      `<button class="btn ghost sm" id="refreshBtn">回收 <b id="cnt">0</b> 份 ⟳</button>`;
    $("#copyBtn").onclick = () => {
      navigator.clipboard.writeText(r.share_url);
      $("#copyBtn").textContent = "已复制";
    };
    $("#refreshBtn").onclick = refreshCount;
    refreshCount();
  } catch (e) {
    alert(e.message);
  }
}

async function refreshCount() {
  const r = await api(`/api/surveys/${state.surveyId}/responses`);
  const c = $("#cnt");
  if (c) c.textContent = r.count;
}

$("#sendBtn").onclick = () => send();
$("#input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    send();
  }
});
$("#publishBtn").onclick = publish;
$("#newBtn").onclick = () => location.reload();
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("chip")) send(e.target.textContent);
});

initProject();
