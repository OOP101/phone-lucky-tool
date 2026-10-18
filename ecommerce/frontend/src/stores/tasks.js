import { defineStore } from 'pinia'

let seq = 0
const nextId = () => `task_${Date.now()}_${++seq}`

/**
 * 全局 AI 任务中心
 *
 * 所有 AI 长任务（文案写作、订单分析、客服生成等）都注册到这里执行。
 * 任务状态挂在 Pinia 单例上，与具体页面组件生命周期解耦：
 * 切换路由 / 页面组件卸载都不会中断进行中的请求，结果随时可取。
 */
export const useTaskStore = defineStore('tasks', {
  state: () => ({
    // { id, type, title, status, result(文本), data(结构化结果), sections(流式段落进度), error, createdAt, finishedAt }
    tasks: [],
  }),

  getters: {
    running: (s) => s.tasks.filter((t) => t.status === 'running'),
    runningCount() {
      return this.running.length
    },
    /** 顶栏铃铛：有进行中或最近完成（30 分钟内）的任务 */
    hasActivity() {
      return this.runningCount > 0
    },
    recent: (s) =>
      [...s.tasks]
        .sort((a, b) => b.createdAt - a.createdAt)
        .slice(0, 20),
  },

  actions: {
    /**
     * 包裹一个异步 AI 任务，自动维护状态。
     * @param {{type: string, title: string}} meta
     * @param {(id: string) => Promise<any>} fn 业务函数，返回结果（字符串或对象）
     * @param {(id: string) => void} [onStart] 任务创建后立即回调（用于绑定 loading）
     * @returns {Promise<string>} 任务 id（调用方可选订阅）
     */
    async run(meta, fn, onStart) {
      const id = nextId()
      this.tasks.unshift({
        id,
        type: meta.type || 'ai',
        title: meta.title || 'AI 任务',
        status: 'running',
        result: '',
        data: null,
        sections: null, // 流式任务：[{key,label,text,done,error}]，与组件生命周期解耦
        error: '',
        createdAt: Date.now(),
        finishedAt: 0,
      })
      onStart?.(id)
      try {
        const result = await fn(id)
        this.succeed(id, result)
      } catch (e) {
        this.fail(id, e?.response?.data?.detail || e?.message || '任务失败')
      }
      return id
    },

    succeed(id, result) {
      const t = this.tasks.find((x) => x.id === id)
      if (!t) return
      t.status = 'done'
      // data 保留结构化原始结果，供发起页面回显富内容
      if (result && typeof result === 'object') t.data = result
      t.result =
        typeof result === 'string'
          ? result
          : result?.result || result?.analysis || result?.copy || JSON.stringify(result)
      t.finishedAt = Date.now()
    },

    fail(id, error) {
      const t = this.tasks.find((x) => x.id === id)
      if (!t) return
      t.status = 'error'
      t.error = error
      t.finishedAt = Date.now()
    },

    /** 取某页面相关的最近任务（用于页面内结果回显） */
    latestOfType(type) {
      return this.tasks.find((t) => t.type === type) || null
    },

    remove(id) {
      this.tasks = this.tasks.filter((t) => t.id !== id)
    },

    clearFinished() {
      this.tasks = this.tasks.filter((t) => t.status === 'running')
    },
  },
})
