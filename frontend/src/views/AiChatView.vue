<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Delete, Promotion, VideoPause } from '@element-plus/icons-vue'

import { aiApi } from '@/api/ai'
import { useAuthStore } from '@/stores/auth'
import type { ChatPayload } from '@/types/ai'

interface Bubble {
  role: 'user' | 'assistant'
  content: string
  error?: boolean
}

const auth = useAuthStore()

const bubbles = ref<Bubble[]>([])
const draft = ref('')
const sending = ref(false)
const elapsedMs = ref(0)
const modelName = ref('')
const listEl = ref<HTMLElement | null>(null)
let controller: AbortController | null = null
let startedAt = 0

const suggestions = [
  '用三句话介绍一下这个平台的能力',
  '帮我写一段部门周报的开头',
  '把「本周完成了用户模块开发」润色得更正式一些',
  '解释一下 JWT 和 Session 的区别',
]

const canChat = computed(() => auth.has('ai:chat'))
const isEmpty = computed(() => bubbles.value.length === 0)

function scrollToBottom(): void {
  nextTick(() => {
    if (listEl.value) {
      listEl.value.scrollTop = listEl.value.scrollHeight
    }
  })
}

watch(bubbles, scrollToBottom, { deep: true })

async function send(text?: string): Promise<void> {
  const content = (text ?? draft.value).trim()
  if (!content || sending.value) return
  if (!canChat.value) {
    ElMessage.error('当前账号没有 AI 对话权限')
    return
  }

  draft.value = ''
  sending.value = true
  elapsedMs.value = 0
  bubbles.value.push({ role: 'user', content })
  bubbles.value.push({ role: 'assistant', content: '' })
  const target = bubbles.value[bubbles.value.length - 1]

  const payload: ChatPayload = {
    messages: bubbles.value
      .filter((item) => item.role === 'user' && item.content)
      .map((item) => ({ role: 'user' as const, content: item.content })),
    system_prompt: '你是智企协同平台的企业助手，回答简洁、专业，使用简体中文。',
  }

  startedAt = performance.now()
  controller = new AbortController()

  try {
    await aiApi.streamChat(
      payload,
      {
        onDelta(delta) {
          target.content += delta
        },
        onError(message) {
          target.error = true
          target.content = target.content || message
          ElMessage.error(message)
        },
      },
      controller.signal,
    )
  } catch (error) {
    if ((error as Error).name === 'AbortError') {
      target.content += target.content ? '\n\n（已停止）' : '（已停止）'
    } else {
      target.error = true
      target.content = target.content || '请求失败，请稍后重试'
    }
  } finally {
    elapsedMs.value = Math.round(performance.now() - startedAt)
    sending.value = false
    controller = null
    if (!modelName.value) modelName.value = 'qwen-plus'
  }
}

function stop(): void {
  controller?.abort()
}

function clearAll(): void {
  if (sending.value) stop()
  bubbles.value = []
  elapsedMs.value = 0
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void send()
  }
}

onBeforeUnmount(() => controller?.abort())
</script>

<template>
  <div class="chat-page">
    <el-card shadow="never" class="chat-card">
      <template #header>
        <div class="chat-header">
          <div class="chat-title">
            <el-icon class="chat-icon"><ChatDotRound /></el-icon>
            <span>AI 助手</span>
            <el-tag size="small" type="success" effect="plain">{{ modelName || 'qwen-plus' }}</el-tag>
          </div>
          <div class="chat-actions">
            <span v-if="elapsedMs" class="elapsed">{{ (elapsedMs / 1000).toFixed(1) }}s</span>
            <el-button :icon="Delete" text :disabled="isEmpty" @click="clearAll">清空</el-button>
          </div>
        </div>
      </template>

      <div ref="listEl" class="chat-list">
        <el-empty v-if="isEmpty" description="还没有对话，试试下面的问题">
          <div class="suggestions">
            <el-tag
              v-for="item in suggestions"
              :key="item"
              class="suggestion"
              effect="plain"
              @click="send(item)"
            >
              {{ item }}
            </el-tag>
          </div>
        </el-empty>

        <div v-for="(item, index) in bubbles" :key="index" class="bubble-row" :class="item.role">
          <el-avatar :size="32" class="bubble-avatar">
            {{ item.role === 'user' ? auth.displayName.slice(0, 1) : 'AI' }}
          </el-avatar>
          <div class="bubble" :class="{ error: item.error }">
            <span v-if="item.content">{{ item.content }}</span>
            <span v-else class="typing">思考中…</span>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="draft"
          type="textarea"
          :rows="3"
          resize="none"
          maxlength="2000"
          show-word-limit
          placeholder="输入问题，Enter 发送，Shift + Enter 换行"
          :disabled="!canChat"
          @keydown="onKeydown"
        />
        <div class="input-actions">
          <el-button v-if="sending" :icon="VideoPause" @click="stop">停止</el-button>
          <el-button
            v-else
            type="primary"
            :icon="Promotion"
            :disabled="!draft.trim() || !canChat"
            @click="send()"
          >
            发送
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.chat-page {
  height: calc(100vh - 100px);
}

.chat-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-card :deep(.el-card__body) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  padding: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.chat-icon {
  color: #409eff;
}

.chat-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.elapsed {
  font-size: 12px;
  color: #909399;
}

.chat-list {
  flex: 1;
  min-height: 0;
  padding: 20px;
  overflow-y: auto;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.suggestion {
  cursor: pointer;
}

.bubble-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.bubble-row.user {
  flex-direction: row-reverse;
}

.bubble-avatar {
  flex: none;
  background: #409eff;
}

.bubble-row.user .bubble-avatar {
  background: #67c23a;
}

.bubble {
  max-width: 72%;
  padding: 10px 14px;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f4f4f5;
  border-radius: 10px;
}

.bubble-row.user .bubble {
  color: #fff;
  background: #409eff;
}

.bubble.error {
  color: #f56c6c;
  background: #fef0f0;
}

.typing {
  color: #909399;
}

.chat-input {
  padding: 12px 20px 16px;
  border-top: 1px solid #ebeef5;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
</style>
