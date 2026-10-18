<template>
  <div class="crm-page">
    <PageHeader
      title="客户管理"
      subtitle="客户分级、来源沉淀与跟进记录，帮助团队聚焦高价值客户"
    >
      <template #actions>
        <el-button type="primary" @click="showCreateDialog">
          <el-icon style="margin-right: 4px"><Plus /></el-icon>新建客户
        </el-button>
      </template>
    </PageHeader>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6">
        <StatCard label="总客户数" :value="stats.total || 0" tone="primary">
          <template #icon><el-icon :size="22"><User /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="A 级客户" :value="stats.grade_a || 0" tone="cyan">
          <template #icon><el-icon :size="22"><Medal /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard
          label="待跟进"
          :value="stats.pending_follow_up || 0"
          :tone="(stats.pending_follow_up || 0) > 0 ? 'warning' : 'neutral'"
        >
          <template #icon><el-icon :size="22"><Bell /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="本月新增" :value="stats.month_new || 0" tone="success">
          <template #icon><el-icon :size="22"><TrendCharts /></el-icon></template>
        </StatCard>
      </el-col>
    </el-row>

    <!-- 搜索栏 -->
    <AppCard class="filter-card">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索客户名称、联系人、邮箱…"
        clearable
        style="max-width: 380px"
        @keyup.enter="reload"
        @clear="reload"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" @click="reload">搜索</el-button>
    </AppCard>

    <!-- 客户列表 -->
    <AppCard>
      <el-table :data="customers" v-loading="loading" style="width: 100%">
        <el-table-column prop="company_name" label="客户名称" min-width="210" />
        <el-table-column prop="contact_person" label="联系人" width="110" />
        <el-table-column prop="email" label="邮箱" min-width="200" show-overflow-tooltip />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column label="等级" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="getGradeType(row.grade)" round effect="light">{{ row.grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="100">
          <template #default="{ row }">{{ sourceLabel(row.source) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="viewCustomer(row)">详情</el-button>
            <el-button size="small" text type="primary" @click="showFollowUpDialog(row)">跟进</el-button>
          </template>
        </el-table-column>

        <template #empty>
          <EmptyState text="暂无客户" hint="点击右上角「新建客户」录入第一位客户" />
        </template>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadCustomers"
          @current-change="loadCustomers"
          background
        />
      </div>
    </AppCard>

    <!-- 新建客户对话框 -->
    <el-dialog v-model="createDialogVisible" title="新建客户" width="600px">
      <el-form :model="createForm" label-width="92px">
        <el-form-item label="客户名称" required>
          <el-input v-model="createForm.company_name" placeholder="请输入公司名称" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="createForm.contact_person" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="createForm.email" type="email" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="createForm.phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="createForm.address" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="行业">
          <el-input v-model="createForm.industry" />
        </el-form-item>
        <el-form-item label="客户等级">
          <el-select v-model="createForm.grade" style="width: 100%">
            <el-option label="A 级（重点）" value="A" />
            <el-option label="B 级（潜力）" value="B" />
            <el-option label="C 级（常规）" value="C" />
            <el-option label="D 级（观察）" value="D" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源">
          <el-select v-model="createForm.source" clearable style="width: 100%">
            <el-option label="亚马逊" value="amazon" />
            <el-option label="展会" value="exhibition" />
            <el-option label="官网" value="website" />
            <el-option label="转介绍" value="referral" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.notes" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createCustomer" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 客户详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="客户详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="客户名称">{{ detailData.company_name }}</el-descriptions-item>
        <el-descriptions-item label="联系人">{{ detailData.contact_person }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ detailData.email }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ detailData.phone }}</el-descriptions-item>
        <el-descriptions-item label="地址" :span="2">{{ detailData.address }}</el-descriptions-item>
        <el-descriptions-item label="行业">{{ detailData.industry }}</el-descriptions-item>
        <el-descriptions-item label="等级">
          <el-tag :type="getGradeType(detailData.grade)" round effect="light">{{ detailData.grade }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="来源">{{ sourceLabel(detailData.source) }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(detailData.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detailData.notes }}</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">跟进记录</el-divider>

      <el-timeline v-if="followUps.length">
        <el-timeline-item
          v-for="item in followUps"
          :key="item.id"
          :timestamp="formatTime(item.created_at)"
          placement="top"
        >
          <div class="follow-type">{{ getContactTypeLabel(item.contact_type) }}</div>
          <div class="follow-content">{{ item.content }}</div>
          <div v-if="item.next_follow_date" class="next-follow">
            <el-icon :size="13"><Clock /></el-icon>
            下次跟进：{{ formatTime(item.next_follow_date) }}
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无跟进记录" :image-size="80" />

      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button type="success" plain @click="openEmailDialog">
          <el-icon><Promotion /></el-icon>AI 写邮件
        </el-button>
        <el-button type="primary" @click="showFollowUpDialog(detailData)">新增跟进</el-button>
      </template>
    </el-dialog>

    <!-- AI 写邮件对话框 -->
    <el-dialog v-model="emailDialogVisible" title="AI 写客户邮件" width="620px">
      <el-form label-width="92px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="邮件类型">
              <el-select v-model="emailForm.email_type" style="width: 100%">
                <el-option label="开发信（首次触达）" value="development" />
                <el-option label="跟进邮件" value="follow_up" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="语言">
              <el-select v-model="emailForm.language" style="width: 100%">
                <el-option label="英语" value="en" />
                <el-option label="德语" value="de" />
                <el-option label="日语" value="ja" />
                <el-option label="法语" value="fr" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="补充信息">
          <el-input v-model="emailForm.context" type="textarea" :rows="2" placeholder="选填：产品、报价、卖点等，会作为写作依据" />
        </el-form-item>
      </el-form>

      <div v-if="emailResult" class="email-result">
        <el-input v-model="emailResult" type="textarea" :rows="11" readonly />
      </div>

      <template #footer>
        <el-button @click="emailDialogVisible = false">关闭</el-button>
        <el-button v-if="emailResult" @click="copyEmail">
          <el-icon><CopyDocument /></el-icon>复制
        </el-button>
        <el-button type="primary" @click="generateEmail" :loading="emailLoading">
          {{ emailLoading ? '写作中…' : '生成邮件' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 跟进记录对话框 -->
    <el-dialog v-model="followUpDialogVisible" title="新增跟进记录" width="500px">
      <el-form :model="followUpForm" label-width="92px">
        <el-form-item label="联系方式" required>
          <el-select v-model="followUpForm.contact_type" style="width: 100%">
            <el-option label="电话" value="phone" />
            <el-option label="邮件" value="email" />
            <el-option label="面谈" value="meeting" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="跟进内容" required>
          <el-input v-model="followUpForm.content" type="textarea" :rows="4" placeholder="记录本次沟通要点、客户反馈与下一步动作" />
        </el-form-item>
        <el-form-item label="下次跟进">
          <el-date-picker
            v-model="followUpForm.next_follow_date"
            type="datetime"
            placeholder="选择日期时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="followUpDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createFollowUp" :loading="creatingFollowUp">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus, User, Medal, Bell, TrendCharts, Clock,
  Promotion, CopyDocument,
} from '@element-plus/icons-vue'
import api from '../api'
import PageHeader from '../components/PageHeader.vue'
import AppCard from '../components/AppCard.vue'
import StatCard from '../components/StatCard.vue'
import EmptyState from '../components/EmptyState.vue'

// 统计数据
const stats = ref({})

// 客户列表
const customers = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')

// 新建客户
const createDialogVisible = ref(false)
const creating = ref(false)
const createForm = ref({
  company_name: '',
  contact_person: '',
  email: '',
  phone: '',
  address: '',
  industry: '',
  grade: 'C',
  source: '',
  notes: '',
})

// 客户详情
const detailDialogVisible = ref(false)
const detailData = ref({})
const followUps = ref([])

// 跟进记录
const followUpDialogVisible = ref(false)
const creatingFollowUp = ref(false)
const followUpForm = ref({
  customer_id: null,
  contact_type: 'phone',
  content: '',
  next_follow_date: null,
})

// 加载统计数据
const loadStats = async () => {
  try {
    stats.value = await api.get('/crm/stats/overview')
  } catch (error) {
    console.error('加载统计失败', error)
  }
}

const reload = () => {
  currentPage.value = 1
  loadCustomers()
}

// 加载客户列表
const loadCustomers = async () => {
  loading.value = true
  try {
    const res = await api.get('/crm/customers', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        keyword: searchKeyword.value || undefined,
      },
    })
    customers.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    ElMessage.error('加载客户列表失败')
  } finally {
    loading.value = false
  }
}

