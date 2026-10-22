<template>
    <PageContainer title="结算单更新 · 现代模拟结算单更新">
        <div class="form-card">
            <div class="form-row">
                <label>节点</label>
                <select v-model="selectedNode" class="input" style="width: 220px">
                    <option value="">请选择节点</option>
                    <option v-for="n in nodes" :key="n" :value="n">{{ n }}</option>
                </select>
                <span class="hint">（"日前实时参考"将使用该节点的日前 + 实时数据）</span>
            </div>
            <div class="form-row">
                <label>日期范围</label>
                <DateRangeInput :start="form.dateStart" :end="form.dateEnd" @update:start="form.dateStart = $event"
                    @update:end="form.dateEnd = $event" />
            </div>
            <div class="form-row">
                <label>现货申报</label>
                <PathInput v-model="form.spot_file" type="file" placeholder="现货申报表 .xlsx（含日期工作表）" />
            </div>
            <div class="form-row">
                <label>数据统计</label>
                <PathInput v-model="form.stat_file" type="file" placeholder="含「中长期持仓详细」" />
            </div>
            <div class="form-row">
                <label>月度策略</label>
                <PathInput v-model="form.strategy_file" type="file" placeholder="含「年月分解表」「旬度分解表」" />
            </div>
            <div class="form-row">
                <label>日前实时参考</label>
                <div class="picker-wrap">
                    <PriceFilePicker v-model="form.info_spot_file" :start-date="form.dateStart" :end-date="form.dateEnd"
                        :kind-options="[{ value: 'plant-pair', label: '节点（日前 + 实时）' }]" default-kind="plant-pair"
                        :node-name="selectedNode" :hide-node-picker="true" @update:start-date="form.dateStart = $event"
                        @update:end-date="form.dateEnd = $event" />
                </div>
            </div>
            <div class="form-row">
                <label>合约参考</label>
                <div class="picker-wrap">
                    <PriceFilePicker v-model="form.info_contract_file" :start-date="form.dateStart"
                        :end-date="form.dateEnd" :kind-options="[{ value: 'unified', label: '日前统一结算点' }]"
                        default-kind="unified" @update:start-date="form.dateStart = $event"
                        @update:end-date="form.dateEnd = $event" />
                </div>
            </div>
            <div class="form-row">
                <label>目标文件</label>
                <PathInput v-model="form.target_file" type="file" placeholder="模拟结算单模板 .xlsx" />
            </div>

            <div class="form-row">
                <label>年度合约电价</label>
                <input v-model.number="form.annual_price" type="number" step="0.0001" class="input" />
            </div>
            <div class="form-row">
                <label>月度合约电价</label>
                <input v-model.number="form.monthly_price" type="number" step="0.0001" class="input" />
            </div>
            <div class="form-row">
                <label>旬度电价</label>
                <div class="tenday-row">
                    <div class="tenday-item">
                        <span class="tenday-label">上旬</span>
                        <input v-model.number="form.tenday_early" type="number" step="0.0001" class="input small" />
                    </div>
                    <div class="tenday-item">
                        <span class="tenday-label">中旬</span>
                        <input v-model.number="form.tenday_mid" type="number" step="0.0001" class="input small" />
                    </div>
                    <div class="tenday-item">
                        <span class="tenday-label">下旬</span>
                        <input v-model.number="form.tenday_late" type="number" step="0.0001" class="input small" />
                    </div>
                </div>
            </div>

            <div class="form-row">
                <label>指定日期（可选）</label>
                <DateRangeInput :start="form.dateStart" :end="form.dateEnd" @update:start="form.dateStart = $event"
                    @update:end="form.dateEnd = $event" />
            </div>

            <div class="form-actions">
                <button class="btn primary" :disabled="starting" @click="submit">
                    {{ starting ? '启动中...' : '▶ 开始生成' }}
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
import { ref, reactive, onMounted } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import PathInput from '@/components/PathInput.vue'
import DateRangeInput from '@/components/DateRangeInput.vue'
import PriceFilePicker from '@/components/PriceFilePicker.vue'
import { listPlantNodes } from '@/api/modules/nodes'
import { expandDateRange } from '@/utils/dateRange'
import TaskMonitor from '@/components/TaskMonitor.vue'
import {
    startSettlementTask,
    parsePaths,
    type TaskInfo,
} from '@/api/modules/settlement'
const selectedNode = ref('')
const nodes = ref<string[]>([])
const form = reactive({
    spot_file: '',
    stat_file: '',
    strategy_file: '',
    info_spot_file: '',
    info_contract_file: '',
    target_file: '',
    annual_price: 0,
    monthly_price: 0,
    tenday_early: 0,
    tenday_mid: 0,
    tenday_late: 0,
    dateStart: '',
    dateEnd: '',
})

