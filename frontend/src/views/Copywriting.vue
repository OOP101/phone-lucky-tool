<template>
  <div class="cw-page">
    <PageHeader
      title="智能文案"
      subtitle="选择模板、填写商品信息，AI 并发生成多语言标题、详情、广告语与 SEO 关键词"
    />

    <!-- ① 模板选择 -->
    <div class="section-label">
      <span class="step-no">1</span>选择文案模板
    </div>
    <div class="template-grid">
      <div
        v-for="t in templates"
        :key="t.type"
        class="template-card"
        :class="{ active: form.copy_type === t.type }"
        @click="selectTemplate(t.type)"
      >
        <div class="t-icon"><el-icon :size="22"><component :is="t.icon" /></el-icon></div>
        <div class="t-name">{{ t.name }}</div>
        <div class="t-desc">{{ t.desc }}</div>
        <div class="t-outputs">
          <span v-for="o in t.outputs" :key="o" class="output-chip">{{ o }}</span>
        </div>
      </div>
    </div>

    <!-- 当前模板提示 -->
    <div v-if="currentTemplate" class="template-hint">
      <el-icon :size="15"><CircleCheckFilled /></el-icon>
      已选择「{{ currentTemplate.name }}」· 将生成：{{ currentTemplate.outputs.join('、') }}
    </div>

    <!-- ② 示例商品 -->
    <div class="section-label">
      <span class="step-no">2</span>一键填充示例商品（也可手动填写）
    </div>
    <div class="preset-grid">
      <div
        v-for="p in presets"
        :key="p.name"
        class="preset-card"
        @click="applyPreset(p)"
      >
        <div class="p-icon"><el-icon :size="20"><component :is="p.icon" /></el-icon></div>
        <div class="p-info">
          <div class="p-name">{{ p.name }}</div>
          <div class="p-desc">{{ p.selling_points }}</div>
        </div>
      </div>
    </div>

    <!-- ③ 参数与生成 -->
    <div class="section-label">
      <span class="step-no">3</span>填写信息并生成
    </div>
    <el-row :gutter="16">
      <el-col :xs="24" :md="10">
        <AppCard title="商品信息">
          <el-form :model="form" label-width="84px" label-position="left" size="default">
            <el-form-item label="商品名称">
              <el-input v-model="form.product_name" placeholder="如：智能 LED 灯带" />
            </el-form-item>
            <el-form-item label="品类">
              <el-input v-model="form.category" placeholder="如：智能家居" />
            </el-form-item>
            <el-form-item label="卖点关键词">
              <el-input
                v-model="form.selling_points"
                type="textarea"
                :rows="2"
                placeholder="RGB 变色、App 控制、节能环保"
              />
            </el-form-item>
            <el-form-item label="目标市场">
              <el-input v-model="form.target_market" placeholder="如：欧美 / 东南亚 / 中东" />
            </el-form-item>
            <el-form-item label="目标语言">
              <el-select v-model="form.target_language" style="width: 100%">
                <el-option v-for="l in langs" :key="l.code" :label="l.name" :value="l.code" />
              </el-select>
            </el-form-item>
            <el-form-item label="风格 / 语气">
              <div class="style-row">
                <el-select v-model="form.style" placeholder="风格" allow-create filterable style="width: 100%">
                  <el-option v-for="s in styleOptions" :key="s" :label="s" :value="s" />
                </el-select>
                <el-select v-model="form.tone" placeholder="语气" allow-create filterable style="width: 100%">
                  <el-option v-for="t in toneOptions" :key="t" :label="t" :value="t" />
                </el-select>
              </div>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                class="gen-btn"
                :loading="loading"
                @click="generate"
              >
                {{ loading ? 'AI 创作中…' : `一键生成${currentTemplate?.name || '文案'}` }}
              </el-button>
            </el-form-item>
            <div v-if="loading" class="gen-tip">
              <span class="loading-dots"><span></span><span></span><span></span></span>
              生成在后台继续，可切换到其他页面，完成后在右上角任务中心查看
            </div>
          </el-form>
        </AppCard>
      </el-col>

      <el-col :xs="24" :md="14">
        <AppCard>
          <template #title>
            <div class="result-head">
              <span>生成结果</span>
              <el-button v-if="result" text type="primary" size="small" @click="copyResult">
                <el-icon style="margin-right: 3px"><CopyDocument /></el-icon>复制全部
              </el-button>
            </div>
          </template>

          <EmptyState
            v-if="!result && !loading"
            text="还没有生成结果"
            hint="选择模板 → 填写或填充商品 → 一键生成"
          />

          <!-- 流式生成中：段落卡片逐段出现、逐字输出 -->
          <div v-if="loading" class="result">
            <div v-if="liveSections.length === 0" class="gen-loading">
              <span class="loading-dots"><span></span><span></span><span></span></span>
              <span>正在连接 AI，多段文案将并发出稿…</span>
            </div>
            <div v-for="sec in liveSections" :key="sec.key" class="block">
              <div class="block-head">
                <div class="label">
                  {{ sec.label }}
                  <span v-if="!sec.done" class="sec-badge running">
                    <span class="mini-dots"><i></i><i></i><i></i></span>生成中
                  </span>
                  <span v-else-if="sec.error" class="sec-badge failed">失败</span>
                  <span v-else class="sec-badge done">完成</span>
                </div>
                <el-button text size="small" type="primary" :disabled="!sec.text" @click="copyOne(sec.text)">
                  复制
                </el-button>
              </div>
              <div v-if="sec.text" class="text" :class="{ pre: isPre(sec.key) }">
                {{ sec.text }}<span v-if="!sec.done" class="caret"></span>
              </div>
              <div v-else-if="!sec.error" class="thinking">
                <span class="loading-dots"><span></span><span></span><span></span></span>
                AI 正在构思这一段…
              </div>
              <div v-else class="sec-error">{{ sec.error }}</div>
            </div>
          </div>

          <div v-if="result && !loading" class="result">
            <div v-for="block in resultBlocks" :key="block.key" class="block">
              <div class="block-head">
                <div class="label">{{ block.label }}</div>
                <el-button text size="small" type="primary" @click="copyOne(block.text)">复制</el-button>
              </div>
              <div class="text" :class="{ pre: block.pre }">{{ block.text }}</div>
            </div>
          </div>
        </AppCard>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  MagicStick, Document, Promotion, Present, Search,
  Lightning, Sunny, Headset,
  CircleCheckFilled, CopyDocument,
} from '@element-plus/icons-vue'
import { TOKEN_KEY } from '../api'
import { useTaskStore } from '../stores/tasks'
import PageHeader from '../components/PageHeader.vue'
import AppCard from '../components/AppCard.vue'
import EmptyState from '../components/EmptyState.vue'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'
const taskStore = useTaskStore()

