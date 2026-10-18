<template>
  <div class="kb-page">
    <PageHeader
      title="知识库管理"
      subtitle="上传企业文档，自动完成清洗、分块与向量化，为智能客服提供可溯源的知识检索"
    >
      <template #actions>
        <el-button :loading="loading" @click="loadDocs">
          <el-icon style="margin-right: 4px"><Refresh /></el-icon>刷新
        </el-button>
      </template>
    </PageHeader>

    <!-- 统计 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6">
        <StatCard label="文档总数" :value="stats.total" :loading="loading" tone="primary">
          <template #icon><el-icon :size="22"><Collection /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="已索引" :value="stats.indexed" :loading="loading" tone="success">
          <template #icon><el-icon :size="22"><CircleCheck /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="分块总数" :value="stats.chunks" :loading="loading" tone="cyan">
          <template #icon><el-icon :size="22"><Files /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard
          label="待处理 / 失败"
          :value="`${stats.pending} / ${stats.failed}`"
          :loading="loading"
          :tone="stats.pending + stats.failed > 0 ? 'warning' : 'neutral'"
        >
          <template #icon><el-icon :size="22"><Clock /></el-icon></template>
        </StatCard>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 左：上传 + 检索测试 -->
      <el-col :xs="24" :md="9">
        <AppCard title="上传文档" class="mb-4">
          <el-upload
            ref="uploadRef"
            drag
            :auto-upload="false"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
            :limit="1"
            accept=".txt,.md,.csv,.pdf,.docx"
            class="kb-upload"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="upload-tip">支持 PDF / Word / CSV / Markdown / TXT · 单文件建议 ≤ 20MB</div>
            </template>
          </el-upload>

          <el-button
            type="primary"
            class="upload-btn"
            :loading="uploading"
            :disabled="!file"
            @click="upload"
          >
            {{ uploading ? '正在清洗与向量化…' : '上传并向量化' }}
          </el-button>
        </AppCard>

        <AppCard title="检索测试" extra="验证知识库命中效果">
          <el-input
            v-model="query"
            placeholder="输入问题或关键词"
            clearable
            @keydown.enter="search"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button
            type="primary"
            class="search-btn"
            :loading="searching"
            :disabled="!query.trim()"
            @click="search"
          >
            开始检索
          </el-button>

          <div v-if="searched" class="search-meta">
            命中 {{ searchResults.length }} 条相关片段
          </div>

          <EmptyState
            v-if="searched && searchResults.length === 0"
            text="未命中相关内容"
            hint="尝试更换关键词，或先上传相关文档"
          />

          <div v-if="searchResults.length" class="hit-list">
            <div v-for="(r, i) in searchResults" :key="i" class="hit-item">
              <div class="hit-head">
                <el-icon :size="14" class="hit-src-icon"><Document /></el-icon>
                <span class="hit-source">{{ r.metadata?.source || r.source || '未知来源' }}</span>
                <span class="hit-score">{{ (r.score * 100).toFixed(1) }}%</span>
              </div>
              <div class="hit-bar">
                <div class="hit-bar-fill" :style="{ width: Math.min(r.score * 100, 100) + '%' }"></div>
              </div>
              <p class="hit-text">{{ r.text }}</p>
            </div>
          </div>
        </AppCard>
      </el-col>

      <!-- 右：文档列表 -->
      <el-col :xs="24" :md="15">
        <AppCard title="文档列表" :extra="`共 ${documents.length} 个文档`">
          <el-table
            :data="documents"
            v-loading="loading"
            :show-header="documents.length > 0"
            style="width: 100%"
          >
            <el-table-column label="文档" min-width="240">
              <template #default="{ row }">
                <div class="doc-cell">
                  <div class="doc-icon">
                    <el-icon :size="18"><Document /></el-icon>
                  </div>
                  <div class="doc-meta">
                    <div class="doc-name">{{ row.filename }}</div>
                    <div class="doc-ext">{{ fileExt(row.filename) }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="分块" width="80" align="center" />
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag
                  :type="statusType(row.status)"
                  size="small"
                  round
                  effect="light"
                >
                  {{ statusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="上传时间" width="160">
              <template #default="{ row }">
                <span class="doc-time">{{ formatTime(row.created_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="72" fixed="right" align="center">
              <template #default="{ row }">
                <el-button type="danger" size="small" text @click="remove(row)">删除</el-button>
              </template>
            </el-table-column>

            <template #empty>
              <EmptyState
                text="知识库还是空的"
                hint="从左侧上传第一份文档，几分钟后即可被智能客服引用"
              />
            </template>
          </el-table>
        </AppCard>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection, CircleCheck, Files, Clock,
  UploadFilled, Search, Document, Refresh,
} from '@element-plus/icons-vue'
import api from '../api'
import PageHeader from '../components/PageHeader.vue'
import AppCard from '../components/AppCard.vue'
import StatCard from '../components/StatCard.vue'
import EmptyState from '../components/EmptyState.vue'

const uploadRef = ref(null)
const file = ref(null)
const uploading = ref(false)
const loading = ref(false)
const documents = ref([])
const query = ref('')
const searchResults = ref([])
const searching = ref(false)
const searched = ref(false)

// 统计由文档列表派生
const stats = computed(() => {
  const docs = documents.value
  return {
    total: docs.length,
    indexed: docs.filter((d) => d.status === 'indexed').length,
    chunks: docs.reduce((sum, d) => sum + (d.chunk_count || 0), 0),
    pending: docs.filter((d) => d.status === 'pending').length,
    failed: docs.filter((d) => d.status === 'failed').length,
  }
})

const fileExt = (name) => {
  const idx = (name || '').lastIndexOf('.')
  return idx >= 0 ? name.slice(idx + 1).toUpperCase() : 'FILE'
}

const statusType = (s) => ({ indexed: 'success', pending: 'warning', failed: 'danger' }[s] || 'info')
const statusLabel = (s) => ({ indexed: '已索引', pending: '处理中', failed: '失败' }[s] || s)

const formatTime = (t) => {
  if (!t) return '–'
  const d = new Date(t)
  if (Number.isNaN(d.getTime())) return t
  return d.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

const loadDocs = async () => {
  loading.value = true
  try {
    const res = await api.get('/knowledge')
    documents.value = res.documents || []
  } finally {
    loading.value = false
  }
}

const onFileChange = (uploadFile) => {
  file.value = uploadFile.raw
}
const onFileRemove = () => {
  file.value = null
}

const upload = async () => {
  if (!file.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    await api.post('/knowledge/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('上传成功，文档已进入向量化流程')
    file.value = null
    uploadRef.value?.clearFiles()
    loadDocs()
  } finally {
    uploading.value = false
  }
}

const remove = async (row) => {
  await ElMessageBox.confirm(
    `确定删除「${row.filename}」吗？该文档的所有向量片段将一并移除。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  await api.delete(`/knowledge/${row.id}`)
  ElMessage.success('已删除')
  loadDocs()
}

const search = async () => {
  if (!query.value.trim()) return
  searching.value = true
  searched.value = true
  try {
    const res = await api.post('/knowledge/search', { query: query.value, top_k: 5 })
    searchResults.value = res.results || []
  } finally {
    searching.value = false
  }
}

onMounted(loadDocs)
</script>

<style scoped>
.kb-page {
  padding-bottom: 16px;
}
.stat-row {
  margin-bottom: 16px;
}
.stat-row :deep(.el-col) {
  margin-bottom: 16px;
}
.mb-4 {
  margin-bottom: 16px;
}

/* 上传区 */
.kb-upload :deep(.el-upload-dragger) {
  border-radius: var(--radius-md);
  border: 1.5px dashed var(--border-color);
  background: var(--bg-subtle);
  padding: 28px 20px;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.kb-upload :deep(.el-upload-dragger:hover) {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.kb-upload :deep(.el-icon--upload) {
  color: var(--color-primary);
  font-size: 40px;
  margin-bottom: 8px;
}
.kb-upload :deep(.el-upload__text) {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
.kb-upload :deep(.el-upload__text em) {
  color: var(--color-primary);
  font-style: normal;
}
.upload-tip {
  text-align: center;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: 6px;
}
.upload-btn {
  width: 100%;
  margin-top: 14px;
}
.search-btn {
  width: 100%;
  margin-top: 10px;
}
.search-meta {
  margin-top: 14px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

/* 检索命中 */
.hit-list {
  margin-top: 10px;
}
.hit-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--divider);
}
.hit-item:last-child {
  border-bottom: none;
}
.hit-head {
  display: flex;
  align-items: center;
  gap: 5px;
}
.hit-src-icon {
  color: var(--text-tertiary);
}
.hit-source {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hit-score {
  margin-left: auto;
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-primary);
}
.hit-bar {
  height: 3px;
  border-radius: 2px;
  background: var(--divider);
  margin: 8px 0;
  overflow: hidden;
}
.hit-bar-fill {
  height: 100%;
  border-radius: 2px;
  background: var(--color-primary);
  transition: width 0.4s ease;
}
.hit-text {
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 文档单元格 */
.doc-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.doc-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--bg-subtle);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.doc-meta {
  min-width: 0;
}
.doc-name {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-ext {
  font-size: 11px;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
}
.doc-time {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
