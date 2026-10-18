<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-head">
        <span class="logo-mark">贸</span>
        <h2>国际贸易智能平台</h2>
        <p class="sub">登录以继续使用</p>
      </div>
      <el-form :model="form" label-position="top" @keyup.enter="submit">
        <el-form-item label="用户名">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            autofocus
            size="large"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
            size="large"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="loading" @click="submit">
          登 录
        </el-button>
      </el-form>
      <p class="tip">演示模式可直接浏览；默认管理员 admin / admin123</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { TOKEN_KEY } from '../api'

const router = useRouter()
const form = reactive({ username: '', password: '' })
const loading = ref(false)

const submit = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await api.post('/auth/login', { username: form.username, password: form.password })
    localStorage.setItem(TOKEN_KEY, res.access_token)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch {
    // 错误提示由 axios 拦截器统一弹出
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page);
  padding: 20px;
}
.login-card {
  width: 400px;
  background: var(--bg-card);
  border: 1px solid var(--divider);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 40px 36px 32px;
}
.login-head {
  text-align: center;
  margin-bottom: 26px;
}
.logo-mark {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: var(--color-primary);
  color: #fff;
  font-size: 24px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.login-head h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}
.login-head .sub {
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}
.submit {
  width: 100%;
  margin-top: 6px;
  font-weight: 600;
}
.tip {
  margin: 18px 0 0;
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
}
</style>
