<template>
  <div class="dashboard">
    <!-- 问候区 -->
    <div class="hello">
      <div>
        <h1 class="hello-title">{{ greeting }}，{{ auth.me?.sub || '你好' }}</h1>
        <p class="hello-sub">{{ todayText }} · 欢迎回到国际贸易智能服务平台</p>
      </div>
      <el-tag type="info" effect="plain" round size="large">v2.0</el-tag>
    </div>

    <!-- 核心指标 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="12" :md="6">
        <StatCard label="今日会话" :value="data.chat?.today ?? 0" :loading="loading" tone="primary">
          <template #icon><el-icon :size="22"><ChatDotRound /></el-icon></template>
          <template #sub>本周 {{ data.chat?.week ?? 0 }} · 累计 {{ data.chat?.total ?? 0 }}</template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <StatCard label="客户总数" :value="data.customer?.total ?? 0" :loading="loading" tone="cyan">
          <template #icon><el-icon :size="22"><User /></el-icon></template>
          <template #sub>A 级 {{ data.customer?.grade_a ?? 0 }} · 近 30 天新增 {{ data.customer?.month_new ?? 0 }}</template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <StatCard label="在售商品" :value="data.product?.active ?? 0" :loading="loading" tone="neutral">
          <template #icon><el-icon :size="22"><Goods /></el-icon></template>
          <template #sub>商品总数 {{ data.product?.total ?? 0 }}</template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <StatCard
          label="低库存预警"
          :value="data.product?.low_stock ?? 0"
          :loading="loading"
          :tone="(data.product?.low_stock ?? 0) > 0 ? 'danger' : 'warning'"
        >
          <template #icon><el-icon :size="22"><Warning /></el-icon></template>
          <template #sub>库存总值 ¥{{ (data.product?.stock_value ?? 0).toLocaleString() }}</template>
        </StatCard>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="lower-row">
      <!-- 快捷入口 -->
      <el-col :xs="24" :md="14">
        <AppCard title="快捷入口">
          <div class="quick-grid">
            <RouterLink
              v-for="q in quickEntries"
              :key="q.path"
              :to="q.path"
              class="quick-item"
            >
              <div class="quick-icon" :class="q.tone">
                <el-icon :size="19"><component :is="q.icon" /></el-icon>
              </div>
              <div class="quick-label">{{ q.label }}</div>
              <div class="quick-desc">{{ q.desc }}</div>
            </RouterLink>
          </div>
        </AppCard>
      </el-col>

      <!-- 运营动态 -->
      <el-col :xs="24" :md="10">
        <AppCard title="运营动态">
          <div class="metric-list">
            <div class="metric-row">
              <span class="metric-label">今日 AI 调用</span>
              <span class="metric-value">{{ data.ai?.calls_today ?? 0 }} 次</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">今日 Token 消耗</span>
              <span class="metric-value">{{ (data.ai?.tokens_today ?? 0).toLocaleString() }}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">待跟进客户</span>
              <span class="metric-value" :class="{ warn: (data.customer?.pending_followups ?? 0) > 0 }">
                {{ data.customer?.pending_followups ?? 0 }} 个
              </span>
            </div>
            <div class="metric-row">
              <span class="metric-label">知识文档</span>
              <span class="metric-value">{{ data.knowledge?.indexed ?? 0 }} / {{ data.knowledge?.total ?? 0 }} 已索引</span>
            </div>
          </div>
        </AppCard>
      </el-col>
    </el-row>

    <!-- 最近 AI 任务 -->
    <AppCard title="最近 AI 任务" class="tasks-card">
      <EmptyState
        v-if="taskStore.tasks.length === 0"
        text="还没有 AI 任务"
        hint="在智能文案、亚马逊分析等页面发起任务后，可随时在此查看进度与结果"
      />
      <div v-else class="task-list">
        <div v-for="t in taskStore.recent.slice(0, 5)" :key="t.id" class="task-row">
          <span class="task-dot" :class="t.status"></span>
          <span class="task-title">{{ t.title }}</span>
          <el-tag size="small" round :type="statusType(t.status)" effect="light">
            {{ statusLabel(t.status) }}
          </el-tag>
          <span class="task-time">{{ relativeTime(t.createdAt) }}</span>
        </div>
      </div>
    </AppCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  ChatDotRound, User, Goods, Warning,
  EditPen, Switch, Collection, ShoppingCart,
} from '@element-plus/icons-vue'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import { useTaskStore } from '../stores/tasks'
import StatCard from '../components/StatCard.vue'
import AppCard from '../components/AppCard.vue'
import EmptyState from '../components/EmptyState.vue'

