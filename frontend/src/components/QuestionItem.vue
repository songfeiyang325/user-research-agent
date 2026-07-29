<script setup>
import { computed } from 'vue'

const props = defineProps({
  q: { type: Object, required: true },
  index: { type: Number, default: 0 },
  interactive: { type: Boolean, default: false },
  modelValue: { default: null },
})
const emit = defineEmits(['update:modelValue'])

const LABELS = {
  text: '单行输入框', textarea: '多行输入框', radio: '单选', checkbox: '多选',
  'binary-choice': '判断题', 'radio-star': '评分', 'radio-nps': 'NPS',
  vote: '投票', cascader: '多级联动',
}
const label = computed(() => LABELS[props.q.type] || props.q.type)
const isMulti = computed(() => props.q.type === 'checkbox' || props.q.type === 'vote')
const isSingle = computed(() =>
  ['radio', 'binary-choice'].includes(props.q.type)
)
const stars = computed(() =>
  Array.from({ length: props.q.starMax || 5 }, (_, i) => i + 1)
)
const npsRange = computed(() => {
  const lo = props.q.min ?? 0
  const hi = props.q.max ?? 10
  return Array.from({ length: hi - lo + 1 }, (_, i) => lo + i)
})

function isChecked(hash) {
  return Array.isArray(props.modelValue) && props.modelValue.includes(hash)
}
function toggleCheck(hash) {
  const cur = Array.isArray(props.modelValue) ? [...props.modelValue] : []
  const i = cur.indexOf(hash)
  if (i >= 0) cur.splice(i, 1)
  else cur.push(hash)
  emit('update:modelValue', cur)
}
</script>

<template>
  <div class="q">
    <div class="q-title">
      <span class="idx">{{ index + 1 }}.</span>{{ q.title }}
      <span v-if="q.isRequired" class="req">*</span>
      <span class="tag">{{ label }}</span>
    </div>
    <div class="q-body">
      <!-- 输入类 -->
      <input
        v-if="q.type === 'text'"
        class="fld" type="text" :disabled="!interactive"
        :placeholder="q.placeholder || '请输入'"
        :value="modelValue || ''"
        @input="emit('update:modelValue', $event.target.value)"
      />
      <textarea
        v-else-if="q.type === 'textarea'"
        class="fld" rows="3" :disabled="!interactive"
        :placeholder="q.placeholder || '请输入'"
        :value="modelValue || ''"
        @input="emit('update:modelValue', $event.target.value)"
      ></textarea>

      <!-- 单选 / 判断 -->
      <div v-else-if="isSingle" class="opts">
        <label v-for="o in q.options" :key="o.hash" class="opt">
          <input
            type="radio" :disabled="!interactive"
            :checked="modelValue === o.hash"
            @change="emit('update:modelValue', o.hash)"
          />
          <span>{{ o.text }}</span>
        </label>
      </div>

      <!-- 多选 / 投票 -->
      <div v-else-if="isMulti" class="opts">
        <label v-for="o in q.options" :key="o.hash" class="opt">
          <input
            type="checkbox" :disabled="!interactive"
            :checked="isChecked(o.hash)"
            @change="toggleCheck(o.hash)"
          />
          <span>{{ o.text }}</span>
        </label>
      </div>

      <!-- 评分 -->
      <div v-else-if="q.type === 'radio-star'" class="stars">
        <span
          v-for="v in stars" :key="v"
          class="star" :class="{ on: modelValue >= v }"
          @click="interactive && emit('update:modelValue', v)"
        >★</span>
      </div>

      <!-- NPS -->
      <div v-else-if="q.type === 'radio-nps'" class="npswrap">
        <div class="npsline">
          <span
            v-for="v in npsRange" :key="v"
            class="nps" :class="{ on: modelValue === v }"
            @click="interactive && emit('update:modelValue', v)"
          >{{ v }}</span>
        </div>
        <div class="npsmsg"><span>{{ q.minMsg }}</span><span>{{ q.maxMsg }}</span></div>
      </div>

      <div v-else class="muted">（{{ label }} 暂不支持渲染）</div>
    </div>
  </div>
</template>
