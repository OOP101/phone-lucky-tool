<template>
  <div class="admin-page">
    <PageHeader
      title="系统管理"
      subtitle="查看服务运行状态、知识库规模与系统审计日志"
    />

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <AppCard title="系统运行状态" class="mb-4">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="应用名称">{{ status.app }}</el-descriptions-item>
            <el-descriptions-item label="版本">
              <el-tag size="small" type="primary" effect="light" round>{{ status.version }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="LLM 提供商">{{ status.llm_provider }}（{{ status.llm_impl }}）</el-descriptions-item>
            <el-descriptions-item label="LLM 模型">{{ status.llm_model }}</el-descriptions-item>
            <el-descriptions-item label="嵌入提供商">{{ status.embedding_provider }}</el-descriptions-item>
            <el-descriptions-item label="向量库">{{ status.vector_store }}</el-descriptions-item>
            <el-descriptions-item label="向量条目数">{{ status.vector_count }}</el-descriptions-item>
          </el-descriptions>
        </AppCard>

        <el-row :gutter="16">
          <el-col :span="12">
            <StatCard label="知识库文档" :value="knowledgeStats?.documents ?? 0" :loading="!knowledgeStats" tone="primary">
              <template #icon><el-icon :size="22"><Collection /></el-icon></template>
            </StatCard>
          </el-col>
          <el-col :span="12">
            <StatCard label="向量分块数" :value="knowledgeStats?.chunks ?? 0" :loading="!knowledgeStats" tone="cyan">
              <template #icon><el-icon :size="22"><Files /></el-icon></template>
            </StatCard>
          </el-col>
        </el-row>
      </el-col>

      <el-col :xs="24" :md="12">
        <AppCard title="审计日志" :extra="`共 ${logs.length} 条`">
          <el-table :data="logs" height="452" size="default">
            <el-table-column prop="id" label="ID" width="64" />
            <el-table-column prop="actor" label="操作者" width="90" />
            <el-table-column label="动作" width="120">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" round>{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="detail" label="详情" min-width="150" show-overflow-tooltip />
            <el-table-column label="时间" width="168">
              <template #default="{ row }">
                <span class="log-time">{{ formatTime(row.created_at) }}</span>
              </template>
            </el-table-column>

            <template #empty>
              <EmptyState text="暂无审计日志" />
            </template>
          </el-table>
        </AppCard>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Collection, Files } from '@element-plus/icons-vue'
import api from '../api'
import PageHeader from '../components/PageHeader.vue'
import AppCard from '../components/AppCard.vue'
import StatCard from '../components/StatCard.vue'
import EmptyState from '../components/EmptyState.vue'

const status = ref({})
const knowledgeStats = ref(null)
const logs = ref([])

const formatTime = (t) => {
  if (!t) return '–'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  return d.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

const load = async () => {
  const [s, k, a] = await Promise.all([
    api.get('/admin/status'),
    api.get('/admin/knowledge-stats'),
    api.get('/admin/audit'),
  ])
  status.value = s
  knowledgeStats.value = k
  logs.value = a.logs
}

onMounted(load)
</script>

<style scoped>
.mb-4 {
  margin-bottom: 16px;
}
.log-time {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