const templates = [
  { type: 'all', icon: MagicStick, name: '一键全套', desc: '上架所需一次生成', outputs: ['标题', '详情', '广告语', '关键词'] },
  { type: 'product', icon: Document, name: '商品详情', desc: '商品上架完整信息', outputs: ['标题', '详情', '关键词'] },
  { type: 'ad', icon: Promotion, name: '投放广告语', desc: 'Google / Facebook 投放', outputs: ['广告语'] },
  { type: 'campaign', icon: Present, name: '活动文案', desc: '促销 / 节日营销主题', outputs: ['活动文案'] },
  { type: 'keywords', icon: Search, name: 'SEO 关键词', desc: '搜索引擎优化标签', outputs: ['关键词'] },
]

const presets = [
  {
    icon: Lightning, name: '智能 LED 灯带', category: '智能家居',
    selling_points: 'RGB 变色、App 与语音控制、节能环保',
    target_market: '欧美、东南亚',
  },
  {
    icon: Sunny, name: '便携太阳能充电板', category: '户外装备',
    selling_points: '21W 折叠、双 USB 输出、IPX4 防水',
    target_market: '欧美、中东',
  },
  {
    icon: Headset, name: '无线蓝牙耳机', category: '消费电子',
    selling_points: '蓝牙 5.3、30 小时续航、主动降噪',
    target_market: '全球',
  },
]