// 显示新建对话框
const showCreateDialog = () => {
  createForm.value = {
    company_name: '',
    contact_person: '',
    email: '',
    phone: '',
    address: '',
    industry: '',
    grade: 'C',
    source: '',
    notes: '',
  }
  createDialogVisible.value = true
}

// 创建客户
const createCustomer = async () => {
  if (!createForm.value.company_name) {
    ElMessage.warning('请输入客户名称')
    return
  }

  creating.value = true
  try {
    await api.post('/crm/customers', createForm.value)
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    loadCustomers()
    loadStats()
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

// 查看客户详情
const viewCustomer = async (row) => {
  try {
    detailData.value = await api.get(`/crm/customers/${row.id}`)
    followUps.value = await api.get(`/crm/customers/${row.id}/follow-ups`)
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载详情失败')
  }
}

// 显示跟进对话框
const showFollowUpDialog = (row) => {
  followUpForm.value = {
    customer_id: row.id,
    contact_type: 'phone',
    content: '',
    next_follow_date: null,
  }
  followUpDialogVisible.value = true
}

// 创建跟进记录
const createFollowUp = async () => {
  if (!followUpForm.value.content) {
    ElMessage.warning('请输入跟进内容')
    return
  }

  creatingFollowUp.value = true
  try {
    await api.post('/crm/follow-ups', followUpForm.value)
    ElMessage.success('跟进记录已保存')
    followUpDialogVisible.value = false
    loadStats()

    // 刷新详情
    if (detailDialogVisible.value) {
      followUps.value = await api.get(`/crm/customers/${detailData.value.id}/follow-ups`)
    }
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    creatingFollowUp.value = false
  }
}

// 辅助函数
const getGradeType = (grade) => {
  // 等级是分类而非危险状态，统一克制配色
  const map = { A: 'primary', B: 'warning', C: 'info', D: 'info' }
  return map[grade] || 'info'
}

const sourceLabel = (s) =>
  ({ amazon: '亚马逊', exhibition: '展会', website: '官网', referral: '转介绍', other: '其他' }[s] || s || '–')

const getContactTypeLabel = (type) => {
  const map = { phone: '电话沟通', email: '邮件往来', meeting: '当面会谈', other: '其他方式' }
  return map[type] || type
}

const formatTime = (time) => {
  if (!time) return '–'
  return new Date(time).toLocaleString('zh-CN')
}

// ---------- AI 写邮件 ----------
const emailDialogVisible = ref(false)
const emailLoading = ref(false)
const emailResult = ref('')
const emailForm = ref({
  email_type: 'development',
  language: 'en',
  context: '',
})

const openEmailDialog = () => {
  emailForm.value = { email_type: 'development', language: 'en', context: '' }
  emailResult.value = ''
  emailDialogVisible.value = true
}

const generateEmail = async () => {
  emailLoading.value = true
  try {
    const res = await api.post('/crm/ai/generate-email', {
      customer_id: detailData.value.id,
      email_type: emailForm.value.email_type,
      language: emailForm.value.language,
      context: emailForm.value.context || null,
    })
    emailResult.value = res.email
  } catch (e) {
    ElMessage.error('邮件生成失败，请稍后重试')
  } finally {
    emailLoading.value = false
  }
}

const copyEmail = async () => {
  try {
    await navigator.clipboard.writeText(emailResult.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.warning('复制失败，请手动选择文本复制')
  }
}

onMounted(() => {
  loadStats()
  loadCustomers()
})
</script>

<style scoped>
.stat-row {
  margin-bottom: 16px;
}
.stat-row :deep(.el-col) {
  margin-bottom: 16px;
}
.email-result {
  margin-top: 4px;
}
.filter-card {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.filter-card :deep(.el-card__body) {
  display: flex;
  gap: 10px;
  width: 100%;
  align-items: center;
  padding: 14px 18px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.follow-type {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.follow-content {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.6;
}
.next-follow {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: var(--font-size-xs);
  color: var(--color-warning);
}
</style>
