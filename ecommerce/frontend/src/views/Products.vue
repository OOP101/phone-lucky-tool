<template>
  <div class="prod-page">
    <PageHeader
      title="商品管理"
      subtitle="维护本地商品档案、库存与成本，同步关联亚马逊 ASIN 与站点"
    >
      <template #actions>
        <el-button type="primary" @click="showCreateDialog">
          <el-icon style="margin-right: 4px"><Plus /></el-icon>新建商品
        </el-button>
      </template>
    </PageHeader>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6">
        <StatCard label="总商品数" :value="stats.total || 0" tone="primary">
          <template #icon><el-icon :size="22"><Goods /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="在售商品" :value="stats.active || 0" tone="cyan">
          <template #icon><el-icon :size="22"><Sell /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard
          label="低库存"
          :value="stats.low_stock || 0"
          :tone="(stats.low_stock || 0) > 0 ? 'danger' : 'neutral'"
        >
          <template #icon><el-icon :size="22"><Warning /></el-icon></template>
        </StatCard>
      </el-col>
      <el-col :xs="12" :sm="6">
        <StatCard label="库存总值" :value="`¥${formatMoney(stats.total_value)}`" tone="neutral">
          <template #icon><el-icon :size="22"><Money /></el-icon></template>
        </StatCard>
      </el-col>
    </el-row>

    <!-- 搜索栏 -->
    <AppCard class="filter-card">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索商品名称、SKU、ASIN…"
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
      <el-button
        type="success"
        plain
        :loading="syncing"
        class="sync-btn"
        @click="syncFromAmazon"
      >
        <el-icon v-if="!syncing"><Refresh /></el-icon>
        {{ syncing ? '同步中…' : '从亚马逊同步' }}
      </el-button>
    </AppCard>

    <!-- 商品列表 -->
    <AppCard>
      <el-table :data="products" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="商品名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="sku" label="SKU" width="130">
          <template #default="{ row }">
            <span class="mono">{{ row.sku }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="110" />
        <el-table-column prop="brand" label="品牌" width="100" />
        <el-table-column label="售价" width="110">
          <template #default="{ row }">
            <span class="price">{{ row.currency }} {{ row.selling_price }}</span>
          </template>
        </el-table-column>
        <el-table-column label="库存" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.stock_quantity < 10" type="danger" size="small" round effect="light">
              {{ row.stock_quantity }}
            </el-tag>
            <span v-else class="stock-ok">{{ row.stock_quantity }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="amazon_asin" label="ASIN" width="120">
          <template #default="{ row }">
            <span class="mono">{{ row.amazon_asin || '–' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'active' ? 'success' : 'info'"
              size="small"
              round
              effect="light"
            >
              {{ row.status === 'active' ? '在售' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="viewProduct(row)">详情</el-button>
            <el-button size="small" text type="primary" @click="editProduct(row)">编辑</el-button>
          </template>
        </el-table-column>

        <template #empty>
          <EmptyState text="暂无商品" hint="点击右上角「新建商品」录入第一件商品" />
        </template>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadProducts"
          @current-change="loadProducts"
          background
        />
      </div>
    </AppCard>

    <!-- 新建/编辑商品对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑商品' : '新建商品'" width="700px">
      <el-form :model="form" label-width="92px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="SKU" required>
              <el-input v-model="form.sku" :disabled="isEdit" placeholder="如 LED-STRIP-5M" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="商品名称" required>
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="分类">
              <el-input v-model="form.category" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="品牌">
              <el-input v-model="form.brand" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="成本价">
              <el-input-number v-model="form.cost_price" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="售价">
              <el-input-number v-model="form.selling_price" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="币种">
              <el-select v-model="form.currency" style="width: 100%">
                <el-option label="USD" value="USD" />
                <el-option label="EUR" value="EUR" />
                <el-option label="GBP" value="GBP" />
                <el-option label="JPY" value="JPY" />
                <el-option label="CNY" value="CNY" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="库存数量">
              <el-input-number v-model="form.stock_quantity" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="在售" value="active" />
                <el-option label="下架" value="inactive" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="亚马逊 ASIN">
              <el-input v-model="form.amazon_asin" placeholder="如 B0XXXXXXXX" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="亚马逊站点">
              <el-select v-model="form.amazon_marketplace" clearable style="width: 100%">
                <el-option label="美国 US" value="US" />
                <el-option label="英国 UK" value="UK" />
                <el-option label="德国 DE" value="DE" />
                <el-option label="日本 JP" value="JP" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveProduct" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 商品详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="商品详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="商品名称">{{ detailData.name }}</el-descriptions-item>
        <el-descriptions-item label="SKU">{{ detailData.sku }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ detailData.category }}</el-descriptions-item>
        <el-descriptions-item label="品牌">{{ detailData.brand }}</el-descriptions-item>
        <el-descriptions-item label="成本价">{{ detailData.currency }} {{ detailData.cost_price }}</el-descriptions-item>
        <el-descriptions-item label="售价">{{ detailData.currency }} {{ detailData.selling_price }}</el-descriptions-item>
        <el-descriptions-item label="库存">
          <el-tag v-if="detailData.stock_quantity < 10" type="danger" round effect="light">
            {{ detailData.stock_quantity }}
          </el-tag>
          <span v-else>{{ detailData.stock_quantity }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag
            :type="detailData.status === 'active' ? 'success' : 'info'"
            round
            effect="light"
          >
            {{ detailData.status === 'active' ? '在售' : '下架' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="亚马逊 ASIN">{{ detailData.amazon_asin || '–' }}</el-descriptions-item>
        <el-descriptions-item label="亚马逊站点">{{ detailData.amazon_marketplace || '–' }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ detailData.description }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(detailData.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatTime(detailData.updated_at) }}</el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="editProduct(detailData)">编辑</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus, Goods, Sell, Warning, Money, Refresh } from '@element-plus/icons-vue'
import api from '../api'
import PageHeader from '../components/PageHeader.vue'
import AppCard from '../components/AppCard.vue'
import StatCard from '../components/StatCard.vue'
import EmptyState from '../components/EmptyState.vue'

// 统计数据
const stats = ref({})

// 商品列表
const products = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')
const syncing = ref(false)

// 新建/编辑
const dialogVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const form = ref({
  sku: '',
  name: '',
  category: '',
  brand: '',
  description: '',
  cost_price: 0,
  selling_price: 0,
  currency: 'USD',
  stock_quantity: 0,
  amazon_asin: '',
  amazon_marketplace: '',
  status: 'active',
})

// 详情
const detailDialogVisible = ref(false)
const detailData = ref({})

// 加载统计数据
const loadStats = async () => {
  try {
    stats.value = await api.get('/products/stats/overview')
  } catch (error) {
    console.error('加载统计失败', error)
  }
}

const reload = () => {
  currentPage.value = 1
  loadProducts()
}

// 加载商品列表
const loadProducts = async () => {
  loading.value = true
  try {
    const res = await api.get('/products', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        keyword: searchKeyword.value || undefined,
      },
    })
    products.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    ElMessage.error('加载商品列表失败')
  } finally {
    loading.value = false
  }
}

// 从亚马逊同步商品
const syncFromAmazon = async () => {
  syncing.value = true
  try {
    const res = await api.post('/products/sync-from-amazon', null, {
      params: { marketplace: 'US' },
    })
    ElMessage.success(`同步完成：新增 ${res.created} 个，更新 ${res.updated} 个`)
    loadProducts()
    loadStats()
  } catch (error) {
    ElMessage.error('同步失败，请检查亚马逊连接状态')
  } finally {
    syncing.value = false
  }
}

// 显示新建对话框
const showCreateDialog = () => {
  isEdit.value = false
  form.value = {
    sku: '',
    name: '',
    category: '',
    brand: '',
    description: '',
    cost_price: 0,
    selling_price: 0,
    currency: 'USD',
    stock_quantity: 0,
    amazon_asin: '',
    amazon_marketplace: '',
    status: 'active',
  }
  dialogVisible.value = true
}

// 编辑商品
const editProduct = (row) => {
  isEdit.value = true
  form.value = { ...row }
  detailDialogVisible.value = false
  dialogVisible.value = true
}

// 保存商品
const saveProduct = async () => {
  if (!form.value.sku || !form.value.name) {
    ElMessage.warning('请填写 SKU 和商品名称')
    return
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/products/${form.value.id}`, form.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/products', form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadProducts()
    loadStats()
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 查看详情
const viewProduct = async (row) => {
  try {
    detailData.value = await api.get(`/products/${row.id}`)
    detailDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载详情失败')
  }
}

// 辅助函数
const formatMoney = (value) => {
  if (!value) return '0.00'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatTime = (time) => {
  if (!time) return '–'
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  loadStats()
  loadProducts()
})
</script>

<style scoped>
.stat-row {
  margin-bottom: 16px;
}
.stat-row :deep(.el-col) {
  margin-bottom: 16px;
}
.filter-card {
  margin-bottom: 16px;
}
.filter-card :deep(.el-card__body) {
  display: flex;
  gap: 10px;
  width: 100%;
  align-items: center;
  padding: 14px 18px;
}
.sync-btn {
  margin-left: auto;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.mono {
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
.price {
  font-weight: 600;
  color: var(--text-primary);
}
.stock-ok {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
</style>
