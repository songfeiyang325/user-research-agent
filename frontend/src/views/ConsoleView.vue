<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { get, post, streamSSE } from '../api'
import QuestionItem from '../components/QuestionItem.vue'

const projectId = ref(null)
const surveyId = ref(null)
const schema = ref({})
const messages = ref([])
const input = ref('')
const busy = ref(false)
const canPublish = ref(false)
const shareUrl = ref('')
const count = ref(0)
const copied = ref(false)
const messagesEl = ref(null)

const chips = [
  '面向司机做一次服务满意度调研，5 题左右',
  '调研乘客对新版打车界面的看法',
  '给运营团队做一次内部工具满意度问卷',
]

const questions = computed(() => schema.value?.dataConf?.dataList || [])
const title = computed(
  () => schema.value?.bannerConf?.titleConfig?.mainTitle || '问卷预览'
)

onMounted(async () => {
  const r = await post('/api/projects', { name: '未命名调研' })
  projectId.value = r.project_id
  surveyId.value = r.survey_id
  schema.value = r.survey.schema
})

function scrollBottom() {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

async function send(preset) {
  if (busy.value) return
  const text = (preset || input.value).trim()
  if (!text) return
  if (!preset) input.value = ''
  messages.value.push({ role: 'user', content: text })
  const ai = reactive({ role: 'ai', content: '思考中…', loading: true })
  messages.value.push(ai)
  busy.value = true
  scrollBottom()
  try {
    let acc = ''
    await streamSSE(
      `/api/projects/${projectId.value}/chat`,
      { message: text },
      (evt) => {
        if (evt.type === 'token') {
          acc += evt.text
          ai.content = acc
          ai.loading = false
          scrollBottom()
        } else if (evt.type === 'survey') {
          schema.value = evt.survey
          canPublish.value = true
        } else if (evt.type === 'error') {
          ai.content = (acc ? acc + '\n' : '') + '⚠️ ' + evt.message
          ai.loading = false
        }
      }
    )
    if (!acc) {
      ai.content = '（已更新问卷）'
      ai.loading = false
    }
  } catch (e) {
    ai.content = '⚠️ ' + e.message
    ai.loading = false
  } finally {
    busy.value = false
    scrollBottom()
  }
}

async function publish() {
  try {
    const r = await post(`/api/surveys/${surveyId.value}/publish`)
    shareUrl.value = r.share_url
    refreshCount()
  } catch (e) {
    alert(e.message)
  }
}

async function refreshCount() {
  const r = await get(`/api/surveys/${surveyId.value}/responses`)
  count.value = r.count
}

function copyLink() {
  navigator.clipboard.writeText(shareUrl.value)
  copied.value = true
  setTimeout(() => (copied.value = false), 1500)
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    send()
  }
}
</script>

<template>
  <div>
    <header class="topbar">
      <div class="brand">🧭 用户调研 Agent <span class="sub">控制台</span></div>
      <button class="btn ghost" @click="$router.go(0)">新建调研</button>
    </header>

    <main class="console">
      <section class="chat">
        <div class="messages" ref="messagesEl">
          <div v-if="messages.length === 0" class="hint">
            <p>👋 我是你的调研助手。用一句话告诉我你想调研什么，我来生成问卷；你可以继续对话来修改。</p>
            <div class="chips">
              <button v-for="c in chips" :key="c" class="chip" @click="send(c)">{{ c }}</button>
            </div>
          </div>
          <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role === 'user' ? 'user' : 'ai'">
            <div class="bubble" :class="{ loading: m.loading }">{{ m.content }}</div>
          </div>
        </div>
        <div class="composer">
          <textarea
            v-model="input" rows="3"
            placeholder="描述你的调研，Enter 发送 / Shift+Enter 换行"
            @keydown="onKeydown"
          ></textarea>
          <button class="btn primary" :disabled="busy" @click="send()">发送</button>
        </div>
      </section>

      <section class="preview">
        <div class="preview-head">
          <div class="ptitle">{{ title }}</div>
          <button class="btn primary" :disabled="!canPublish" @click="publish">发布</button>
        </div>
        <div v-if="shareUrl" class="share">
          已发布 · <a :href="shareUrl" target="_blank">{{ shareUrl }}</a>
          <button class="btn ghost sm" @click="copyLink">{{ copied ? '已复制' : '复制链接' }}</button>
          <button class="btn ghost sm" @click="refreshCount">回收 <b>{{ count }}</b> 份 ⟳</button>
        </div>
        <div class="preview-body">
          <div v-if="questions.length === 0" class="empty">左侧对话生成问卷后，这里实时预览 👉</div>
          <QuestionItem
            v-for="(q, i) in questions" :key="q.field"
            :q="q" :index="i" :interactive="false"
          />
        </div>
      </section>
    </main>
  </div>
</template>
