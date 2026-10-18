<template>
  <div class="chat-page">
    <div class="chat-panel">
      <div class="chat-header">
        <el-icon :size="18" class="header-icon"><ChatDotRound /></el-icon>
        <span class="header-title">跨境电商智能客服</span>
        <el-tag size="small" type="info" effect="plain" round>RAG + Agent</el-tag>
        <el-tag size="small" type="success" effect="plain" round>流式回答</el-tag>
      </div>

      <div ref="listRef" class="chat-list">
        <!-- 欢迎区 + 快捷指令卡片（仅在会话开始前展示） -->
        <div v-if="messages.length <= 1" class="welcome">
          <div class="welcome-title">您好，我是您的跨境电商 AI 助手</div>
          <div class="welcome-sub">
            基于企业知识库实时作答，支持订单、物流、产品、售后与贸易术语咨询。点击下方卡片快速提问：
          </div>
          <div class="suggestion-grid">
            <div
              v-for="s in suggestions"
              :key="s.text"
              class="suggestion-card"
              @click="send(null, s.text)"
            >
              <div class="s-icon"><el-icon :size="19"><component :is="s.icon" /></el-icon></div>
              <div class="s-body">
                <div class="s-title">{{ s.title }}</div>
                <div class="s-desc">{{ s.desc }}</div>
              </div>
            </div>
          </div>
        </div>

        <div v-for="(msg, i) in messages" :key="i" class="msg-row" :class="msg.role">
          <div class="avatar" :class="msg.role">
            {{ msg.role === 'user' ? '我' : 'AI' }}
          </div>
          <div class="bubble-wrap">
            <div class="bubble" :class="{ thinking: msg.role === 'assistant' && !msg.content }">
              <template v-if="msg.content">{{ msg.content }}</template>
              <template v-else-if="msg.thinking">
                正在检索知识库并思考…（已分析 {{ msg.reasoned || 0 }} 字）
              </template>
              <template v-else>正在思考…</template>
            </div>
            <div v-if="msg.intent" class="meta">
              <el-tag size="small" type="primary" effect="plain" round>意图：{{ intentLabel(msg.intent) }}</el-tag>
              <el-tag v-if="msg.need_human" size="small" type="danger" effect="plain" round>已转人工</el-tag>
            </div>
            <div v-if="msg.sources && msg.sources.length" class="sources">
              <el-collapse>
                <el-collapse-item :title="`知识来源（${msg.sources.length} 条，点击展开）`">
                  <div v-for="(s, j) in msg.sources" :key="j" class="source-item">
                    <div class="source-head">
                      <el-tag size="small" type="primary" effect="plain" round>{{ s.source }}</el-tag>
                      <span class="score">相关度 {{ (s.score * 100).toFixed(1) }}%</span>
                    </div>
                    <p class="source-text">{{ s.text }}</p>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>

        <div v-if="loading" class="typing">
          <span></span><span></span><span></span>
        </div>
      </div>

      <!-- 快捷输入 chips -->
      <div class="quick-chips">
        <span class="chips-label">快捷提问</span>
        <div class="chips-scroll">
          <span
            v-for="s in suggestions"
            :key="s.text"
            class="chip"
            @click="send(null, s.text)"
          >
            <el-icon :size="13"><component :is="s.icon" /></el-icon>{{ s.title }}
          </span>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="请输入您的问题，例如：订单什么时候发货？支持哪些支付方式？（Enter 发送）"
          @keydown.enter.exact.prevent="send()"
        />
        <el-button type="primary" :loading="loading" @click="send()">发送</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import {
  ChatDotRound, Van, CreditCard, Goods, Ship,
  RefreshLeft, Medal, Sunny, Stamp,
} from '@element-plus/icons-vue'
import { TOKEN_KEY } from '../api'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

// 快捷指令卡片（与示例知识库对齐，点击即发送）
const suggestions = [
  { icon: Van, title: '订单什么时候发货？', desc: '现货 24-48 小时内发货', text: '订单什么时候发货？' },
  { icon: CreditCard, title: '支持哪些支付方式？', desc: 'T/T、信用证、PayPal 等', text: '支持哪些支付方式？' },
  { icon: Goods, title: 'MOQ 起订量是多少？', desc: '常规产品 100 件起', text: '最小起订量 MOQ 是多少？' },
  { icon: Ship, title: 'FOB 和 CIF 的区别？', desc: '常用贸易术语解读', text: 'FOB 和 CIF 有什么区别？' },
  { icon: RefreshLeft, title: '退换货流程', desc: '售后申请与处理时效', text: '退换货流程是怎样的？' },
  { icon: Medal, title: '产品国际认证', desc: 'CE、RoHS、FCC、FDA', text: '产品有哪些国际认证？' },
  { icon: Sunny, title: 'LED 灯带规格', desc: '热销产品参数一览', text: '智能LED灯带是什么规格？' },
  { icon: Stamp, title: 'OEM 贴牌定制', desc: '可打客户 LOGO', text: '可以OEM贴牌定制吗？' },
]

const input = ref('')
const loading = ref(false)
const messages = ref([
  {
    role: 'assistant',
    content: '您好！我是多语言智能客服，可为您解答订单、物流、产品、售后等问题。',
  },
])
const listRef = ref(null)
const sessionId = ref('session-' + Date.now())

