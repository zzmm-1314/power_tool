<template>
    <div v-if="taskId" class="task-monitor">
        <div class="monitor-header">
            <span class="title">
                {{ statusText }}
                <span class="task-id">（{{ taskId.slice(0, 8) }}…）</span>
            </span>
            <div class="actions">
                <button v-if="task?.finished" class="btn-close" @click="$emit('close')">
                    关闭
                </button>
            </div>
        </div>

        <div class="progress-wrap">
            <div class="progress-bar">
                <div class="progress-fill"
                    :class="{ done: task?.status === 'completed', err: task?.status === 'error' }"
                    :style="{ width: `${task?.progress.percent || 0}%` }"></div>
            </div>
            <span class="progress-text">
                {{ task?.progress.percent || 0 }}%
                （{{ task?.progress.current || 0 }}/{{ task?.progress.total || 0 }}）
            </span>
        </div>

        <div ref="logRef" class="log-panel scroll-y">
            <div v-for="(line, i) in task?.logs || []" :key="i" class="log-line"
                :class="{ err: line.includes('错误') || line.includes('失败'), ok: line.includes('完成') || line.includes('✅') }">
                {{ line }}
            </div>
            <div v-if="!task?.logs?.length" class="log-empty">等待日志输出...</div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { fetchTaskStatus, type TaskInfo } from '@/api/modules/settlement'

const props = defineProps<{ taskId: string | null }>()
const emit = defineEmits<{
    (e: 'finished', task: TaskInfo): void
    (e: 'close'): void
}>()

const task = ref<TaskInfo | null>(null)
const logRef = ref<HTMLDivElement | null>(null)
let timer: number | undefined

const statusText = computed(() => {
    const s = task.value?.status
    if (s === 'completed') return '✅ 已完成'
    if (s === 'error') return '❌ 发生错误'
    return '⏳ 运行中'
})

async function poll() {
    if (!props.taskId) return
    try {
        const data = await fetchTaskStatus(props.taskId)
        task.value = data
        scrollToBottom()
        if (data.finished) {
            clearInterval(timer)
            emit('finished', data)
        }
    } catch (e) {
        console.warn('[TaskMonitor] 获取状态失败', e)
    }
}

function scrollToBottom() {
    const el = logRef.value
    if (el) {
        // 下一帧滚动到底部
        requestAnimationFrame(() => {
            el.scrollTop = el.scrollHeight
        })
    }
}

watch(
    () => props.taskId,
    (newId) => {
        clearInterval(timer)
        task.value = null
        if (!newId) return
        poll()
        timer = window.setInterval(poll, 1000)
    },
    { immediate: true },
)

onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.task-monitor {
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.monitor-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.title {
    font-size: 14px;
    font-weight: 600;
    color: #1f2d3d;
}

.task-id {
    font-size: 12px;
    color: #909399;
    font-weight: 400;
}

.btn-close {
    height: 26px;
    padding: 0 12px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    background: #fff;
    color: #606266;
    font-size: 12px;
    cursor: pointer;
}

.btn-close:hover {
    background: #f5f7fa;
}

.progress-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
}

.progress-bar {
    flex: 1;
    height: 10px;
    background: #f0f2f5;
    border-radius: 5px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: #2d6cdf;
    transition: width 0.3s;
}

.progress-fill.done {
    background: #67c23a;
}

.progress-fill.err {
    background: #f56c6c;
}

.progress-text {
    font-size: 12px;
    color: #606266;
    min-width: 100px;
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.log-panel {
    max-height: 280px;
    min-height: 120px;
    padding: 8px 10px;
    background: #1e1e1e;
    color: #d4d4d4;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    line-height: 1.6;
}

.log-line.err {
    color: #f56c6c;
}

.log-line.ok {
    color: #67c23a;
}

.log-empty {
    color: #909399;
    font-style: italic;
}
</style>