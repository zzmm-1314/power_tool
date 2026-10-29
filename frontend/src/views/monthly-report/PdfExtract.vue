<template>
    <PageContainer title="结算单 PDF 数据提取">
        <div class="extract-layout">
            <!-- 左侧：上传与配置 -->
            <div class="panel panel-left">
                <div class="section-title">1. 上传 PDF 文件</div>
                <div class="upload-area" @click="triggerFileInput">
                    <input ref="fileInputRef" type="file" accept=".pdf" multiple class="hidden-input"
                        @change="onFilesChange" />
                    <div v-if="!selectedFiles.length" class="upload-placeholder">
                        <p>点击此处选择 PDF 结算单</p>
                        <p class="sub-text">支持多选，自动按文件名识别月份</p>
                    </div>
                    <div v-else class="file-list">
                        <p v-for="f in selectedFiles" :key="f.name">📄 {{ f.name }}</p>
                    </div>
                </div>
                <button v-if="selectedFiles.length" class="btn-text" @click="clearFiles">清空已选</button>

                <div class="section-title" style="margin-top: 20px;">2. 选择提取字段</div>
                <div class="field-group">
                    <label class="checkbox-label">
                        <input type="checkbox" v-model="fields.page1_total_qty" /> 第一页 - 合计电量
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" v-model="fields.page1_total_price" /> 第一页 - 合计电价
                    </label>
                    <div class="divider"></div>
                    <label class="checkbox-label">
                        <input type="checkbox" v-model="fields.extract_page2" /> 提取第二页完整表格 (可选)
                    </label>
                </div>

                <button class="btn-submit" :disabled="!selectedFiles.length || extracting" @click="submitExtract">
                    {{ extracting ? '正在提取...' : '开始提取' }}
                </button>
            </div>

            <!-- 右侧：结果展示 -->
            <div class="panel panel-right">
                <div class="result-header">
                    <div class="section-title" style="margin-bottom: 0;">第一页提取结果</div>
                    <div class="action-btns" v-if="results.length">
                        <button v-if="hasPage2Data" class="btn-download" @click="downloadPage2">
                            📥 下载第二页表格
                        </button>
                        <button class="btn-export" @click="exportExcel">
                            📥 导出第一页数据
                        </button>
                    </div>
                </div>

                <div v-if="!results.length" class="empty-tip">暂无数据，请在左侧上传并提取</div>
                <div v-else class="table-wrap">
                    <table class="result-table">
                        <thead>
                            <tr>
                                <th>文件名</th>
                                <th>月份</th>
                                <th v-if="fields.page1_total_qty">合计电量</th>
                                <th v-if="fields.page1_total_price">合计电价</th>
                                <th>状态</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(row, idx) in results" :key="idx">
                                <td :title="row.filename" class="col-name">{{ row.filename }}</td>
                                <td>{{ row.month }}</td>
                                <td v-if="fields.page1_total_qty">{{ row.page1_total_qty ?? '-' }}</td>
                                <td v-if="fields.page1_total_price">{{ row.page1_total_price ?? '-' }}</td>
                                <td>
                                    <span :class="['status-tag', row.status]">
                                        {{ row.status === 'success' ? '成功' : '失败' }}
                                    </span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import PageContainer from '@/components/PageContainer.vue'

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFiles = ref<File[]>([])
const extracting = ref(false)
const results = ref<any[]>([])

const fields = reactive({
    page1_total_qty: true,
    page1_total_price: true,
    extract_page2: false,
})

// 判断是否有第二页数据，控制按钮显示
const hasPage2Data = computed(() => {
    return results.value.some(r => r.page2_data && r.page2_data.length > 0)
})

function triggerFileInput() {
    fileInputRef.value?.click()
}

function onFilesChange(e: Event) {
    const target = e.target as HTMLInputElement
    selectedFiles.value = Array.from(target.files ?? [])
}

function clearFiles() {
    selectedFiles.value = []
    if (fileInputRef.value) fileInputRef.value.value = ''
}

async function submitExtract() {
    if (!selectedFiles.value.length) return
    extracting.value = true
    results.value = []

    const formData = new FormData()
    for (const f of selectedFiles.value) {
        formData.append('files', f)
    }
    formData.append('fields', JSON.stringify(fields))

    try {
        const res = await fetch('/api/monthly/extract-pdf', {
            method: 'POST',
            body: formData,
        })
        const json = await res.json()

        // 兼容后端 code 为 0 或 200 的情况
        if (json.code === 0 || json.code === 200) {
            results.value = json.data || []
        } else {
            alert('提取失败：' + (json.msg || '未知错误'))
        }
    } catch (err) {
        console.error(err)
        alert('请求失败，请检查网络或后端服务')
    } finally {
        extracting.value = false
    }
}

