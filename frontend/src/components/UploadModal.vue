<template>
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="visible" class="upload-mask" @click.self="close">
                <div class="upload-modal">
                    <button class="close-btn" @click="close">×</button>

                    <div class="modal-header">
                        <h2 class="modal-title">📤 上传 Excel</h2>
                        <p class="modal-subtitle">
                            选择数据类型后批量上传，系统自动识别日期
                        </p>
                    </div>

                    <div class="modal-body">
                        <div class="form-item">
                            <label>数据类型</label>
                            <select v-model="datasetKey" class="select">
                                <option v-for="opt in DATASETS" :key="opt.key" :value="opt.key">
                                    {{ opt.label }}
                                </option>
                            </select>
                        </div>

                        <div v-if="currentDataset.needNode" class="form-item">
                            <label>电厂节点名称</label>
                            <div v-if="currentDataset.needNode" class="form-item">
                                <label>选择节点</label>
                                <select v-model="nodeName" class="select">
                                    <option value="">请选择节点</option>
                                    <option v-for="n in nodeOptions" :key="n.id" :value="n.name">
                                        {{ n.name }}
                                    </option>
                                </select>
                                <p v-if="!nodeOptions.length" class="hint">
                                    暂无节点，请先在「节点编辑」页面添加
                                </p>
                            </div>
                        </div>

                        <div class="form-item">
                            <label>选择文件（可多选）</label>
                            <input ref="fileInputRef" type="file" accept=".xlsx,.xls" multiple class="file-input"
                                @change="onFilesChange" />
                        </div>

                        <p v-if="selectedFiles.length" class="selected-tip">
                            已选 {{ selectedFiles.length }} 个文件：
                            {{selectedFiles.map((f) => f.name).join('、')}}
                        </p>

                        <p v-if="msg" class="msg" :class="msgType">{{ msg }}</p>
                        <!-- ===== 上传进度 ===== -->
                        <div v-if="uploading || uploadingItems.length" class="progress-wrap">
                            <!-- 整体进度条 -->
                            <div class="overall-progress">
                                <div class="overall-bar-wrap">
                                    <div class="overall-bar-fill" :style="{ width: overallPercent + '%' }" />
                                </div>
                                <span class="overall-text">
                                    {{ overallPercent }}%（{{ doneCount }}/{{ uploadingItems.length }}）
                                </span>
                            </div>

                            <!-- 每个文件的进度 -->
                            <ul class="queue-list">
                                <li v-for="(it, i) in uploadingItems" :key="i" class="queue-item" :class="it.status">
                                    <span class="queue-icon">{{ statusIcon(it.status) }}</span>
                                    <span class="queue-name" :title="it.name">{{ it.name }}</span>
                                    <div class="queue-bar-wrap">
                                        <div class="queue-bar-fill" :style="{ width: it.percent + '%' }" />
                                    </div>
                                    <span class="queue-percent">{{ it.percent }}%</span>
                                    <span class="queue-size">{{ formatSize(it.total) }}</span>
                                </li>
                            </ul>
                        </div>
                        <ul v-if="uploadResults.length" class="result-list">
                            <li v-for="(r, i) in uploadResults" :key="i" :class="['result-item', r.ok ? 'ok' : 'err']">
                                <span class="result-icon">{{ r.ok ? '✓' : '✗' }}</span>
                                <span class="result-name">{{ r.name }}</span>
                                <span class="result-extra">
                                    <template v-if="r.ok && r.dates?.length && !r.nodes">
                                        日期：{{ r.dates.join('、') }}
                                    </template>

                                    <template v-else-if="r.ok && r.nodes?.length">
                                        写入 {{ r.nodes.length }} 个节点：
                                        <span class="node-list">{{ r.nodes.join('、') }}</span>
                                        <template v-if="r.ignoredNodes?.length">
                                            <br />
                                            <span class="ignored-tip">
                                                （已忽略 {{ r.ignoredNodes.length }} 个未录入节点，
                                                如需处理请到「节点编辑」添加）
                                            </span>
                                        </template>
                                    </template>

                                    <template v-else-if="r.error">（{{ r.error }}）</template>
                                </span>
                            </li>
                        </ul>
                    </div>

                    <div class="modal-footer">
                        <button class="btn ghost" @click="close" :disabled="uploading">
                            取消
                        </button>
                        <button class="btn" :disabled="!canSubmit || uploading" @click="submit">
                            {{ uploading ? '上传中...' : `上传 ${selectedFiles.length || ''} 个文件` }}
                        </button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import {
    uploadTempData,
    uploadSingleTempFile,
    type UploadItemResult,
} from '@/api/modules/tempData'
import { listPlantNodes, type PlantNode } from '@/api/modules/nodes'
interface DatasetOption {
    key: string
    label: string
    dataType: string
    subType?: string
    needNode?: boolean
}

