<template>
  <el-card :body-style="{ padding: padding }" class="app-card" :shadow="shadow">
    <template v-if="title || $slots.title" #header>
      <slot name="title">
        <div class="app-card-title">
          <span v-if="icon" class="app-card-icon">{{ icon }}</span>
          <span>{{ title }}</span>
          <span v-if="extra" class="app-card-extra">{{ extra }}</span>
        </div>
      </slot>
    </template>
    <slot />
  </el-card>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  icon: { type: String, default: '' },
  extra: { type: String, default: '' },
  padding: { type: String, default: '20px' },
  shadow: { type: String, default: 'never' },
})
</script>

<style scoped>
.app-card {
  height: 100%;
}
.app-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
}
.app-card-icon {
  font-size: 18px;
}
.app-card-extra {
  margin-left: auto;
  font-size: var(--font-size-xs);
  font-weight: 400;
  color: var(--text-tertiary);
}
:deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid var(--divider);
}
</style>
