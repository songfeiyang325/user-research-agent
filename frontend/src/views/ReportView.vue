<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { get } from '../api'

const route = useRoute()
const sid = route.params.sid
const report = ref(null)
const loadErr = ref('')

const fieldA = ref('')
const fieldB = ref('')
const ct = ref(null)
const ctErr = ref('')

const CAT = ['radio', 'checkbox', 'binary-choice', 'vote', 'radio-star', 'radio-nps']
const catQuestions = computed(() =>
  (report.value?.questions || []).filter((q) => CAT.includes(q.type))
)
const narrativeHtml = computed(() =>
  report.value ? marked.parse(report.value.narrative || '') : ''
)

onMounted(async () => {
  try {
    report.value = await get(`/api/surveys/${sid}/analysis`)
  } catch (e) {
    loadErr.value = e.message
  }
})

function maxCount(q) {
  return Math.max(1, ...(q.aggregation || []).map((a) => a.count))
}
async function runCrosstab() {
  ctErr.value = ''
  ct.value = null
  if (!fieldA.value || !fieldB.value) {
    ctErr.value = '请选择两道题'
    return
  }
  try {
    ct.value = await get(`/api/surveys/${sid}/crosstab?a=${fieldA.value}&b=${fieldB.value}`)
  } catch (e) {
    ctErr.value = e.message
  }
}
function ctMax(m) {
  return Math.max(1, ...m.flat())
}
function cellBg(v, max) {
  const t = max ? v / max : 0
  return `rgba(250,166,0,${(0.06 + 0.74 * t).toFixed(3)})`
}
function printPdf() {
  window.print()
}
</script>

<template>
  <div>
    <header class="topbar">
      <div class="brand">📊 分析报告</div>
      <div class="actions">
        <a class="btn ghost" :href="`/api/surveys/${sid}/export.xlsx`">导出 Excel</a>
        <button class="btn ghost" @click="printPdf">导出 PDF</button>
        <a class="btn ghost" href="/">← 返回控制台</a>
      </div>
    </header>

    <div class="report" v-if="loadErr">
      <div class="notfound">{{ loadErr }}</div>
    </div>

    <div class="report" v-else-if="report">
      <h1 class="rtitle">{{ report.title }}</h1>
      <p class="rcount">共收集 <b>{{ report.overview.count }}</b> 份有效回答</p>

      <!-- AI 洞察叙事 -->
      <section class="card narrative">
        <h3>AI 洞察</h3>
        <div class="md" v-html="narrativeHtml"></div>
      </section>

      <!-- 分题统计 -->
      <section
        class="card"
        v-for="q in report.questions"
        :key="q.field"
      >
        <div class="q-head">{{ q.title }} <span class="q-type">{{ q.type }}</span></div>

        <!-- 选择/评分：条形分布 -->
        <template v-if="q.aggregation && q.aggregation.length">
          <div class="summary" v-if="q.summary">
            <span v-if="q.summary.average != null">均值 {{ q.summary.average }}</span>
            <span v-if="q.summary.median != null"> · 中位数 {{ q.summary.median }}</span>
            <span v-if="q.summary.nps != null"> · NPS {{ q.summary.nps }}</span>
          </div>
          <div class="bars">
            <div class="bar-row" v-for="a in q.aggregation" :key="a.id">
              <div class="bar-label" :title="a.text">{{ a.text }}</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: (a.count / maxCount(q) * 100) + '%' }"></div>
              </div>
              <div class="bar-val">
                {{ a.count }}<span v-if="a.percent != null" class="pct"> · {{ a.percent }}%</span>
              </div>
            </div>
          </div>
        </template>

        <!-- 开放题：主题聚类 -->
        <template v-else-if="q.open_text">
          <div v-if="q.themes && q.themes.length">
            <div class="theme" v-for="(t, i) in q.themes" :key="i">
              <span class="theme-name">{{ t.theme }}</span>
              <span class="theme-count">{{ t.count }}</span>
              <div class="theme-eg" v-for="(e, j) in t.examples" :key="j">“{{ e }}”</div>
            </div>
          </div>
          <div v-else class="muted">暂无开放题回答</div>
        </template>

        <div v-else class="muted">（该题型暂不统计）</div>
      </section>

      <!-- 交叉分析 -->
      <section class="card">
        <h3>交叉分析</h3>
        <div class="ct-picker">
          <select v-model="fieldA">
            <option value="" disabled>选择题目 A（行）</option>
            <option v-for="q in catQuestions" :key="q.field" :value="q.field">{{ q.title }}</option>
          </select>
          <span>×</span>
          <select v-model="fieldB">
            <option value="" disabled>选择题目 B（列）</option>
            <option v-for="q in catQuestions" :key="q.field" :value="q.field">{{ q.title }}</option>
          </select>
          <button class="btn primary sm" @click="runCrosstab">分析</button>
        </div>
        <div v-if="ctErr" class="muted err">{{ ctErr }}</div>
        <div v-if="ct" class="ct-wrap">
          <table class="ct">
            <thead>
              <tr><th></th><th v-for="(c, j) in ct.colLabels" :key="j">{{ c }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in ct.matrix" :key="i">
                <th>{{ ct.rowLabels[i] }}</th>
                <td v-for="(v, j) in row" :key="j" :style="{ background: cellBg(v, ctMax(ct.matrix)) }">{{ v }}</td>
              </tr>
            </tbody>
          </table>
          <div class="ct-stats" v-if="ct.cramersV != null">
            χ² = {{ ct.chi2 }} · p = {{ ct.pValue }} · Cramér's V = <b>{{ ct.cramersV }}</b>
            <span class="muted">（V 越接近 1 关联越强）</span>
          </div>
          <div class="ct-stats muted" v-else>数据不足，无法计算关联强度</div>
        </div>
      </section>
    </div>

    <div class="report" v-else><div class="muted">加载中…</div></div>
  </div>
</template>
