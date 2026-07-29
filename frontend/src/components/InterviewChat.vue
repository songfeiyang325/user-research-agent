<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { get, streamSSE } from '../api'

const props = defineProps({ path: String, title: String })

const messages = ref([])
const sessionId = ref(null)
const input = ref('')
const busy = ref(false)
const ended = ref(false)
const boxEl = ref(null)
const KEY = 'interview:' + props.path

function scroll() {
  nextTick(() => {
    if (boxEl.value) boxEl.value.scrollTop = boxEl.value.scrollHeight
  })
}
function strip(t) {
  return t.replace(/\[END\]/g, '').trimEnd()
}
function pushAI() {
  messages.value.push({ role: 'ai', content: '…' })
  return messages.value[messages.value.length - 1]
}

onMounted(async () => {
  const saved = localStorage.getItem(KEY)
  if (saved) {
    try {
      const s = await get('/api/interview/' + saved)
      sessionId.value = saved
      messages.value = s.transcript.map((t) => ({
        role: t.role === 'assistant' ? 'ai' : 'user',
        content: t.content,
      }))
      ended.value = s.status === 'done'
      scroll()
      return
    } catch (e) {
      localStorage.removeItem(KEY)
    }
  }
  startInterview()
})

async function startInterview() {
  busy.value = true
  const bubble = pushAI()
  let acc = ''
  try {
    await streamSSE(`/api/r/${props.path}/interview/start`, {}, (evt) => {
      if (evt.type === 'session') {
        sessionId.value = evt.session_id
        localStorage.setItem(KEY, evt.session_id)
      } else if (evt.type === 'token') {
        acc += evt.text
        bubble.content = strip(acc)
        scroll()
      } else if (evt.type === 'end') {
        ended.value = true
      } else if (evt.type === 'error') {
        bubble.content = '⚠️ ' + evt.message
      }
    })
  } catch (e) {
    bubble.content = '⚠️ ' + e.message
  } finally {
    busy.value = false
  }
}

async function sendAnswer() {
  if (busy.value || ended.value) return
  const text = input.value.trim()
  if (!text || !sessionId.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: text })
  scroll()
  busy.value = true
  const bubble = pushAI()
  let acc = ''
  try {
    await streamSSE(`/api/interview/${sessionId.value}/reply`, { message: text }, (evt) => {
      if (evt.type === 'token') {
        acc += evt.text
        bubble.content = strip(acc)
        scroll()
      } else if (evt.type === 'end') {
        ended.value = true
      } else if (evt.type === 'error') {
        bubble.content = '⚠️ ' + evt.message
      }
    })
  } catch (e) {
    bubble.content = '⚠️ ' + e.message
  } finally {
    busy.value = false
  }
}

function onKey(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    sendAnswer()
  }
}
</script>

<template>
  <div class="interview-page">
    <div class="iv-head">🎤 {{ title || 'AI 访谈' }}</div>
    <div class="messages" ref="boxEl">
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role === 'user' ? 'user' : 'ai'">
        <div class="bubble">{{ m.content }}</div>
      </div>
      <div v-if="ended" class="interview-end">✅ 访谈结束，感谢你的参与！</div>
    </div>
    <div class="composer" v-if="!ended">
      <textarea
        v-model="input" rows="2" :disabled="busy"
        placeholder="输入你的回答，Enter 发送 / Shift+Enter 换行"
        @keydown="onKey"
      ></textarea>
      <button class="btn primary" :disabled="busy" @click="sendAnswer">发送</button>
    </div>
  </div>
</template>
