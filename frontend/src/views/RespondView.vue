<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { get, post } from '../api'
import QuestionItem from '../components/QuestionItem.vue'

const route = useRoute()
const path = route.params.path
const title = ref('问卷')
const schema = ref(null)
const answers = reactive({})
const msg = ref('')
const msgErr = ref(false)
const done = ref(false)
const loadError = ref('')
const start = Date.now()

const questions = computed(() => schema.value?.dataConf?.dataList || [])

onMounted(async () => {
  try {
    const r = await get(`/api/r/${path}/schema`)
    title.value = r.title || '问卷'
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
  const missing = []
  questions.value.forEach((q, i) => {
    if (q.isRequired && !answered(q)) missing.push(i + 1)
  })
  if (missing.length) {
    msgErr.value = true
    msg.value = '请完成必填题：第 ' + missing.join('、') + ' 题'
    return
  }
  try {
    await post(`/api/r/${path}`, {
      data: { ...answers },
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
  <div class="respond-body">
    <div v-if="loadError" class="notfound">{{ loadError }}</div>
    <div v-else-if="done" class="respond">
      <div class="done">✅ 提交成功，感谢你的参与！</div>
    </div>
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
