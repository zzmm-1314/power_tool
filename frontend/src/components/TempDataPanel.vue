<template>
    <div class="temp-panel">
        <div class="panel-header" @click="expanded = !expanded">
            <span class="panel-title">📁 临时数据文件</span>
            <span v-if="files.length" class="badge">{{ files.length }}</span>
            <span class="arrow" :class="{ open: expanded }">▾</span>
        </div>

        <div v-show="expanded" class="panel-body">
            <p class="hint">
                <template v-if="dataType === 'load'">
                    上传「实际负荷/预测负荷」Excel，系统自动识别文件名日期。
                </template>
                <template v-else-if="dataType === 'pv'">
                    上传「新能源总出力 / 光伏总出力预测」Excel，自动识别日期。
                </template>
                <template v-else-if="dataType === 'day-ahead' && subType === 'unified'">
                    上传「日前市场出清负荷侧电价YYYYMMDD.xlsx」。
                </template>
                <template v-else-if="dataType === 'spread' && subType === 'unified'">
                    上传「实时市场出清负荷侧电价YYYYMMDD.xlsx」。
                    价差热力图 = 日前价格 − 实时价格，需要日前与实时同时存在。
                </template>
                <template v-else>
                    上传 Excel 临时展示；数据库更新后系统会自动删除对应文件。
                </template>
            </p>

            <p v-if="msg" class="msg" :class="msgType">{{ msg }}</p>

            <ul class="file-list">
                <li v-for="f in files" :key="f.path" class="file-item">
                    <div class="file-info">
                        <span class="file-date">
                            {{ f.date || f.fileName || f.path }}
                        </span>
                        <span class="file-meta">
                            {{ f.date ? (f.fileName || f.path) : '' }}
                        </span>
                        <span class="file-uploaded">{{ f.uploadedAt }}</span>
                    </div>
                    <button class="icon-btn" @click="doDelete(f)">删除</button>
                </li>
                <li v-if="!files.length" class="empty">暂无匹配的临时数据</li>
            </ul>

            <div class="panel-footer">
                <button class="btn-refresh" :disabled="loading" @click="refresh">
                    {{ loading ? '刷新中...' : '刷新列表' }}
                </button>
                <button class="btn-setting" @click="openStorageSetting">
                    ⚙ 存储目录
                </button>
            </div>
            <StorageSettingModal v-model="storageModalVisible" @changed="onStorageChanged" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
    listTempData,
    deleteTempData,
    type TempFileItem,
} from '@/api/modules/tempData'
import { useAppStore } from '@/stores/app'
import StorageSettingModal from '@/components/StorageSettingModal.vue'
const props = defineProps<{
    dataType: string
    subType?: string
    date?: string
    nodeName?: string
}>()
const storageModalVisible = ref(false)
const appStore = useAppStore()

const expanded = ref(false)
const files = ref<TempFileItem[]>([])
const loading = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')

async function refresh() {
    loading.value = true
    try {
        files.value = await listTempData({
            dataType: props.dataType,
            subType: props.subType,
            date: props.date,
            nodeName: props.nodeName,
        })
    } catch {
        files.value = []
    } finally {
        loading.value = false
    }
}

async function doDelete(f: TempFileItem) {
    if (!confirm(`确定删除「${f.fileName || f.path}」？`)) return
    try {
        await deleteTempData(f.path)
        await refresh()
        appStore.bumpDataVersion()   // 通知其他页面刷新
    } catch (e) {
        msg.value = (e as Error).message || '删除失败'
        msgType.value = 'err'
    }
}
function openStorageSetting() {
    storageModalVisible.value = true
}

function onStorageChanged() {
    // 目录变了：强制刷新文件列表
    refresh()
}
/* 展开 / 条件变化 / 上传成功 → 自动刷新 */
watch(expanded, (v) => {
    if (v) refresh()
})
watch(
    () => [props.date, props.nodeName],
    () => {
        if (expanded.value) refresh()
    },
)
watch(
    () => appStore.dataVersion,
    () => {
        if (expanded.value) refresh()
    },
)
</script>

<style scoped>
.temp-panel {
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    overflow: hidden;
}

.panel-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 16px;
    cursor: pointer;
    user-select: none;
}

.panel-header:hover {
    background: #fafbfc;
}

.panel-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
}

.badge {
    min-width: 18px;
    height: 18px;
    padding: 0 6px;
    border-radius: 9px;
    background: #e6a23c;
    color: #fff;
    font-size: 12px;
    line-height: 18px;
    text-align: center;
}

.arrow {
    margin-left: auto;
    font-size: 12px;
    color: #909399;
    transition: transform 0.2s;
    transform: rotate(-90deg);
}

.arrow.open {
    transform: rotate(0deg);
}

.panel-body {
    padding: 4px 16px 16px;
    border-top: 1px solid #f0f2f5;
}

.hint {
    margin: 8px 0 12px;
    color: #909399;
    font-size: 12px;
    line-height: 1.6;
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

.file-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.file-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px dashed #ebeef5;
}

.file-item:last-child {
    border-bottom: none;
}

.file-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
}

.file-date {
    font-size: 13px;
    color: #303133;
    font-weight: 500;
}

.file-meta {
    font-size: 12px;
    color: #909399;
    word-break: break-all;
}

.file-uploaded {
    font-size: 12px;
    color: #c0c4cc;
}

.icon-btn {
    padding: 3px 10px;
    border: 1px solid #fbc4c4;
    border-radius: 4px;
    background: #fff;
    color: #f56c6c;
    font-size: 12px;
    cursor: pointer;
    white-space: nowrap;
    flex-shrink: 0;
}

.icon-btn:hover {
    background: #fef0f0;
}

.empty {
    padding: 16px 0;
    text-align: center;
    color: #c0c4cc;
    font-size: 12px;
}

.panel-footer {
    margin-top: 12px;
    text-align: right;
}

.btn-refresh {
    padding: 4px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    background: #fff;
    color: #606266;
    font-size: 12px;
    cursor: pointer;
}

.btn-refresh:hover:not(:disabled) {
    background: #f5f7fa;
}

.btn-refresh:disabled {
    color: #c0c4cc;
    cursor: not-allowed;
}

.panel-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 12px;
}

.btn-setting {
    padding: 4px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    background: #fff;
    color: #606266;
    font-size: 12px;
    cursor: pointer;
}

.btn-setting:hover {
    background: #f5f7fa;
    color: #2d6cdf;
    border-color: #2d6cdf;
}
</style>