const DATASETS: DatasetOption[] = [
    { key: 'load', label: '负荷分析（浙江电网）', dataType: 'load' },
    { key: 'pv', label: '光伏出力（浙江电网）', dataType: 'pv' },
    {
        key: 'day-ahead-unified',
        label: '日前电价 · 统一结算点',
        dataType: 'day-ahead',
        subType: 'unified',
    },
    {
        key: 'day-ahead-plant',
        label: '日前电价 · 电厂节点',
        dataType: 'day-ahead',
        subType: 'plant',
        // needNode: true,          // ← 恢复 needNode
    },
    {
        key: 'spread-unified',
        label: '价差分析 · 实时价格数据',
        dataType: 'spread',
        subType: 'unified',
    },
    {
        key: 'spread-plant',
        label: '价差分析 · 电厂节点实时价格',
        dataType: 'spread',
        subType: 'plant',
        // needNode 移除 —— 自动识别文件中所有节点，只写入已录入节点
    },
]

const appStore = useAppStore()

const visible = computed(() => appStore.uploadVisible)

const datasetKey = ref<string>('load')
const nodeName = ref('')
const selectedFiles = ref<File[]>([])
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')
const uploadResults = ref<UploadItemResult[]>([])
interface UploadingItem {
    file: File
    name: string
    loaded: number
    total: number
    percent: number
    status: 'pending' | 'uploading' | 'ok' | 'error'
    result?: UploadItemResult
    error?: string
}
const uploadingItems = ref<UploadingItem[]>([])
/** 整体进度 = (已结束文件数 + 当前文件百分比) / 总文件数 */
const overallPercent = computed(() => {
    const items = uploadingItems.value
    if (!items.length) return 0
    let done = 0
    let cur = 0
    for (const it of items) {
        if (it.status === 'ok' || it.status === 'error') {
            done += 1
        } else if (it.status === 'uploading') {
            cur = it.percent / 100
        }
    }
    return Math.round(((done + cur) / items.length) * 100)
})
const doneCount = computed(
    () =>
        uploadingItems.value.filter(
            (it) => it.status === 'ok' || it.status === 'error',
        ).length,
)
const currentDataset = computed<DatasetOption>(
    () => DATASETS.find((d) => d.key === datasetKey.value) ?? DATASETS[0],
)

const canSubmit = computed(() => {
    if (!selectedFiles.value.length) return false
    if (currentDataset.value.needNode && !nodeName.value) return false
    return true
})
// 新增：从节点列表加载
const nodeOptions = ref<PlantNode[]>([])

async function loadNodes() {
    try {
        nodeOptions.value = await listPlantNodes()
    } catch {
        nodeOptions.value = []
    }
}
function statusIcon(s: UploadingItem['status']): string {
    if (s === 'ok') return '✓'
    if (s === 'error') return '✗'
    if (s === 'uploading') return '…'
    return '·'
}
function formatSize(bytes: number): string {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}
function close() {
    if (uploading.value) return      // 上传中不能关
    appStore.closeUpload()
    setTimeout(() => {
        selectedFiles.value = []
        uploadingItems.value = []      // ← 新增：清空上传队列
        uploadResults.value = []
        msg.value = ''
        nodeName.value = ''
        if (fileInputRef.value) fileInputRef.value.value = ''
    }, 200)
}

