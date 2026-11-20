<template>
    <PageContainer :title="config.title">
        <div class="form-card">
            <AnnualConfigNotice />

            <div class="form-row">
                <label>电厂节点</label>
                <SearchableSelect v-model="selectedNode" :options="nodes"
                    :style="{ width: config.nodeWidth || '250px' }" />
            </div>

            <div class="form-row">
                <label>目标文件</label>
                <PathInput v-model="form.target_file" type="file" placeholder="模拟结算单模板 .xlsx" />
            </div>

            <!-- ⭐ 申报电量：与目标文件一致，选路径即可 -->
            <div v-if="config.showDeclaration" class="form-row">
                <label>申报电量文件</label>
                <PathInput v-model="form.declaration_file" type="file" placeholder="48点申报电量 .xlsx（可留空，留空则全部按 0 处理）" />
                <button type="button" class="btn-download-decl" @click="downloadDeclarationTemplate">
                    📥 下载模板
                </button>
            </div>

            <div class="form-row">
                <label>合约电量</label>
                <div class="field-box">
                    <div class="field-hint">
                        勾选的项目按输入电量调用合约分解，未勾选的取数据库已录入电量
                    </div>
                    <div class="switch-grid">
                        <div v-for="part in contractParts" :key="part.key"
                            :class="['switch-card', { 'is-on': contractSwitch[part.key] }]">
                            <label class="switch-head">
                                <span class="toggle">
                                    <input v-model="contractSwitch[part.key]" type="checkbox" />
                                    <span class="toggle-track"><span class="toggle-thumb" /></span>
                                </span>
                                <span class="switch-title">{{ part.label }}</span>
                            </label>
                            <input v-model.number="form[part.qtyField]" type="number" class="input qty-input"
                                :disabled="!contractSwitch[part.key]"
                                :placeholder="contractSwitch[part.key] ? '分解用量' : '取数据库'" />
                        </div>
                    </div>
                </div>
            </div>

            <div class="form-row">
                <label>合约电价</label>
                <div class="tenday-row" style="flex-wrap: wrap; gap: 10px;">
                    <div class="tenday-item">
                        <span class="tenday-label">年度</span>
                        <input v-model.number="form.annual_price" type="number" class="input small" step="0.0001" />
                    </div>
                    <div v-if="config.showMonthlyPrice" class="tenday-item">
                        <span class="tenday-label">月度</span>
                        <input v-model.number="form.monthly_price" type="number" class="input small" step="0.0001" />
                    </div>
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
                <label>滚撮数据</label>
                <div class="switch-grid">
                    <label :class="['switch-card', 'switch-card--flat', { 'is-on': form.enableRollingSpot }]">
                        <span class="toggle">
                            <input v-model="form.enableRollingSpot" type="checkbox" />
                            <span class="toggle-track"><span class="toggle-thumb" /></span>
                        </span>
                        <span class="switch-body">
                            <span class="switch-title">省内滚撮</span>
                            <span class="switch-desc">Z2 电量 / Z3 电费</span>
                        </span>
                    </label>
                    <label :class="['switch-card', 'switch-card--flat', { 'is-on': form.enableCrossProvince }]">
                        <span class="toggle">
                            <input v-model="form.enableCrossProvince" type="checkbox" />
                            <span class="toggle-track"><span class="toggle-thumb" /></span>
                        </span>
                        <span class="switch-body">
                            <span class="switch-title">省间滚撮</span>
                            <span class="switch-desc">AA2 电量 / AA3 电费</span>
                        </span>
                    </label>
                </div>
            </div>

            <div class="form-row">
                <label>日期范围</label>
                <DateRangeInput :start="form.dateStart" :end="form.dateEnd" @update:start="form.dateStart = $event"
                    @update:end="form.dateEnd = $event" />
            </div>

            <div class="form-actions">
                <button class="btn primary" :disabled="starting" @click="submit">
                    {{ starting ? '启动中...' : '▶ 开始生成' }}
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
import SearchableSelect from '@/components/SearchableSelect.vue'
import TaskMonitor from '@/components/TaskMonitor.vue'
import AnnualConfigNotice from '@/components/AnnualConfigNotice.vue'
import { listPlantNodes, fetchGlobalNode } from '@/api/modules/nodes'
import { expandDateRange } from '@/utils/dateRange'
import { startSettlementTask, type TaskInfo } from '@/api/modules/settlement'
import type { SettlementSimConfig } from './settlement-sim-types'
import { useRouter } from 'vue-router'
import { request } from '@/api/request'
import { apiUrl } from '@/utils/apiBase'

const props = defineProps<{ config: SettlementSimConfig }>()

const nodes = ref<string[]>([])
const selectedNode = ref('')
const starting = ref(false)
const taskId = ref<string | null>(null)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')
const router = useRouter()
const hasCurve = ref(true)

/** 合约电量五个部分：勾选=调用合约分解，未勾选=取数据库 */
const contractParts = [
    { key: 'year', label: '年度', qtyField: 'qty_year' },
    { key: 'month', label: '月度', qtyField: 'qty_month' },
    { key: 'tenday1', label: '上旬', qtyField: 'qty_tenday1' },
    { key: 'tenday2', label: '中旬', qtyField: 'qty_tenday2' },
    { key: 'tenday3', label: '下旬', qtyField: 'qty_tenday3' },
] as const

const contractSwitch = reactive<Record<string, boolean>>({
    year: false,
    month: false,
    tenday1: false,
    tenday2: false,
    tenday3: false,
})