const starting = ref(false)
const taskId = ref<string | null>(null)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')

const labelMap: Record<string, string> = {
    spot_file: '现货申报',
    stat_file: '数据统计',
    strategy_file: '月度策略',
    info_spot_file: '日前实时参考',
    info_contract_file: '合约参考',
    target_file: '目标文件',
}
async function loadNodes() {
    try {
        const list = await listPlantNodes()
        nodes.value = list.map((n) => n.name)
    } catch {
        nodes.value = []
    }
}

async function autoParse() {
    msg.value = ''
    const paths = [
        form.spot_file,
        form.stat_file,
        form.strategy_file,
        form.target_file,
    ].filter(Boolean)
    if (!paths.length) {
        msg.value = '请先选择部分文件'
        msgType.value = 'err'
        return
    }
    try {
        const res = await parsePaths(paths)
        if (res.spot_file) form.spot_file = res.spot_file
        if (res.stat_file) form.stat_file = res.stat_file
        if (res.strategy_file) form.strategy_file = res.strategy_file
        if (res.target_file) form.target_file = res.target_file
        // ⚠ 不覆盖 info_spot_file / info_contract_file
        msg.value = '已自动识别路径（日前实时/合约参考需手动生成）'
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message
        msgType.value = 'err'
    }
}

async function submit() {
    msg.value = ''
    if (!selectedNode.value) {
        msg.value = '请先选择节点'
        msgType.value = 'err'
        return
    }
    if (!form.dateStart || !form.dateEnd) {
        msg.value = '请先选择日期范围'
        msgType.value = 'err'
        return
    }

    const required: (keyof typeof form)[] = [
        'spot_file', 'stat_file', 'strategy_file',
        'info_spot_file', 'info_contract_file', 'target_file',
    ]
    for (const k of required) {
        if (!form[k]) {
            msg.value = `请填写「${labelMap[k as string] || k}」`
            msgType.value = 'err'
            return
        }
    }

    starting.value = true
    try {
        const res = await startSettlementTask('xiandai', {
            spot_file: form.spot_file,
            stat_file: form.stat_file,
            strategy_file: form.strategy_file,
            info_spot_file: form.info_spot_file,
            info_contract_file: form.info_contract_file,
            target_file: form.target_file,
            annual_price: form.annual_price,
            monthly_price: form.monthly_price,
            tenday_early: form.tenday_early,
            tenday_mid: form.tenday_mid,
            tenday_late: form.tenday_late,
            selected_dates: expandDateRange(form.dateStart, form.dateEnd),
        })
        taskId.value = res.taskId
        msg.value = '任务已启动'
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
        task.status === 'completed' ? '✅ 完成' : '❌ 失败，请查看日志'
    msgType.value = task.status === 'completed' ? 'ok' : 'err'
}
onMounted(loadNodes)
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
    margin-bottom: 12px;
}

.form-row>label {
    width: 130px;
    flex-shrink: 0;
    padding-top: 8px;
    font-size: 13px;
    color: #606266;
    text-align: right;
}

.form-row> :deep(.path-input),
.form-row> :deep(.date-multi),
.form-row>.input,
.form-row>.tenday-row {
    flex: 1;
    min-width: 0;
}

.input {
    height: 32px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
    width: 180px;
}

.input:focus {
    border-color: #2d6cdf;
}

.input.small {
    width: 120px;
}

.tenday-row {
    display: flex;
    gap: 16px;
    padding-top: 2px;
}

.tenday-item {
    display: flex;
    align-items: center;
    gap: 6px;
}

.tenday-label {
    font-size: 12px;
    color: #606266;
}

.form-actions {
    display: flex;
    gap: 10px;
    padding-left: 142px;
    margin-top: 8px;
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
    margin: 12px 0 0 142px;
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

.hint {
    font-size: 12px;
    color: #909399;
}

.picker-wrap {
    flex: 1;
    min-width: 0;
    padding: 8px 12px;
    background: #fafbfc;
    border-radius: 4px;
    border: 1px solid #f0f2f5;
}
</style>