<script setup lang="ts">
import { nextTick, ref } from 'vue'

const props = defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ submit: [content: string] }>()
const input = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function autoResize() {
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
      textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 120) + 'px'
    }
  })
}

function handleSubmit() {
  const content = input.value.trim()
  if (!content || props.disabled) return
  emit('submit', content)
  input.value = ''
  autoResize()
}

// Enter 发送，Shift+Enter 换行
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <div class="chat-input">
    <textarea
      ref="textareaRef"
      v-model="input"
      :disabled="disabled"
      rows="1"
      placeholder="输入旅游需求或问题... (Enter发送, Shift+Enter换行)"
      @input="autoResize"
      @keydown="onKeydown"
    />
    <button :disabled="disabled || !input.trim()" @click="handleSubmit">
      {{ disabled ? '思考中...' : '发送' }}
    </button>
  </div>
</template>

<style scoped>
.chat-input {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid #e0e0e0;
  align-items: flex-end;
}
textarea {
  flex: 1;
  padding: 0.5rem 1rem;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  font-size: 1rem;
  font-family: inherit;
  resize: none;
  outline: none;
  line-height: 1.5;
  max-height: 120px;
  overflow-y: auto;
}
textarea:focus {
  border-color: #2563eb;
}
textarea:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}
button {
  padding: 0.5rem 1.5rem;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  cursor: pointer;
  font-size: 1rem;
  white-space: nowrap;
  height: 2.5rem;
}
button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
</style>
