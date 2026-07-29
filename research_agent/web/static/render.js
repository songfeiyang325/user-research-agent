/* ---- 共享问卷渲染：控制台预览(只读) 与 受访页(可填) 复用 ---- */
(function () {
  const TYPE_LABELS = {
    text: "单行输入框", textarea: "多行输入框", radio: "单选", checkbox: "多选",
    "binary-choice": "判断题", "radio-star": "评分", "radio-nps": "NPS",
    vote: "投票", cascader: "多级联动",
  };
  const esc = (s) =>
    (s == null ? "" : String(s)).replace(/[&<>"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function optionHtml(q, o, interactive) {
    const dis = interactive ? "" : "disabled";
    const many = q.type === "checkbox" || q.type === "vote";
    const input = many
      ? `<input type="checkbox" data-group="${q.field}" value="${esc(o.hash)}" ${dis}>`
      : `<input type="radio" name="${q.field}" value="${esc(o.hash)}" ${dis}>`;
    return `<label class="opt">${input}<span>${esc(o.text)}</span></label>`;
  }

  function bodyHtml(q, interactive) {
    const dis = interactive ? "" : "disabled";
    switch (q.type) {
      case "text":
        return `<input class="fld" type="text" data-field="${q.field}" placeholder="${esc(q.placeholder || "请输入")}" ${dis}>`;
      case "textarea":
        return `<textarea class="fld" data-field="${q.field}" rows="3" placeholder="${esc(q.placeholder || "请输入")}" ${dis}></textarea>`;
      case "radio": case "checkbox": case "binary-choice": case "vote":
        return `<div class="opts">${(q.options || []).map((o) => optionHtml(q, o, interactive)).join("")}</div>`;
      case "radio-star": {
        const max = q.starMax || 5;
        let s = "";
        for (let v = 1; v <= max; v++)
          s += `<label class="star"><input type="radio" name="${q.field}" value="${v}" ${dis}><span>★</span></label>`;
        return `<div class="stars">${s}</div>`;
      }
      case "radio-nps": {
        const lo = q.min == null ? 0 : q.min, hi = q.max == null ? 10 : q.max;
        let s = "";
        for (let v = lo; v <= hi; v++)
          s += `<label class="nps"><input type="radio" name="${q.field}" value="${v}" ${dis}><span>${v}</span></label>`;
        return `<div class="npswrap"><div class="npsline">${s}</div><div class="npsmsg"><span>${esc(q.minMsg || "")}</span><span>${esc(q.maxMsg || "")}</span></div></div>`;
      }
      default:
        return `<div class="muted">（${TYPE_LABELS[q.type] || q.type} 暂不支持渲染）</div>`;
    }
  }

  function questionsHtml(schema, interactive) {
    const list = ((schema.dataConf || {}).dataList) || [];
    if (!list.length) return "";
    return list.map((q, i) =>
      `<div class="q"><div class="q-title"><span class="idx">${i + 1}.</span>${esc(q.title)}` +
      `${q.isRequired ? '<span class="req">*</span>' : ""}` +
      `<span class="tag">${TYPE_LABELS[q.type] || q.type}</span></div>` +
      `<div class="q-body">${bodyHtml(q, interactive)}</div></div>`
    ).join("");
  }

  function collectAnswers(schema, root) {
    const list = ((schema.dataConf || {}).dataList) || [];
    const data = {}, missing = [];
    list.forEach((q, i) => {
      const f = q.field;
      if (q.type === "text" || q.type === "textarea") {
        const el = root.querySelector(`[data-field="${f}"]`);
        const v = el ? el.value.trim() : "";
        if (v) data[f] = v;
      } else if (q.type === "checkbox" || q.type === "vote") {
        const arr = [...root.querySelectorAll(`[data-group="${f}"]:checked`)].map((e) => e.value);
        if (arr.length) data[f] = arr;
      } else {
        const el = root.querySelector(`input[name="${f}"]:checked`);
        if (el) data[f] = (q.type === "radio-star" || q.type === "radio-nps") ? Number(el.value) : el.value;
      }
      const answered = data[f] !== undefined && !(Array.isArray(data[f]) && !data[f].length);
      if (q.isRequired && !answered) missing.push(i + 1);
    });
    return { data, missing };
  }

  window.SurveyRender = { questionsHtml, collectAnswers };
})();
