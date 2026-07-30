<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { get, post } from '../api'
import { visibleQuestions } from '../logic'
import QuestionItem from '../components/QuestionItem.vue'
import InterviewChat from '../components/InterviewChat.vue'

const route = useRoute()
const path = route.params.path
const title = ref('问卷')
const mode = ref('form')
const schema = ref(null)
const answers = reactive({})
const msg = ref('')
const msgErr = ref(false)
const done = ref(false)
const loadError = ref('')
const start = Date.now()

const questions = computed(() => visibleQuestions(schema.value || {}, answers))

onMounted(async () => {
  try {
    const r = await get(`/api/r/${path}/schema`)
    title.value = r.title || '问卷'
    mode.value = r.mode || 'form'
    schema.value = r.schema
  } catch (e) {
    loadError.value = '问卷不存在或未发布'
  }
})

function answered(q) {
  const v = answers[q.field]
  if (v === undefined || v === null || v === '') return false
  if (Array.isArray(v) && v.length === 0) return false
  return true
}

async function submit() {
  const vis = questions.value
  const missing = []
  vis.forEach((q, i) => {
    if (q.isRequired && !answered(q)) missing.push(i + 1)
  })
  if (missing.length) {
    msgErr.value = true
    msg.value = '请完成必填题：第 ' + missing.join('、') + ' 题'
    return
  }
  // 只提交当前可见题目的作答（被逻辑隐藏的不计入）
  const data = {}
  vis.forEach((q) => {
    const v = answers[q.field]
    if (v !== undefined && v !== '' && !(Array.isArray(v) && !v.length)) data[q.field] = v
  })
  try {
    await post(`/api/r/${path}`, {
      data,
      meta: { diffTime: (Date.now() - start) / 1000 },
    })
    done.value = true
  } catch (e) {
    msgErr.value = true
    msg.value = e.message
  }
}
</script>

<template>
  <div v-if="loadError" class="respond-body"><div class="notfound">{{ loadError }}</div></div>

  <!-- AI 主持访谈 -->
  <InterviewChat v-else-if="mode === 'interview' && schema" :path="path" :title="title" />

  <!-- 静态表单 -->
  <div v-else class="respond-body">
    <div v-if="done" class="respond"><div class="done">✅ 提交成功，感谢你的参与！</div></div>
    <div v-else-if="schema" class="respond">
      <h2>{{ title }}</h2>
      <QuestionItem
        v-for="(q, i) in questions" :key="q.field"
        :q="q" :index="i" :interactive="true"
        v-model="answers[q.field]"
      />
      <button class="btn primary block" @click="submit">提交</button>
      <div v-if="msg" class="rmsg" :class="{ err: msgErr }">{{ msg }}</div>
    </div>
  </div>
</template>