// 导出第一页
async function exportExcel() {
    if (!results.value.length) return

    // 剔除 page2_data，防止第一页导出报错
    const page1Results = results.value.map(r => {
        const { page2_data, ...rest } = r
        return rest
    })

    try {
        const res = await fetch('/api/monthly/export-excel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ results: page1Results }),
        })
        if (!res.ok) throw new Error()
        triggerDownload(await res.blob(), `第一页提取结果_${Date.now()}.xlsx`)
    } catch (err) {
        alert('第一页导出失败')
    }
}

// 下载第二页
async function downloadPage2() {
    const page2List = results.value
        .filter(r => r.page2_data && r.page2_data.length)
        .map(r => ({
            filename: r.filename,
            data: r.page2_data
        }))

    if (!page2List.length) return

    try {
        const res = await fetch('/api/monthly/export-page2-excel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ page2_list: page2List }),
        })
        if (!res.ok) throw new Error()
        triggerDownload(await res.blob(), `第二页完整表格_${Date.now()}.xlsx`)
    } catch (err) {
        alert('第二页导出失败')
    }
}

function triggerDownload(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
}
</script>

<style scoped>
.extract-layout {
    display: flex;
    gap: 16px;
    height: calc(100vh - 160px);
}

.panel {
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    padding: 16px;
    display: flex;
    flex-direction: column;
}

.panel-left {
    flex: 0 0 320px;
}

.panel-right {
    flex: 1;
    overflow: hidden;
}

.section-title {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 12px;
}

/* 上传区域 */
.upload-area {
    border: 1px dashed #dcdfe6;
    border-radius: 6px;
    padding: 24px 20px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s;
    background: #fafbfc;
    word-break: break-all;
}

.upload-area:hover {
    border-color: #2d6cdf;
}

.hidden-input {
    display: none;
}

.upload-placeholder p {
    margin: 0;
    color: #606266;
    font-size: 14px;
}

.upload-placeholder .sub-text {
    margin-top: 6px;
    font-size: 12px;
    color: #909399;
}

.file-list p {
    margin: 4px 0;
    font-size: 13px;
    color: #2d6cdf;
}

.btn-text {
    background: none;
    border: none;
    color: #909399;
    cursor: pointer;
    padding: 0;
    font-size: 12px;
    text-align: right;
    margin-top: 8px;
}

.btn-text:hover {
    color: #f56c6c;
}

/* 勾选组 */
.field-group {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.checkbox-label {
    font-size: 13px;
    color: #303133;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
}

.divider {
    height: 1px;
    background: #ebeef5;
    margin: 6px 0;
}

.btn-submit {
    margin-top: auto;
    height: 36px;
    background: #2d6cdf;
    color: #fff;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    cursor: pointer;
}

.btn-submit:disabled {
    background: #a0b4d8;
    cursor: not-allowed;
}

/* 右侧结果区 */
.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.action-btns {
    display: flex;
    gap: 8px;
}

.btn-download,
.btn-export {
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-download {
    background: #fdf6ec;
    color: #e6a23c;
    border: 1px solid #f5dab1;
}

.btn-download:hover {
    background: #e6a23c;
    color: #fff;
}

.btn-export {
    background: #ecf5ff;
    color: #2d6cdf;
    border: 1px solid #c6e2ff;
}

.btn-export:hover {
    background: #2d6cdf;
    color: #fff;
}

/* 表格 */
.table-wrap {
    flex: 1;
    overflow: auto;
    border: 1px solid #ebeef5;
    border-radius: 4px;
}

.result-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.result-table th,
.result-table td {
    padding: 10px 12px;
    text-align: right;
    border-bottom: 1px solid #ebeef5;
    white-space: nowrap;
}

.result-table th {
    background: #f5f7fa;
    font-weight: 600;
    color: #303133;
    position: sticky;
    top: 0;
    z-index: 2;
    text-align: center;
}

.result-table .col-name {
    text-align: left;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
}

.status-tag {
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
}

.status-tag.success {
    background: #f0f9eb;
    color: #67c23a;
}

.status-tag.failed {
    background: #fef0f0;
    color: #f56c6c;
}

.empty-tip {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    color: #909399;
    border: 1px dashed #ebeef5;
    border-radius: 4px;
}
</style>