/* ===== 弹窗打开时应用「预选的数据类型」 ===== */
watch(
    () => appStore.uploadVisible,
    (v) => {
        if (!v) return
        if (currentDataset.value.needNode) loadNodes()
        const key = appStore.uploadInitialKey
        if (key && DATASETS.some((d) => d.key === key)) {
            datasetKey.value = key
        }
        msg.value = ''
        uploadResults.value = []
    },
)

function onFilesChange(e: Event) {
    const target = e.target as HTMLInputElement
    selectedFiles.value = Array.from(target.files ?? [])
    msg.value = ''
    uploadResults.value = []
}

async function submit() {
    if (!canSubmit.value) return

    uploading.value = true
    msg.value = ''
    uploadResults.value = []

    // 先入 ref，让 ref 内的元素全部变成 Proxy
    uploadingItems.value = selectedFiles.value.map((f) => ({
        file: f,
        name: f.name,
        loaded: 0,
        total: f.size,
        percent: 0,
        status: 'pending',
    }))

    const ds = currentDataset.value
    const nodeNameToSend = ds.needNode ? nodeName.value : undefined
    let okCount = 0

    // 关键：遍历 uploadingItems.value 里的元素（Proxy）
    for (let i = 0; i < uploadingItems.value.length; i++) {
        const item = uploadingItems.value[i]   // ← Proxy，修改会触发响应
        item.status = 'uploading'
        item.percent = 0
        item.loaded = 0

        try {
            const res = await uploadSingleTempFile(
                {
                    file: item.file,
                    dataType: ds.dataType,
                    subType: ds.subType,
                    nodeName: nodeNameToSend,
                },
                (loaded, total, percent) => {
                    // 直接写 Proxy 的字段
                    item.loaded = loaded
                    item.total = total || item.file.size
                    item.percent = percent
                },
            )

            const r: UploadItemResult =
                res?.results?.[0] ||
                (res as unknown as UploadItemResult) || {
                    ok: true,
                    name: item.name,
                }

            item.result = r
            if (r.ok) {
                item.status = 'ok'
                item.percent = 100
                uploadResults.value.push(r)
                okCount++
            } else {
                item.status = 'error'
                item.error = r.error || '上传失败'
                uploadResults.value.push({ ...r, ok: false })
            }
        } catch (e) {
            item.status = 'error'
            item.error = (e as Error).message || '上传失败'
            uploadResults.value.push({
                ok: false,
                name: item.name,
                error: item.error,
            })
        }
    }

    uploading.value = false

    const total = uploadingItems.value.length
    if (okCount === total) {
        msg.value = `全部上传成功（${total} 个文件）`
        msgType.value = 'ok'
    } else if (okCount === 0) {
        msg.value = `全部失败（${total} 个文件）`
        msgType.value = 'err'
    } else {
        msg.value = `成功 ${okCount} 个，失败 ${total - okCount} 个`
        msgType.value = 'err'
    }

    if (okCount > 0) {
        selectedFiles.value = []
        if (fileInputRef.value) fileInputRef.value.value = ''
        appStore.bumpDataVersion()
    }
}

watch(datasetKey, () => {
    msg.value = ''
    uploadResults.value = []
    if (currentDataset.value.needNode) loadNodes()
})
</script>

<style scoped>
.upload-mask {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.upload-modal {
    position: relative;
    width: 540px;
    max-width: 92vw;
    max-height: 88vh;
    display: flex;
    flex-direction: column;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
    overflow: hidden;
}

.close-btn {
    position: absolute;
    top: 8px;
    right: 14px;
    border: none;
    background: transparent;
    font-size: 24px;
    color: #909399;
    cursor: pointer;
    line-height: 1;
    z-index: 1;
}

.close-btn:hover {
    color: #303133;
}

.modal-header {
    padding: 20px 24px 12px;
    border-bottom: 1px solid #f0f2f5;
}

.modal-title {
    margin: 0 0 4px;
    font-size: 17px;
    font-weight: 600;
    color: #1f2d3d;
}

.modal-subtitle {
    margin: 0;
    font-size: 12px;
    color: #909399;
}

.modal-body {
    flex: 1;
    padding: 16px 24px;
    overflow-y: auto;
}

.form-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 14px;
}