const auth = useAuthStore()
const taskStore = useTaskStore()

const loading = ref(false)
const data = ref({})

// 蓝（AI 核心）/ 青（业务）交替，小面积图标点缀，不使用彩虹色
const quickEntries = [
  { path: '/chat', label: '智能客服', desc: 'RAG 多轮问答', icon: ChatDotRound, tone: 'primary' },
  { path: '/copywriting', label: '智能文案', desc: '多语言营销文案', icon: EditPen, tone: 'cyan' },
  { path: '/translation', label: '翻译引擎', desc: '术语 + 翻译记忆', icon: Switch, tone: 'primary' },
  { path: '/amazon', label: '亚马逊对接', desc: '订单 / 商品 / 库存', icon: ShoppingCart, tone: 'cyan' },
  { path: '/knowledge', label: '知识库', desc: '文档入库向量化', icon: Collection, tone: 'primary' },
  { path: '/crm', label: '客户管理', desc: '分级与跟进', icon: User, tone: 'cyan' },
]

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todayText = computed(() => {
  const d = new Date()
  const week = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][d.getDay()]
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日 · ${week}`
})

const statusType = (s) => ({ running: 'primary', done: 'success', error: 'danger' }[s] || 'info')
const statusLabel = (s) => ({ running: '进行中', done: '已完成', error: '失败' }[s] || s)

const relativeTime = (ts) => {
  const diff = Date.now() - ts
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour} 小时前`
  return `${Math.floor(hour / 24)} 天前`
}

const fetchOverview = async () => {
  loading.value = true
  try {
    data.value = await api.get('/dashboard/overview')
  } catch {
    // 全局拦截器已提示
  } finally {
    loading.value = false
  }
}

onMounted(fetchOverview)
</script>

<style scoped>
.hello {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}
.hello-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}
.hello-sub {
  margin-top: 6px;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.stat-row :deep(.el-col) {
  margin-bottom: 16px;
}
.lower-row {
  margin-bottom: 16px;
}
.lower-row :deep(.el-col) {
  margin-bottom: 16px;
}

/* 快捷入口 */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.quick-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--bg-subtle);
  border: 1px solid transparent;
  text-decoration: none;
  transition: border-color 0.18s ease, background 0.18s ease;
}
.quick-item:hover {
  background: var(--bg-card);
  border-color: var(--border-color);
}
.quick-icon {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}
.quick-icon.primary { background: var(--color-primary-soft); color: var(--color-primary); }
.quick-icon.cyan { background: var(--color-cyan-soft); color: var(--color-cyan); }
.quick-label {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
}
.quick-desc {
  margin-top: 2px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

/* 运营动态 */
.metric-list {
  display: flex;
  flex-direction: column;
}
.metric-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 0;
  border-bottom: 1px solid var(--divider);
}
.metric-row:last-child {
  border-bottom: none;
}
.metric-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
.metric-value {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-primary);
}
.metric-value.warn {
  color: var(--color-danger);
}

/* 最近任务 */
.tasks-card {
  margin-bottom: 16px;
}
.task-list {
  display: flex;
  flex-direction: column;
}
.task-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 0;
  border-bottom: 1px solid var(--divider);
}
.task-row:last-child {
  border-bottom: none;
}
.task-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.task-dot.running {
  background: var(--color-primary);
  animation: dot-pulse 1.2s ease-in-out infinite;
}
.task-dot.done { background: var(--color-success); }
.task-dot.error { background: var(--color-danger); }
@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.task-title {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  font-weight: 500;
}
.task-time {
  margin-left: auto;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

@media (max-width: 640px) {
  .quick-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
