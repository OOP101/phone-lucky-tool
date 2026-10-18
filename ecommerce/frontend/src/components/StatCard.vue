<template>
  <div class="stat-card" :class="tone">
    <div class="stat-main">
      <div class="stat-label">{{ label }}</div>
      <div class="stat-value">
        <span v-if="loading" class="loading-dots"><span></span><span></span><span></span></span>
        <template v-else>{{ formattedValue }}</template>
      </div>
      <div v-if="sub || $slots.sub" class="stat-sub">
        <slot name="sub">{{ sub }}</slot>
      </div>
    </div>
    <div v-if="icon || $slots.icon" class="stat-icon">
      <slot name="icon">
        <el-icon :size="22"><component :is="icon" /></el-icon>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: 0 },
  sub: { type: String, default: '' },
  icon: { type: [String, Object], default: '' },
  tone: { type: String, default: 'primary' }, // primary / cyan / success / warning / danger / neutral
  loading: { type: Boolean, default: false },
  prefix: { type: String, default: '' },
})

const formattedValue = computed(() => {
  const v = props.value
  if (typeof v === 'number') {
    return props.prefix + v.toLocaleString('zh-CN')
  }
  return props.prefix + (v ?? '–')
})
</script>

<style scoped>
.stat-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: var(--shadow-xs);
  border: 1px solid var(--border-color);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.stat-label {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  font-weight: 500;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
  letter-spacing: -0.02em;
  min-height: 31px;
}
.stat-sub {
  margin-top: 6px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-left: 12px;
}
.stat-card.primary .stat-icon { background: var(--color-primary-soft); color: var(--color-primary); }
.stat-card.cyan .stat-icon { background: var(--color-cyan-soft); color: var(--color-cyan); }
.stat-card.success .stat-icon { background: var(--color-success-soft); color: var(--color-success); }
.stat-card.warning .stat-icon { background: var(--color-warning-soft); color: var(--color-warning); }
.stat-card.danger .stat-icon { background: var(--color-danger-soft); color: var(--color-danger); }
.stat-card.neutral .stat-icon { background: var(--color-info-soft); color: var(--color-info); }
</style>
