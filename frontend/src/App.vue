<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <!-- 仅缓存明确声明的页面（如客服会话），其余页面切换即释放，
           AI 长任务的连续性由全局任务中心（Pinia）保障 -->
      <keep-alive :include="cachedViews">
        <component :is="Component" />
      </keep-alive>
    </transition>
  </router-view>
</template>

<script setup>
// 与页面 defineOptions({ name }) 对应
const cachedViews = ['Chat']
</script>
