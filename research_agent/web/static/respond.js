// ---- 受访页：渲染问卷 → 收集作答 → 提交 ----
const schema = window.__SURVEY__ || {};
const path = window.__PATH__;
const banner = (schema.bannerConf || {}).titleConfig || {};

document.querySelector("#rtitle").textContent = banner.mainTitle || "问卷";
document.querySelector("#form").innerHTML = SurveyRender.questionsHtml(schema, true);

const start = Date.now();

document.querySelector("#submitBtn").onclick = async () => {
  const msg = document.querySelector("#rmsg");
  const { data, missing } = SurveyRender.collectAnswers(
    schema, document.querySelector("#form")
  );
  if (missing.length) {
    msg.className = "rmsg err";
    msg.textContent = "请完成必填题：第 " + missing.join("、") + " 题";
    return;
  }
  try {
    const r = await fetch(`/api/r/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data, meta: { diffTime: (Date.now() - start) / 1000 } }),
    });
    if (!r.ok) throw new Error("提交失败，请稍后再试");
    document.querySelector(".respond").innerHTML =
      '<div class="done">✅ 提交成功，感谢你的参与！</div>';
  } catch (e) {
    msg.className = "rmsg err";
    msg.textContent = e.message;
  }
};