const langs = [
  { code: 'en', name: '英语' },
  { code: 'fr', name: '法语' },
  { code: 'es', name: '西班牙语' },
  { code: 'ar', name: '阿拉伯语' },
  { code: 'ja', name: '日语' },
  { code: 'ko', name: '韩语' },
  { code: 'de', name: '德语' },
  { code: 'ru', name: '俄语' },
  { code: 'pt', name: '葡萄牙语' },
  { code: 'it', name: '意大利语' },
  { code: 'zh', name: '中文' },
]

const styleOptions = ['专业', '活泼', '高端', '科技感', '简约']
const toneOptions = ['亲切', '正式', '热情', '克制']

const form = ref({
  copy_type: 'all',
  product_name: '',
  category: '',
  selling_points: '',
  target_market: '',
  target_language: 'en',
  style: '',
  tone: '',
})
const currentTaskId = ref('')
const result = ref(null)

const currentTemplate = computed(() => templates.find((t) => t.type === form.value.copy_type))

const currentTask = computed(() =>
  taskStore.tasks.find((t) => t.id === currentTaskId.value) || null
)
const loading = computed(() => currentTask.value?.status === 'running')
// 流式段落进度挂在任务单例上：切走页面再回来，实时进度依然存在
const liveSections = computed(() => currentTask.value?.sections || [])

const isPre = (key) => key !== 'title' && key !== 'keywords'

const selectTemplate = (type) => {
  form.value.copy_type = type
  result.value = null
  currentTaskId.value = ''
}

const applyPreset = (p) => {
  form.value.product_name = p.name
  form.value.category = p.category
  form.value.selling_points = p.selling_points
  form.value.target_market = p.target_market
  ElMessage.success(`已填充「${p.name}」，可直接生成`)
}

const generate = async () => {
  if (!form.value.product_name) {
    ElMessage.warning('请填写商品名称，或点击上方示例商品一键填充')
    return
  }
  result.value = null
  const payload = { ...form.value }
  const name = payload.product_name
  await taskStore.run(
    { type: 'copywriting', title: `文案写作 · ${name}` },
    async (id) => {
      const task = taskStore.tasks.find((x) => x.id === id)
      if (task) task.sections = []
      const token = localStorage.getItem(TOKEN_KEY)
      const resp = await fetch(`${API_BASE}/copywriting/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      })
      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}，无法建立流式连接`)

      const reader = resp.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buf = ''
      let finalResult = null

      const upsert = (key, patch) => {
        const secs = taskStore.tasks.find((x) => x.id === id)?.sections
        const sec = secs?.find((s) => s.key === key)
        if (sec) Object.assign(sec, patch)
      }

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
          let data
          try {
            data = JSON.parse(dataLine.slice(5).trim())
          } catch {
            continue
          }
          if (event === 'section_start') {
            const secs = taskStore.tasks.find((x) => x.id === id)?.sections
            secs?.push({ key: data.key, label: data.label, text: '', done: false, error: '' })
          } else if (event === 'delta') {
            const secs = taskStore.tasks.find((x) => x.id === id)?.sections
            const sec = secs?.find((s) => s.key === data.key)
            if (sec) sec.text += data.text
          } else if (event === 'section_end') {
            upsert(data.key, { done: true })
          } else if (event === 'error') {
            upsert(data.key, { done: true, error: data.message })
          } else if (event === 'done') {
            finalResult = data.result
          }
        }
      }
      if (!finalResult) throw new Error('流式响应未返回结果，请重试')
      result.value = finalResult
      return finalResult
    },
    (id) => {
      currentTaskId.value = id
    }
  )
  const t = taskStore.tasks.find((x) => x.id === currentTaskId.value)
  if (t?.status === 'error') ElMessage.error(t.error)
}

const labelMap = {
  title: '商品标题',
  description: '商品描述',
  ad: '广告语',
  campaign: '活动文案',
  keywords: 'SEO 关键词',
}

const resultBlocks = computed(() => {
  if (!result.value) return []
  return Object.entries(result.value)
    .filter(([k]) => labelMap[k])
    .map(([k, v]) => ({ key: k, label: labelMap[k], text: v, pre: k !== 'title' && k !== 'keywords' }))
})

