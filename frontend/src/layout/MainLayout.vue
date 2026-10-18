<template>
  <div class="layout">
    <!-- 浅色分组侧栏 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">贸</div>
        <div class="brand-text">
          <div class="brand-name">国际贸易</div>
          <div class="brand-sub">智能服务平台</div>
        </div>
      </div>

      <nav class="nav-scroll">
        <div v-for="group in menuGroups" :key="group.label" class="nav-group">
          <div class="nav-group-label">{{ group.label }}</div>
          <RouterLink
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            active-class="is-active"
          >
            <el-icon :size="17"><component :is="item.icon" /></el-icon>
            <span class="nav-item-text">{{ item.title }}</span>
          </RouterLink>
        </div>
      </nav>

      <div class="sidebar-footer">
        <el-tag size="small" type="primary" effect="light" round>v2.0</el-tag>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="main-wrap">
      <header class="topbar">
        <div class="topbar-title">{{ currentTitle }}</div>
        <div class="topbar-right">
          <TaskCenter />
          <el-divider direction="vertical" />
          <el-dropdown @command="onCommand">
            <span class="user-chip">
              <div class="user-avatar">{{ (auth.me?.sub || 'U').charAt(0).toUpperCase() }}</div>
              <span class="user-name">{{ auth.me?.sub }}</span>
              <span v-if="auth.roleLabel" class="user-role">{{ auth.roleLabel }}</span>
              <el-icon :size="12"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import TaskCenter from '../components/TaskCenter.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const menuGroups = [
  {
    label: '概览',
    items: [{ path: '/dashboard', title: '工作台', icon: 'HomeFilled' }],
  },
  {
    label: 'AI 工作台',
    items: [
      { path: '/chat', title: '智能客服', icon: 'ChatDotRound' },
      { path: '/copywriting', title: '智能文案', icon: 'EditPen' },
      { path: '/translation', title: '翻译引擎', icon: 'Switch' },
    ],
  },
  {
    label: '电商运营',
    items: [
      { path: '/amazon', title: '亚马逊对接', icon: 'ShoppingCart' },
      { path: '/products', title: '商品管理', icon: 'Goods' },
      { path: '/crm', title: '客户管理', icon: 'User' },
      { path: '/opportunities', title: '商机管理', icon: 'Aim' },
    ],
  },
  {
    label: '知识与数据',
    items: [
      { path: '/knowledge', title: '知识库管理', icon: 'Collection' },
      { path: '/analytics', title: '数据洞察', icon: 'DataAnalysis' },
    ],
  },
  {
    label: '系统',
    items: [{ path: '/admin', title: '管理后台', icon: 'Setting' }],
  },
]

const currentTitle = computed(() => route.meta?.title || '')

const onCommand = (cmd) => {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  background: var(--bg-page);
}

/* ---------- 侧栏 ---------- */
.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--bg-card);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 18px 14px;
}
.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: var(--color-primary);
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-name {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}
.brand-sub {
  font-size: 11px;
  color: var(--text-tertiary);
}
.nav-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 4px 12px 12px;
}
.nav-group {
  margin-top: 14px;
}
.nav-group-label {
  padding: 0 12px 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.06em;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 12px;
  margin-bottom: 2px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  text-decoration: none;
  transition: background 0.15s ease, color 0.15s ease;
}
.nav-item:hover {
  background: var(--bg-subtle);
  color: var(--text-primary);
}
.nav-item.is-active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 600;
}
.sidebar-footer {
  padding: 12px 18px 16px;
}

/* ---------- 主区域 ---------- */
.main-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  height: var(--header-height);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: saturate(160%) blur(12px);
  -webkit-backdrop-filter: saturate(160%) blur(12px);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 10;
}
.topbar-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--text-primary);
}
.topbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.user-chip {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 8px;
  border-radius: var(--radius-pill);
  cursor: pointer;
  outline: none;
  color: var(--text-primary);
}
.user-chip:hover {
  background: var(--bg-subtle);
}
.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}
.user-name {
  font-size: var(--font-size-sm);
  font-weight: 500;
}
.user-role {
  font-size: 11px;
  color: var(--text-tertiary);
}
.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}
</style>