.form-item label {
    font-size: 13px;
    color: #606266;
}

.select,
.input {
    height: 34px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
}

.select:focus,
.input:focus {
    border-color: #2d6cdf;
}

.file-input {
    font-size: 13px;
}

.selected-tip {
    margin: 0 0 10px;
    padding: 6px 10px;
    background: #f5f7fa;
    border-radius: 4px;
    font-size: 12px;
    color: #606266;
    word-break: break-all;
}

.msg {
    margin: 0 0 10px;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
}

.msg.ok {
    background: #f0f9eb;
    color: #67c23a;
}

.msg.err {
    background: #fef0f0;
    color: #f56c6c;
}

.result-list {
    list-style: none;
    margin: 0;
    padding: 8px 10px;
    background: #fafbfc;
    border-radius: 4px;
    font-size: 12px;
    max-height: 200px;
    overflow-y: auto;
}

.result-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
}

.result-icon {
    font-weight: 700;
}

.result-item.ok .result-icon {
    color: #67c23a;
}

.result-item.err .result-icon {
    color: #f56c6c;
}

.result-name {
    color: #303133;
    word-break: break-all;
}

.result-extra {
    color: #909399;
}

.modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 12px 24px;
    border-top: 1px solid #f0f2f5;
    background: #fafbfc;
}

.btn {
    height: 34px;
    padding: 0 18px;
    border: none;
    border-radius: 4px;
    background: #2d6cdf;
    color: #fff;
    font-size: 13px;
    cursor: pointer;
}

.btn:hover:not(:disabled) {
    background: #2459b8;
}

.btn:disabled {
    background: #a0b4d8;
    cursor: not-allowed;
}

.btn.ghost {
    background: transparent;
    color: #606266;
    border: 1px solid #dcdfe6;
}

.btn.ghost:hover:not(:disabled) {
    background: #f5f7fa;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}

.node-list {
    color: #2d6cdf;
    word-break: break-all;
}

.node-list {
    color: #2d6cdf;
    word-break: break-all;
}

.ignored-tip {
    color: #e6a23c;
    font-size: 12px;
}

/* ===== 上传进度 ===== */
.progress-wrap {
    margin-bottom: 12px;
}

.overall-progress {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
}

.overall-bar-wrap {
    flex: 1;
    height: 10px;
    background: #f0f2f5;
    border-radius: 5px;
    overflow: hidden;
}

.overall-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #2d6cdf, #5b9bff);
    border-radius: 5px;
    transition: width 0.2s;
}

.overall-text {
    font-size: 12px;
    color: #606266;
    font-variant-numeric: tabular-nums;
    min-width: 80px;
    text-align: right;
}

.queue-list {
    list-style: none;
    margin: 0;
    padding: 8px 10px;
    background: #fafbfc;
    border-radius: 4px;
    font-size: 12px;
    max-height: 220px;
    overflow-y: auto;
}

.queue-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
}

.queue-icon {
    width: 16px;
    text-align: center;
    font-weight: 700;
}

.queue-item.pending .queue-icon {
    color: #c0c4cc;
}

.queue-item.uploading .queue-icon {
    color: #2d6cdf;
}

.queue-item.ok .queue-icon {
    color: #67c23a;
}

.queue-item.error .queue-icon {
    color: #f56c6c;
}

.queue-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #303133;
}

.queue-bar-wrap {
    flex: 0 0 120px;
    height: 6px;
    background: #eef0f3;
    border-radius: 3px;
    overflow: hidden;
}

.queue-bar-fill {
    height: 100%;
    background: #2d6cdf;
    border-radius: 3px;
    transition: width 0.2s;
}

.queue-item.ok .queue-bar-fill {
    background: #67c23a;
}

.queue-item.error .queue-bar-fill {
    background: #f56c6c;
}

.queue-percent {
    min-width: 40px;
    text-align: right;
    color: #606266;
    font-variant-numeric: tabular-nums;
}

.queue-size {
    min-width: 62px;
    text-align: right;
    color: #909399;
    font-size: 11px;
}
</style>