<template>
  <div class="analytics-page">
    <PageHeader
      title="数据洞察"
      subtitle="客服会话量、意图分布、满意度与 Token 消耗的运营总览"
    />

    <!-- KPI -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :xs="12" :sm="6" v-for="k in kpis" :key="k.label">
        <StatCard :label="k.label" :value="k.value" :loading="!data" :tone="k.tone">
          <template #sub>{{ k.sub }}</template>
          <template #icon><el-icon :size="22"><component :is="k.icon" /></el-icon></template>
        </StatCard>
      </el-col>
    </el-row>

    <!-- 图表 -->
    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <AppCard title="意图分布" extra="客服问题类型占比">
          <div ref="intentChart" class="chart"></div>
        </AppCard>
      </el-col>
      <el-col :xs="24" :md="12">
        <AppCard title="近 7 日对话趋势" extra="每日会话量">
          <div ref="trendChart" class="chart"></div>
        </AppCard>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ChatDotRound, Timer, Star, Coin } from '@element-plus/icons-vue'
import api from '../api'
import PageHeader from '../components/PageHeader.vue'
import AppCard from '../components/AppCard.vue'
import StatCard from '../components/StatCard.vue'

// iOS 数据可视化色板（仅图表内使用）
const IOS_PALETTE = ['#1d4ed8', '#5ac8fa', '#34c759', '#ff9500', '#ff3b30', '#af52de', '#8e8e93']

const INTENT_LABELS = {
  order: '订单查询',
  after_sales: '售后处理',
  product: '产品咨询',
  translation: '翻译',
  human: '人工转接',
}

const intentChart = ref(null)
const trendChart = ref(null)
const data = ref(null)
let intentInst = null
let trendInst = null

const kpis = computed(() => {
  const d = data.value?.kpi || {}
  return [
    {
      label: '累计对话数',
      value: d.total_conversations ?? 0,
      sub: '智能客服总会话',
      icon: ChatDotRound,
      tone: 'primary',
    },
    {
      label: '平均响应延迟',
      value: d.avg_latency_ms ?? 0,
      sub: '单位：毫秒',
      icon: Timer,
      tone: 'cyan',
    },
    {
      label: '客服满意度',
      value: d.avg_rating ?? 0,
      sub: '用户评价均分',
      icon: Star,
      tone: 'warning',
    },
    {
      label: 'Token 消耗',
      value: (d.total_prompt_tokens ?? 0) + (d.total_completion_tokens ?? 0),
      sub: '提示 + 补全',
      icon: Coin,
      tone: 'neutral',
    },
  ]
})

const load = async () => {
  data.value = await api.get('/analytics/dashboard')
  renderCharts()
}

const renderCharts = () => {
  if (!data.value) return

  const intentData = data.value.intent_distribution || []
  if (intentChart.value) {
    intentInst?.dispose()
    intentInst = echarts.init(intentChart.value)
    intentInst.setOption({
      color: IOS_PALETTE,
      tooltip: {
        trigger: 'item',
        formatter: '{b}：{c} 次（{d}%）',
      },
      legend: {
        bottom: 0,
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: '#86868b', fontSize: 12 },
      },
      series: [
        {
          type: 'pie',
          radius: ['46%', '70%'],
          center: ['50%', '44%'],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          data: intentData.map((i) => ({
            name: INTENT_LABELS[i.intent] || i.intent,
            value: i.count,
          })),
        },
      ],
    })
  }

  const trend = data.value.conversation_trend || []
  if (trendChart.value) {
    trendInst?.dispose()
    trendInst = echarts.init(trendChart.value)
    trendInst.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: '#d2d2d7' } },
      },
      grid: { left: 42, right: 20, top: 24, bottom: 34 },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: trend.map((t) => t.date),
        axisLine: { lineStyle: { color: '#d2d2d7' } },
        axisLabel: { color: '#86868b', fontSize: 12 },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        minInterval: 1,
        axisLabel: { color: '#86868b', fontSize: 12 },
        splitLine: { lineStyle: { color: '#e8e8ed', type: 'dashed' } },
      },
      series: [
        {
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2.5, color: '#1d4ed8' },
          itemStyle: { color: '#1d4ed8', borderColor: '#fff', borderWidth: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(29,78,216,0.22)' },
              { offset: 1, color: 'rgba(29,78,216,0.01)' },
            ]),
          },
          data: trend.map((t) => t.count),
        },
      ],
    })
  }
}

const onResize = () => {
  intentInst?.resize()
  trendInst?.resize()
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  load()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  intentInst?.dispose()
  trendInst?.dispose()
})
</script>

<style scoped>
.kpi-row {
  margin-bottom: 16px;
}
.kpi-row :deep(.el-col) {
  margin-bottom: 16px;
}
.chart {
  height: 320px;
}
</style>
