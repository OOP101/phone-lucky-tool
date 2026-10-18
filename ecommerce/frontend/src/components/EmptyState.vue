<template>
  <div class="empty-state">
    <div class="empty-icon">
      <slot name="icon">
        <el-icon :size="30" color="#c7c7cc"><Box /></el-icon>
      </slot>
    </div>
    <div class="empty-text">{{ text }}</div>
    <div v-if="hint" class="empty-hint">{{ hint }}</div>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: '暂无数据' },
  hint: { type: String, default: '' },
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  color: var(--text-tertiary);
}
.empty-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  background: var(--bg-subtle);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}
.empty-text {
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  font-weight: 500;
}
.empty-hint {
  margin-top: 6px;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}
.empty-action {
  margin-top: 16px;
}
</style>