const intentMap = {
  order: '订单查询',
  after_sales: '售后处理',
  product: '产品咨询',
  translation: '翻译',
  human: '人工转接',
}

const intentLabel = (i) => intentMap[i] || i

const scrollBottom = async () => {
  await nextTick()
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
}

const send = async (evt, presetText) => {
  const text = (presetText ?? input.value).trim()
  if (!text || loading.value) return
  const history = messages.value.slice(-8).map((m) => ({ role: m.role, content: m.content }))
  messages.value.push({ role: 'user', content: text })
  if (!presetText) input.value = ''
  loading.value = true
  // 流式：先占位一条空回复，随 SSE 事件逐段填充
  // 状态机：无事件=thinking 占位 → reasoning 事件=推理中(thinking) → delta=正文打字机 → meta=完成
  const assistant = { role: 'assistant', content: '', thinking: false, thinkingAt: 0, reasoned: 0, intent: '', need_human: false, sources: [] }
  messages.value.push(assistant)
  await scrollBottom()
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    const resp = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message: text, session_id: sessionId.value, history }),
    })
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buf = ''
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const frames = buf.split('\n\n')
      buf = frames.pop()
      for (const frame of frames) {
        const lines = frame.split('\n')
        const event = (lines.find((l) => l.startsWith('event:')) || '').slice(6).trim()
        const dataLine = lines.find((l) => l.startsWith('data:'))
        if (!dataLine) continue
        const data = JSON.parse(dataLine.slice(5).trim())
        if (event === 'reasoning') {
          // 推理型模型思考期：只累计进度并切换为“推理中”动效，
          // 不渲染推理原文（避免向终端用户暴露提示词/检索上下文）。
          assistant.thinking = true
          assistant.reasoned += (data.text || '').length
          if (!assistant.thinkingAt) {
            assistant.thinkingAt = Date.now()
            await scrollBottom()
          }
        } else if (event === 'delta') {
          assistant.thinking = false
          assistant.content += data.text
          await scrollBottom()
        } else if (event === 'meta') {
          assistant.intent = data.intent
          assistant.need_human = data.need_human
          assistant.sources = data.sources
        }
      }
    }
  } catch (e) {
    if (!assistant.content) assistant.content = '请求失败，请检查后端服务是否启动。'
  } finally {
    loading.value = false
    await scrollBottom()
  }
}
</script>

<style scoped>
.chat-page {
  height: calc(100vh - 116px);
  display: flex;
  justify-content: center;
}
.chat-panel {
  width: 100%;
  max-width: 900px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--divider);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-xs);
  overflow: hidden;
}
.chat-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--divider);
}
.header-icon {
  color: var(--color-primary);
}
.header-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  margin-right: 4px;
}

/* ---- 欢迎区与快捷指令卡片 ---- */
.welcome {
  padding: 36px 12px 12px;
  text-align: center;
}
.welcome-title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}
.welcome-sub {
  margin: 10px auto 24px;
  max-width: 560px;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.7;
}
.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  text-align: left;
}
.suggestion-card {
  display: flex;
  gap: 10px;
  padding: 13px;
  border: 1px solid var(--divider);
  border-radius: var(--radius-md);
  cursor: pointer;
  background: var(--bg-card);
  transition: border-color 0.18s ease, background 0.18s ease;
}
.suggestion-card:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.s-icon {
  color: var(--color-primary);
  line-height: 1;
  margin-top: 1px;
  flex-shrink: 0;
}
.s-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
}
.s-desc {
  margin-top: 3px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}
.msg-row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}
.avatar.user {
  background: var(--color-primary);
}
.avatar.assistant {
  background: #c7c7cc;
}
.bubble-wrap {
  max-width: 74%;
}
.bubble {
  padding: 10px 14px;
  border-radius: 16px;
  border-top-left-radius: 6px;
  background: #e9e9eb;
  color: var(--text-primary);
  font-size: var(--font-size-base);
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg-row.user .bubble {
  background: var(--color-primary);
  color: #fff;
  border-radius: 16px;
  border-top-right-radius: 6px;
}
.bubble.thinking {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}
.meta {
  margin-top: 6px;
  display: flex;
  gap: 6px;
}
.sources {
  margin-top: 6px;
}
.source-item {
  padding: 6px 0;
}
.source-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.score {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}
.source-text {
  margin-top: 4px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  line-height: 1.6;
}
.typing {
  display: flex;
  gap: 4px;
  padding: 2px 0 8px 44px;
}
.typing span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #c7c7cc;
  animation: blink 1.2s infinite ease-in-out;
}
.typing span:nth-child(2) {
  animation-delay: 0.2s;
}
.typing span:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}

/* ---- 快捷输入 chips ---- */
.quick-chips {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 20px 0;
}
.chips-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  flex-shrink: 0;
}
.chips-scroll {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 6px;
}
.chips-scroll::-webkit-scrollbar {
  height: 0;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  background: var(--bg-subtle);
  border: 1px solid var(--divider);
  border-radius: var(--radius-pill);
  padding: 4px 12px;
  cursor: pointer;
  flex-shrink: 0;
  transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
}
.chip:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}

.chat-input {
  display: flex;
  gap: 10px;
  padding: 12px 20px 18px;
  border-top: 1px solid var(--divider);
  align-items: flex-end;
}
</style>
