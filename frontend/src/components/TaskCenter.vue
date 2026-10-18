<template>
  <el-badge :value="taskStore.runningCount" :hidden="taskStore.runningCount === 0" :max="9">
    <el-button text class="task-entry" @click="drawer = true">
      <el-icon :size="19" :class="{ 'is-spinning': taskStore.runningCount > 0 }">
        <MagicStick />
      </el-icon>
      <span
        v-if="taskStore.runningCount > 0"
        class="task-entry-text"
      >AI 进行中 {{ taskStore.runningCount }}</span>
    </el-button>
  </el-badge>

  <el-drawer v-model="drawer" title="任务中心" size="420px" append-to-body>
    <template #header="{ titleId, titleClass }">
      <span :id="titleId" :class="titleClass" style="font-weight: 600">任务中心</span>
    </template>

    <div v-if="taskStore.tasks.length === 0" class="tc-empty">
      <el-icon :size="28" color="#c7c7cc"><MagicStick /></el-icon>
      <div>暂无 AI 任务，去生成文案或分析订单吧</div>
    </div>

    <div v-else class="tc-list">
      <div v-if="taskStore.tasks.some((t) => t.status !== 'running')" class="tc-clear">
        <el-button text size="small" type="info" @click="taskStore.clearFinished()">
          清空已完成
        </el-button>
      </div>

      <div v-for="t in taskStore.recent" :key="t.id" class="tc-item">
        <div class="tc-item-head">
          <div class="tc-item-title">
            <span class="tc-status-dot" :class="t.status"></span>
            {{ t.title }}
          </div>
          <el-button text size="small" @click="taskStore.remove(t.id)">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>

        <div class="tc-item-time">{{ formatTime(t.createdAt) }}</div>

        <!-- 进行中 -->
        <div v-if="t.status === 'running'" class="tc-running">
          <span class="loading-dots"><span></span><span></span><span></span></span>
          <span>AI 正在处理，可切换到其他页面…</span>
        </div>

        <!-- 失败 -->
        <el-alert v-else-if="t.status === 'error'" type="error" :title="t.error" :closable="false" show-icon />

        <!-- 完成 -->
        <template v-else>
          <div class="tc-result">{{ t.result }}</div>
          <el-button size="small" round @click="copy(t.result)">复制结果</el-button>
        </template>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick, Close } from '@element-plus/icons-vue'
import { useTaskStore } from '../stores/tasks'

const taskStore = useTaskStore()
const drawer = ref(false)

const formatTime = (ts) => {
  const d = new Date(ts)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  return sameDay
    ? d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const copy = async (text) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.task-entry {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: var(--radius-pill);
  color: var(--text-secondary);
}
.task-entry:hover {
  background: var(--bg-subtle);
  color: var(--color-primary);
}
.task-entry-text {
  font-size: var(--font-size-xs);
  font-weight: 500;
  color: var(--color-primary);
}
.is-spinning {
  color: var(--color-primary);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}

.tc-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 60px 20px;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
  text-align: center;
}
.tc-clear {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}
.tc-item {
  background: var(--bg-subtle);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  margin-bottom: 10px;
}
.tc-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tc-item-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-primary);
}
.tc-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.tc-status-dot.running {
  background: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
  animation: pulse 1.2s ease-in-out infinite;
}
.tc-status-dot.done {
  background: var(--color-success);
}
.tc-status-dot.error {
  background: var(--color-danger);
}
.tc-item-time {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin: 4px 0 10px 16px;
}
.tc-running {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
.tc-result {
  font-size: var(--font-size-sm);
  line-height: 1.7;
  color: var(--text-primary);
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  padding: 12px;
  margin-bottom: 10px;
  max-height: 280px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