const form = reactive({
    target_file: '',
    declaration_file: '',   // ⭐ 新增：申报电量 Excel 路径
    annual_price: 0,
    monthly_price: 0,
    tenday_early: 0,
    tenday_mid: 0,
    tenday_late: 0,
    qty_year: 0,
    qty_month: 0,
    qty_tenday1: 0,
    qty_tenday2: 0,
    qty_tenday3: 0,
    enableRollingSpot: false,
    enableCrossProvince: false,
    dateStart: '',
    dateEnd: '',
})

onMounted(async () => {
    checkConfigStatus()
    try {
        const list = await listPlantNodes()
        nodes.value = list.map(n => n.name)
        // ⭐ 默认选中全局节点
        if (!selectedNode.value) {
            try {
                const globalNode = await fetchGlobalNode()
                if (globalNode && nodes.value.includes(globalNode)) {
                    selectedNode.value = globalNode
                }
            } catch {
                // ignore
            }
        }
    } catch {
        nodes.value = []
    }
})

async function checkConfigStatus() {
    try {
        const res = await request<{ has_curve: boolean, has_holiday: boolean }>({
            url: '/contract/config/status',
            method: 'get'
        })
        hasCurve.value = res.has_curve
    } catch (e) {
        console.warn('检查基础配置状态失败', e)
    }
}

function downloadDeclarationTemplate() {
    window.open(apiUrl('/settlement/declaration-template'), '_blank')
}

async function submit() {
    msg.value = ''
    // 只有勾选了至少一项合约电量才需要典型曲线
    const needDecompose = Object.values(contractSwitch).some(Boolean)
    if (needDecompose && !hasCurve.value) {
        if (confirm('已勾选按输入电量分解，但数据库中缺失「典型曲线」，无法完成分解。是否现在去配置？')) {
            router.push('/contract/config')
        }
        return
    }
    if (!selectedNode.value) {
        msg.value = '请先选择电厂节点'
        msgType.value = 'err'
        return
    }
    if (!form.target_file) {
        msg.value = '请填写目标文件'
        msgType.value = 'err'
        return
    }
    if (!form.dateStart || !form.dateEnd) {
        msg.value = '请先选择日期范围'
        msgType.value = 'err'
        return
    }

    starting.value = true
    try {
        const contract_sources: Record<string, string> = {}
        for (const part of contractParts) {
            contract_sources[part.key] = contractSwitch[part.key] ? 'decompose' : 'database'
        }

        const payload: Record<string, any> = {
            node_name: selectedNode.value,
            start_date: form.dateStart,
            end_date: form.dateEnd,
            target_file: form.target_file,
            declaration_file: form.declaration_file,   // ⭐ 新增
            contract_sources,
            annual_price: form.annual_price,
            monthly_price: form.monthly_price,
            tenday_early: form.tenday_early,
            tenday_mid: form.tenday_mid,
            tenday_late: form.tenday_late,
            qty_year: form.qty_year,
            qty_month: form.qty_month,
            qty_tenday1: form.qty_tenday1,
            qty_tenday2: form.qty_tenday2,
            qty_tenday3: form.qty_tenday3,
            enable_rolling_spot: form.enableRollingSpot,
            enable_cross_province: form.enableCrossProvince,
            selected_dates: expandDateRange(form.dateStart, form.dateEnd),
        }

        const res = await startSettlementTask('simulate', payload)
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
    msg.value = task.status === 'completed' ? '✅ 完成' : '❌ 失败，请查看日志'
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
    margin-bottom: 12px;
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
.form-row> :deep(.date-multi),
.form-row>.input,
.form-row>.tenday-row,
.form-row>.field-box,
.form-row>.switch-grid {
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
    transition: border-color 0.2s, background 0.2s;
}

.input:focus {
    border-color: #2d6cdf;
}

.input:disabled {
    background: #f5f7fa;
    color: #a8abb2;
    cursor: not-allowed;
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

/* ===== 合约电量：开关 + 输入框 ===== */
.field-box {
    padding: 10px 12px 12px;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    background: #fafbfc;
}

.field-hint {
    font-size: 12px;
    color: #909399;
    margin-bottom: 10px;
}

.switch-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.switch-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 132px;
    padding: 10px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    background: #fff;
    transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.switch-card.is-on {
    border-color: #2d6cdf;
    background: #f4f8ff;
    box-shadow: 0 0 0 2px rgba(45, 108, 223, 0.08);
}

.switch-card--flat {
    flex-direction: row;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    cursor: pointer;
    min-width: 172px;
}

.switch-head {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
}

.switch-title {
    font-size: 13px;
    font-weight: 500;
    color: #303133;
}

.switch-card.is-on .switch-title {
    color: #2d6cdf;
}

.switch-body {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.switch-desc {
    font-size: 11px;
    color: #909399;
}

.qty-input {
    width: 100%;
    height: 30px;
}

/* ===== 开关（toggle）外观 ===== */
.toggle {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
    cursor: pointer;
}

.toggle input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
}

.toggle-track {
    position: relative;
    display: inline-block;
    width: 34px;
    height: 18px;
    border-radius: 9px;
    background: #dcdfe6;
    transition: background 0.2s ease;
}

.toggle-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
    transition: transform 0.2s ease;
}

.toggle input:checked+.toggle-track {
    background: #2d6cdf;
}

.toggle input:checked+.toggle-track .toggle-thumb {
    transform: translateX(16px);
}

.toggle input:focus-visible+.toggle-track {
    box-shadow: 0 0 0 3px rgba(45, 108, 223, 0.22);
}

.form-actions {
    display: flex;
    gap: 10px;
    padding-left: 122px;
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

.btn-download-decl {
    height: 32px;
    padding: 0 14px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    background: #fff;
    color: #606266;
    font-size: 13px;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.2s, border-color 0.2s, color 0.2s;
}

.btn-download-decl:hover {
    border-color: #2d6cdf;
    color: #2d6cdf;
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