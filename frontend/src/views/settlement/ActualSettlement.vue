<template>
    <PageContainer title="结算单更新 · 实际结算单更新">
        <div class="form-card">
            <div class="form-row">
                <label>明细文件夹</label>
                <PathInput v-model="form.folder" type="folder" placeholder="选择存放每日明细 Excel 的文件夹" />
            </div>
            <div class="form-row">
                <label>目标文件</label>
                <PathInput v-model="form.target_file" type="file" placeholder="待填充的结算单 .xlsx" />
            </div>
            <div class="form-row">
                <label>指定日期（可选）</label>
                <DateRangeInput :start="form.dateStart" :end="form.dateEnd" @update:start="form.dateStart = $event"
                    @update:end="form.dateEnd = $event" />
            </div>

            <div class="form-actions">
                <button class="btn primary" :disabled="starting" @click="submit">
                    {{ starting ? '启动中...' : '▶ 开始更新' }}
                </button>
                <button class="btn ghost" :disabled="starting" @click="autoParse">
                    📂 自动识别
                </button>
            </div>

            <p v-if="msg" class="msg" :class="msgType">{{ msg }}</p>
        </div>

        <TaskMonitor v-if="taskId" :task-id="taskId" @finished="onFinished" @close="taskId = null" />
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import PathInput from '@/components/PathInput.vue'
import DateRangeInput from '@/components/DateRangeInput.vue'
import { expandDateRange } from '@/utils/dateRange'
import TaskMonitor from '@/components/TaskMonitor.vue'
import {
    startSettlementTask,
    parsePaths,
    type TaskInfo,
} from '@/api/modules/settlement'

const form = reactive({
    folder: '',
    target_file: '',
    dateStart: '',
    dateEnd: '',
})

const starting = ref(false)
const taskId = ref<string | null>(null)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')

async function autoParse() {
    msg.value = ''
    const paths = [form.folder, form.target_file].filter(Boolean)
    if (!paths.length) {
        msg.value = '请先选择文件夹或目标文件'
        msgType.value = 'err'
        return
    }
    try {
        const res = await parsePaths(paths)
        if (res.detail_folder) form.folder = res.detail_folder
        if (res.target_file) form.target_file = res.target_file
        msg.value = '已自动识别路径'
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message
        msgType.value = 'err'
    }
}

async function submit() {
    msg.value = ''
    if (!form.folder || !form.target_file) {
        msg.value = '请填写明细文件夹和目标文件'
        msgType.value = 'err'
        return
    }

    const selected_dates = expandDateRange(form.dateStart, form.dateEnd)

    starting.value = true
    try {
        const res = await startSettlementTask('actual', {
            folder: form.folder,
            target_file: form.target_file,
            selected_dates,
        })
        taskId.value = res.taskId
        msg.value = selected_dates.length
            ? `任务已启动（${selected_dates.length} 天）`
            : '任务已启动（全部日期）'
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message
        msgType.value = 'err'
    } finally {
        starting.value = false
    }
}

function onFinished(task: TaskInfo) {
    msg.value =
        task.status === 'completed'
            ? '✅ 更新完成'
            : '❌ 更新失败，请查看日志'
    msgType.value = task.status === 'completed' ? 'ok' : 'err'
}
</script>

<style scoped>
.form-card {
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    padding: 16px 20px;
}

.form-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 14px;
}

.form-row>label {
    width: 110px;
    flex-shrink: 0;
    padding-top: 8px;
    font-size: 13px;
    color: #606266;
    text-align: right;
}

.form-row> :deep(.path-input),
.form-row> :deep(.date-multi) {
    flex: 1;
    min-width: 0;
}

.form-actions {
    display: flex;
    gap: 10px;
    padding-left: 122px;
}

.btn {
    height: 34px;
    padding: 0 18px;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
}

.btn.primary {
    background: #2d6cdf;
    color: #fff;
}

.btn.primary:hover:not(:disabled) {
    background: #2459b8;
}

.btn:disabled {
    background: #a0b4d8;
    color: #fff;
    cursor: not-allowed;
}

.btn.ghost {
    background: #fff;
    color: #606266;
    border: 1px solid #dcdfe6;
}

.btn.ghost:hover:not(:disabled) {
    background: #f5f7fa;
}

.msg {
    margin: 12px 0 0 122px;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 12px;
    display: inline-block;
}

.msg.ok {
    background: #f0f9eb;
    color: #67c23a;
}

.msg.err {
    background: #fef0f0;
    color: #f56c6c;
}
</style>