const resultText = computed(() =>
  resultBlocks.value.map((b) => `【${b.label}】\n${b.text}`).join('\n\n')
)

const copyOne = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

const copyResult = async () => {
  try {
    await navigator.clipboard.writeText(resultText.value)
    ElMessage.success('已复制全部')
  } catch {
    ElMessage.error('复制失败')
  }
}

// 回到页面时恢复最近一次文案任务（进行中继续显示进度，完成后自动回显）
onMounted(() => {
  const latest = taskStore.latestOfType('copywriting')
  if (!latest) return
  currentTaskId.value = latest.id
  if (latest.status === 'done' && latest.data) result.value = latest.data
})

watch(currentTask, (t) => {
  if (t?.status === 'done' && t.data && !result.value) result.value = t.data
})
</script>

<style scoped>
.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 20px 0 12px;
}
.section-label:first-of-type {
  margin-top: 0;
}
.step-no {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ---- 模板卡片 ---- */
.template-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.template-card {
  padding: 16px 14px;
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
  background: var(--bg-card);
}
.template-card:hover {
  border-color: var(--color-primary);
}
.template-card.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.t-icon {
  color: var(--color-primary);
}
.t-name {
  margin-top: 8px;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
}
.t-desc {
  margin: 3px 0 9px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}
.t-outputs {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.output-chip {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-subtle);
  border: 1px solid var(--divider);
  border-radius: var(--radius-pill);
  padding: 1px 8px;
}
.template-card.active .output-chip {
  background: var(--bg-card);
  color: var(--color-primary);
  border-color: rgba(29, 78, 216, 0.25);
}

.template-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 12px 0 0;
  padding: 9px 14px;
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border-radius: var(--radius-sm);
}

/* ---- 示例商品 ---- */
.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.preset-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 13px 16px;
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  background: var(--bg-card);
  transition: border-color 0.18s ease, background 0.18s ease;
}
.preset-card:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.p-icon {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: var(--bg-subtle);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.preset-card:hover .p-icon {
  background: var(--bg-card);
}
.p-info {
  min-width: 0;
}
.p-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
}
.p-desc {
  margin-top: 2px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---- 表单/结果 ---- */
.style-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.gen-btn {
  width: 100%;
}
.gen-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  margin-top: -4px;
}
.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-lg);
  font-weight: 600;
}
.gen-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 56px 0;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

/* ---- 流式段落 ---- */
.sec-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-left: 8px;
  padding: 1px 9px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 500;
  vertical-align: 1px;
}
.sec-badge.running {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}
.sec-badge.done {
  color: var(--color-success);
  background: var(--color-success-soft);
}
.sec-badge.failed {
  color: var(--color-danger);
  background: var(--color-danger-soft);
}
.mini-dots {
  display: inline-flex;
  gap: 2px;
}
.mini-dots i {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: currentColor;
  animation: mini-bounce 1.2s infinite ease-in-out;
}
.mini-dots i:nth-child(2) { animation-delay: 0.18s; }
.mini-dots i:nth-child(3) { animation-delay: 0.36s; }
@keyframes mini-bounce {
  0%, 80%, 100% { opacity: 0.3; transform: translateY(0); }
  40% { opacity: 1; transform: translateY(-2px); }
}
.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  background: var(--bg-subtle);
  border: 1px dashed var(--divider);
  border-radius: var(--radius-sm);
}
.caret {
  display: inline-block;
  width: 2px;
  height: 1.05em;
  margin-left: 2px;
  vertical-align: text-bottom;
  background: var(--color-primary);
  animation: caret-blink 1s steps(1) infinite;
}
@keyframes caret-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
.sec-error {
  font-size: var(--font-size-sm);
  color: var(--color-danger);
  padding: 10px 14px;
  background: var(--color-danger-soft);
  border-radius: var(--radius-sm);
}

.result .block {
  margin-bottom: 18px;
}
.result .block:last-child {
  margin-bottom: 0;
}
.block-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.result .label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-primary);
}
.result .text {
  font-size: var(--font-size-base);
  color: var(--text-primary);
  line-height: 1.7;
}
.result .text.pre {
  white-space: pre-wrap;
  background: var(--bg-subtle);
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--divider);
}
</style>
