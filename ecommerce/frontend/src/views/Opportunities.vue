<template>
  <div class="page">
    <PageHeader title="商机管理" subtitle="跟踪每个潜在成交机会，从初步接触到赢单的全销售管道">
      <template #actions>
        <el-radio-group v-model="viewMode" size="default">
          <el-radio-button value="board">看板</el-radio-button>
          <el-radio-button value="list">列表</el-radio-button>
        </el-radio-group>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          新建商机
        </el-button>
      </template>
    </PageHeader>

    <!-- 管道概览 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6">
        <StatCard label="进行中商机" :value="pipeline.total_open || 0" tone="primary">
          <template #icon><el-icon :size="22"><DataLine /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="加权管道金额" :value="formatMoney(pipeline.weighted_pipeline)" prefix="$" tone="cyan">
          <template #sub>按赢单概率加权</template>
          <template #icon><el-icon :size="22"><Coin /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="赢单率" :value="`${pipeline.win_rate || 0}%`" tone="success">
          <template #sub>成交 / 已结案</template>
          <template #icon><el-icon :size="22"><Trophy /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="已成交" :value="wonStat.count" tone="warning">
          <template #sub>$ {{ formatMoney(wonStat.amount) }}</template>
          <template #icon><el-icon :size="22"><Select /></el-icon></template>
        </StatCard>
      </el-col>
    </el-row>

    <!-- ============ 看板视图 ============ -->
    <div v-if="viewMode === 'board'" class="board" v-loading="boardLoading">
      <div v-for="col in board.columns" :key="col.key" class="board-col">
        <div class="board-col-head">
          <span class="board-col-title">{{ col.label }}</span>
          <span class="board-col-count">{{ col.items.length }}</span>
        </div>

        <div class="board-col-body">
          <div
            v-for="item in col.items"
            :key="item.id"
            class="opp-card"
            @click="openEdit(item)"
          >
            <div class="opp-card-title">{{ item.title }}</div>
            <div class="opp-card-customer">
              <el-icon :size="12"><User /></el-icon>
              {{ item.customer_name || '未知客户' }}
            </div>
            <div class="opp-card-amount">$ {{ formatMoney(item.expected_amount) }}</div>

            <div class="opp-card-foot">
              <div class="prob">
                <div class="prob-bar"><div class="prob-inner" :style="{ width: item.probability + '%' }"></div></div>
                <span class="prob-text">{{ item.probability }}%</span>
              </div>
              <el-button
                size="small"
                text
                type="primary"
                class="advance-btn"
                @click.stop="openMove(item)"
              >
                推进<el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
          </div>

          <div v-if="!col.items.length" class="board-empty">暂无商机</div>
        </div>
      </div>
    </div>

    <!-- ============ 列表视图 ============ -->
    <AppCard v-else>
      <div class="list-toolbar">
        <el-select v-model="listStageFilter" placeholder="全部阶段" clearable style="width: 160px" @change="loadList">
          <el-option v-for="s in allStages" :key="s.key" :label="s.label" :value="s.key" />
        </el-select>
      </div>

      <el-table :data="listItems" v-loading="listLoading" stripe>
        <el-table-column prop="title" label="商机名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="customer_name" label="客户" width="180" show-overflow-tooltip />
        <el-table-column label="阶段" width="110">
          <template #default="{ row }">
            <el-tag :type="stageTagType(row.stage)" size="small" round effect="light">
              {{ stageLabel(row.stage) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预计金额" width="130" align="right">
          <template #default="{ row }">$ {{ formatMoney(row.expected_amount) }}</template>
        </el-table-column>
        <el-table-column label="赢单率" width="150">
          <template #default="{ row }">
            <div class="prob">
              <div class="prob-bar"><div class="prob-inner" :style="{ width: row.probability + '%' }"></div></div>
              <span class="prob-text">{{ row.probability }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="预计成交" width="120">
          <template #default="{ row }">
            <span class="text-secondary">{{ closeDate(row.expected_close_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="openMove(row)">推进</el-button>
            <el-button size="small" text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </AppCard>

    <!-- ============ 新建/编辑对话框 ============ -->
    <el-dialog v-model="formVisible" :title="formIsEdit ? '编辑商机' : '新建商机'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="商机名称" required>
          <el-input v-model="form.title" placeholder="如：XX公司 Q4 采购项目" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="所属客户" required>
              <el-select v-model="form.customer_id" filterable placeholder="选择客户" style="width: 100%">
                <el-option v-for="c in customers" :key="c.id" :label="c.company_name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="销售阶段">
              <el-select v-model="form.stage" style="width: 100%">
                <el-option v-for="s in allStages" :key="s.key" :label="s.label" :value="s.key" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="预计金额">
              <el-input-number v-model="form.expected_amount" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="币种">
              <el-select v-model="form.currency" style="width: 100%">
                <el-option label="USD" value="USD" />
                <el-option label="EUR" value="EUR" />
                <el-option label="GBP" value="GBP" />
                <el-option label="JPY" value="JPY" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="预计成交">
              <el-date-picker v-model="form.expected_close_date" type="date" placeholder="选择日期" style="width: 100%" value-format="YYYY-MM-DDTHH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="赢单概率">
              <el-input-number v-model="form.probability" :min="0" :max="100" :step="10" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="saveForm" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- ============ 阶段推进对话框 ============ -->
    <el-dialog v-model="moveVisible" title="推进商机阶段" width="460px">
      <el-form label-width="90px">
        <el-form-item label="商机">
          <span class="move-title">{{ moveTarget.title }}</span>
        </el-form-item>
        <el-form-item label="目标阶段">
          <el-select v-model="moveStage" style="width: 100%">
            <el-option v-for="s in allStages" :key="s.key" :label="s.label" :value="s.key" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="moveStage === 'won' || moveStage === 'lost'" :label="moveStage === 'won' ? '成交说明' : '流失原因'">
          <el-input v-model="moveReason" type="textarea" :rows="3" :placeholder="moveStage === 'won' ? '成交金额、关键因素…' : '流失原因、竞争对手…'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moveVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmMove" :loading="moving">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, DataLine, Coin, Trophy, Select, User, ArrowRight,
} from '@element-plus/icons-vue'
import api from '../api'
import PageHeader from '../components/PageHeader.vue'
import AppCard from '../components/AppCard.vue'
import StatCard from '../components/StatCard.vue'

// ---------- 阶段元数据 ----------
const allStages = ref([])

// ---------- 视图与统计 ----------
const viewMode = ref('board')
const pipeline = ref({})
const board = ref({ columns: [] })
const boardLoading = ref(false)
const listItems = ref([])
const listLoading = ref(false)
const listStageFilter = ref('')

const customers = ref([])

const wonStat = computed(() => {
  const won = (pipeline.value.by_stage || []).find((s) => s.key === 'won')
  return { count: won?.count || 0, amount: won?.amount || 0 }
})

// ---------- 加载 ----------
const loadStages = async () => {
  const res = await api.get('/opportunities/stages')
  allStages.value = res.stages
}

const loadPipeline = async () => {
  pipeline.value = await api.get('/opportunities/stats/pipeline')
}

const loadBoard = async () => {
  boardLoading.value = true
  try {
    board.value = await api.get('/opportunities/board/data')
  } finally {
    boardLoading.value = false
  }
}

const loadList = async () => {
  listLoading.value = true
  try {
    const res = await api.get('/opportunities', {
      params: { stage: listStageFilter.value || undefined },
    })
    listItems.value = res.items
  } finally {
    listLoading.value = false
  }
}

const loadCustomers = async () => {
  const res = await api.get('/crm/customers', { params: { page: 1, page_size: 100 } })
  customers.value = res.items || []
}

const refreshAll = () => {
  loadPipeline()
  if (viewMode.value === 'board') loadBoard()
  else loadList()
}

// ---------- 新建/编辑 ----------
const formVisible = ref(false)
const formIsEdit = ref(false)
const saving = ref(false)
const emptyForm = () => ({
  title: '', customer_id: null, stage: 'lead', expected_amount: 0,
  currency: 'USD', expected_close_date: null, probability: 20, notes: '',
})
const form = ref(emptyForm())

const openCreate = () => {
  formIsEdit.value = false
  form.value = emptyForm()
  formVisible.value = true
}

const openEdit = (item) => {
  formIsEdit.value = true
  form.value = {
    id: item.id,
    title: item.title,
    customer_id: item.customer_id,
    stage: item.stage,
    expected_amount: item.expected_amount,
    currency: item.currency,
    expected_close_date: item.expected_close_date,
    probability: item.probability,
    notes: item.notes || '',
  }
  formVisible.value = true
}

const saveForm = async () => {
  if (!form.value.title || !form.value.customer_id) {
    ElMessage.warning('请填写商机名称并选择客户')
    return
  }
  saving.value = true
  try {
    if (formIsEdit.value) {
      await api.put(`/opportunities/${form.value.id}`, form.value)
      ElMessage.success('已更新')
    } else {
      await api.post('/opportunities', form.value)
      ElMessage.success('已创建')
    }
    formVisible.value = false
    refreshAll()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail ? String(e.response.data.detail) : '保存失败')
  } finally {
    saving.value = false
  }
}

// ---------- 阶段推进 ----------
const moveVisible = ref(false)
const moveTarget = ref({})
const moveStage = ref('lead')
const moveReason = ref('')
const moving = ref(false)

const openMove = (item) => {
  moveTarget.value = item
  moveStage.value = item.stage
  moveReason.value = ''
  moveVisible.value = true
}

const confirmMove = async () => {
  if ((moveStage.value === 'won' || moveStage.value === 'lost') && !moveReason.value.trim()) {
    ElMessage.warning(moveStage.value === 'won' ? '请填写成交说明' : '请填写流失原因')
    return
  }
  moving.value = true
  try {
    await api.patch(`/opportunities/${moveTarget.value.id}/stage`, {
      stage: moveStage.value,
      close_reason: moveReason.value || null,
    })
    ElMessage.success('阶段已更新')
    moveVisible.value = false
    refreshAll()
  } catch (e) {
    ElMessage.error('操作失败')
  } finally {
    moving.value = false
  }
}

// ---------- 删除 ----------
const remove = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除商机「${row.title}」？`, '删除确认', {
      type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消',
    })
    await api.delete(`/opportunities/${row.id}`)
    ElMessage.success('已删除')
    refreshAll()
  } catch {
    /* 取消 */
  }
}

// ---------- 辅助 ----------
const stageLabel = (key) => allStages.value.find((s) => s.key === key)?.label || key

const stageTagType = (key) => ({
  lead: 'info', need: '', quote: 'warning',
  negotiation: 'warning', won: 'success', lost: 'danger',
}[key] || 'info')

const formatMoney = (v) => Number(v || 0).toLocaleString('en-US', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
})

const closeDate = (iso) => (iso ? iso.slice(0, 10) : '–')

// 切换视图时按需加载
const onViewChange = () => {
  if (viewMode.value === 'list' && !listItems.value.length) loadList()
  if (viewMode.value === 'board') loadBoard()
}

watch(viewMode, onViewChange)

onMounted(async () => {
  await loadStages()
  await Promise.all([loadPipeline(), loadBoard(), loadCustomers()])
})
</script>

<style scoped>
.page { padding: 20px; }
.stat-row { margin-bottom: 20px; }
.stat-row .el-col { margin-bottom: 12px; }

/* ---------- 看板 ---------- */
.board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  align-items: start;
}
.board-col {
  background: var(--bg-subtle, #f5f7fa);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  min-height: 200px;
  display: flex;
  flex-direction: column;
}
.board-col-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
}
.board-col-title { font-weight: 600; font-size: 14px; color: var(--text-primary); }
.board-col-count {
  font-size: 12px;
  background: var(--color-info-soft, #e9ecef);
  color: var(--text-secondary);
  border-radius: 10px;
  padding: 1px 9px;
}
.board-col-body { padding: 10px; display: flex; flex-direction: column; gap: 10px; flex: 1; }
.board-empty {
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
  padding: 24px 0;
  border: 1px dashed var(--border-color);
  border-radius: 8px;
}

.opp-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: box-shadow 0.18s ease, transform 0.18s ease;
}
.opp-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.opp-card-title { font-weight: 600; font-size: 14px; color: var(--text-primary); margin-bottom: 6px; }
.opp-card-customer {
  display: flex; align-items: center; gap: 4px;
  font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;
}
.opp-card-amount { font-size: 15px; font-weight: 700; color: var(--color-primary); margin-bottom: 10px; }
.opp-card-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.advance-btn { font-weight: 500; padding: 0; }

/* ---------- 概率条 ---------- */
.prob { display: flex; align-items: center; gap: 6px; flex: 1; }
.prob-bar {
  flex: 1; height: 5px; background: var(--color-info-soft, #e9ecef);
  border-radius: 3px; overflow: hidden; min-width: 40px;
}
.prob-inner { height: 100%; background: var(--color-primary); border-radius: 3px; transition: width 0.3s; }
.prob-text { font-size: 11px; color: var(--text-tertiary); white-space: nowrap; }

/* ---------- 列表 ---------- */
.list-toolbar { margin-bottom: 14px; }
.text-secondary { color: var(--text-secondary); font-size: 13px; }
.move-title { font-weight: 600; color: var(--text-primary); }

@media (max-width: 1100px) {
  .board { grid-template-columns: repeat(2, 1fr); }
}
</style>
