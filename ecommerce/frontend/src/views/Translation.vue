<template>
  <div class="trans-page">
    <PageHeader
      title="翻译引擎"
      subtitle="术语库保证专业词汇一致性，翻译记忆自动复用历史译文，兼顾质量与成本"
    />

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <AppCard>
          <template #title>
            <div class="panel-head">
              <span class="panel-title">原文</span>
              <el-select v-model="form.source_language" size="small" style="width: 130px">
                <el-option v-for="l in langs" :key="l.code" :label="l.name" :value="l.code" />
              </el-select>
            </div>
          </template>
          <el-input
            v-model="form.text"
            type="textarea"
            :rows="13"
            resize="none"
            placeholder="请输入待翻译的文本…"
            class="trans-textarea"
          />
          <div class="char-count">{{ form.text.length }} 字</div>
        </AppCard>
      </el-col>

      <el-col :xs="24" :md="12">
        <AppCard class="result-panel">
          <template #title>
            <div class="panel-head">
              <span class="panel-title">译文</span>
              <el-select v-model="form.target_language" size="small" style="width: 130px">
                <el-option v-for="l in langs" :key="l.code" :label="l.name" :value="l.code" />
              </el-select>
            </div>
          </template>

          <div class="translation-box">
            <template v-if="loading">
              <span class="loading-dots"><span></span><span></span><span></span></span>
              <div class="empty-text">正在翻译…</div>
            </template>
            <template v-else-if="result">
              <div class="result-text">{{ result.translation }}</div>
            </template>
            <template v-else>
              <el-icon :size="34" class="empty-icon"><Switch /></el-icon>
              <div class="empty-text">译文将显示在这里</div>
            </template>
          </div>

          <div v-if="result && !loading" class="translation-meta">
            <el-tag
              size="small"
              :type="result.source === 'memory' ? 'success' : 'primary'"
              effect="light"
              round
            >
              {{ result.source === 'memory' ? '翻译记忆命中' : '模型翻译' }}
            </el-tag>
            <el-button text type="primary" size="small" @click="copy">
              <el-icon style="margin-right: 3px"><CopyDocument /></el-icon>复制
            </el-button>
          </div>
        </AppCard>
      </el-col>
    </el-row>

    <!-- 操作栏 -->
    <AppCard class="action-bar">
      <div class="options">
        <el-checkbox v-model="form.use_terminology">使用术语库</el-checkbox>
        <el-checkbox v-model="form.use_memory">启用翻译记忆</el-checkbox>
      </div>
      <el-button type="primary" size="large" :loading="loading" @click="translate">
        {{ loading ? '翻译中…' : '立即翻译' }}
      </el-button>
    </AppCard>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Switch, CopyDocument } from '@element-plus/icons-vue'
import api from '../api'
import PageHeader from '../components/PageHeader.vue'
import AppCard from '../components/AppCard.vue'

const langs = [
  { code: 'zh', name: '中文' },
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
]

const form = ref({
  text: '',
  source_language: 'zh',
  target_language: 'en',
  use_terminology: true,
  use_memory: true,
})
const loading = ref(false)
const result = ref(null)

const translate = async () => {
  if (!form.value.text.trim()) {
    ElMessage.warning('请输入待翻译文本')
    return
  }
  loading.value = true
  result.value = null
  try {
    result.value = await api.post('/translation/translate', form.value)
  } finally {
    loading.value = false
  }
}

const copy = async () => {
  try {
    await navigator.clipboard.writeText(result.value.translation)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.trans-page {
  padding-bottom: 16px;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.panel-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
}
.trans-textarea :deep(.el-textarea__inner) {
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  line-height: 1.7;
  background: var(--bg-subtle);
  box-shadow: none;
}
.trans-textarea :deep(.el-textarea__inner:focus) {
  box-shadow: none;
  border-color: var(--color-primary);
}
.char-count {
  text-align: right;
  margin-top: 8px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.translation-box {
  min-height: 300px;
  max-height: 420px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--bg-subtle);
  border-radius: var(--radius-sm);
  padding: 18px;
}
.result-panel {
  height: 100%;
}
.empty-icon {
  color: var(--text-tertiary);
}
.empty-text {
  margin-top: 10px;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}
.result-text {
  width: 100%;
  font-size: var(--font-size-base);
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-wrap;
}
.translation-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
}

.action-bar {
  margin-top: 16px;
}
.action-bar :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
}
.options {
  display: flex;
  gap: 24px;
}
.action-bar .el-button {
  min-width: 132px;
}
</style>
