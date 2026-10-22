<template>
    <PageContainer title="月报数据部分填充">
        <template #extra>
            <button class="btn-upload" @click="openTemplatePicker">
                📤 上传模板
            </button>
            <input ref="templateInputRef" type="file" accept=".docx" class="hidden-input" @change="onTemplateChange" />
        </template>

        <!-- 步骤 1：模板 -->
        <div class="card">
            <h3 class="step-title">
                <span class="step-num">1</span> 选择 Word 模板
            </h3>
            <p class="hint">
                模板放在 <code>temp/monthly/templates/</code> 下，支持 docxtpl 占位符（如
                <code>&#123;&#123; plant_name &#125;&#125;</code>）。
            </p>
            <div class="row">
                <select v-model="selectedTemplate" class="input select">
                    <option value="">请选择模板</option>
                    <option v-for="t in templates" :key="t.name" :value="t.name">
                        {{ t.name }}
                    </option>
                </select>
                <span v-if="currentTemplateInfo" class="template-info">
                    {{ formatSize(currentTemplateInfo.size) }} ·
                    {{ currentTemplateInfo.uploadedAt }}
                </span>
                <button class="btn ghost" :disabled="!selectedTemplate" @click="removeTemplate">
                    删除此模板
                </button>
                <button class="btn ghost" :disabled="loading" @click="loadTemplates">
                    刷新
                </button>
            </div>
            <p v-if="!templates.length" class="empty-tip small">
                暂无模板，请点击右上角「📤 上传模板」上传
                <code>电力交易服务月报_模板.docx</code>
            </p>
        </div>

        <!-- 步骤 2：PDF + 操作 -->
        <div class="card">
            <h3 class="step-title">
                <span class="step-num">2</span> 上传 PDF 结算单
            </h3>
            <p class="hint">
                上传交易中心出具的结算单 PDF，系统自动解析并填充到 Word 模板。
            </p>
            <div class="row">
                <input ref="pdfInputRef" type="file" accept=".pdf" class="file-input" @change="onPdfChange" />
                <button class="btn ghost" :disabled="!pdfFile || parsing" @click="parsePdf">
                    {{ parsing ? '解析中...' : '解析预览' }}
                </button>
                <button class="btn primary" :disabled="!pdfFile || !selectedTemplate || generating"
                    @click="generateReport">
                    {{ generating ? '生成中...' : '📄 生成月报' }}
                </button>
            </div>
            <p v-if="selectedFileName" class="file-name">
                已选文件：{{ selectedFileName }}
            </p>
            <p v-if="msg" class="msg" :class="msgType">{{ msg }}</p>
        </div>

        <!-- 步骤 3：解析预览 -->
        <div v-if="previewFields.length" class="card">
            <h3 class="step-title">
                <span class="step-num">3</span> 解析结果预览
                <span class="preview-meta">
                    （已填充 {{ filledCount }} / {{ previewFields.length }} 个字段）
                </span>
            </h3>
            <div class="preview-wrap scroll-y">
                <table class="preview-table">
                    <thead>
                        <tr>
                            <th style="width: 220px">字段</th>
                            <th style="width: 220px">占位符</th>
                            <th>值</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="f in previewFields" :key="f.key" :class="{ filled: !!f.value }">
                            <td class="label-cell">{{ f.label }}</td>
                            <td class="key-cell"><code>{{ f.key }}</code></td>
                            <td class="value-cell" :class="{ empty: !f.value }">
                                {{ f.value || '—' }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import {
    listMonthlyTemplates,
    uploadMonthlyTemplate,
    deleteMonthlyTemplate,
    parseMonthlyPdf,
    generateMonthlyReport,
    type TemplateItem,
    type FieldItem,
} from '@/api/modules/monthly'

/* ============ 模板 ============ */
const templates = ref<TemplateItem[]>([])
const selectedTemplate = ref('')
const loading = ref(false)
const templateInputRef = ref<HTMLInputElement | null>(null)

const currentTemplateInfo = computed(
    () => templates.value.find((t) => t.name === selectedTemplate.value) || null,
)

function formatSize(n: number): string {
    if (n < 1024) return `${n} B`
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
    return `${(n / 1024 / 1024).toFixed(2)} MB`
}

async function loadTemplates() {
    loading.value = true
    try {
        templates.value = await listMonthlyTemplates()
        if (!selectedTemplate.value && templates.value.length) {
            selectedTemplate.value = templates.value[0].name
        }
    } catch (e) {
        console.warn('加载模板失败', e)
        templates.value = []
    } finally {
        loading.value = false
    }
}

function openTemplatePicker() {
    templateInputRef.value?.click()
}

async function onTemplateChange(e: Event) {
    const input = e.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return
    try {
        await uploadMonthlyTemplate(file)
        await loadTemplates()
        selectedTemplate.value = file.name
        msg.value = `模板「${file.name}」上传成功`
        msgType.value = 'ok'
    } catch (err) {
        msg.value = (err as Error).message || '模板上传失败'
        msgType.value = 'err'
    } finally {
        input.value = ''
    }
}

async function removeTemplate() {
    if (!selectedTemplate.value) return
    if (!confirm(`确定删除模板「${selectedTemplate.value}」？`)) return
    try {
        await deleteMonthlyTemplate(selectedTemplate.value)
        selectedTemplate.value = ''
        await loadTemplates()
        msg.value = '模板已删除'
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message || '删除失败'
        msgType.value = 'err'
    }
}

/* ============ PDF ============ */
const pdfFile = ref<File | null>(null)
const pdfInputRef = ref<HTMLInputElement | null>(null)
const selectedFileName = ref('')
const parsing = ref(false)
const generating = ref(false)
const msg = ref('')
const msgType = ref<'ok' | 'err'>('ok')

const previewFields = ref<FieldItem[]>([])
const filledCount = computed(
    () => previewFields.value.filter((f) => f.value).length,
)

function onPdfChange(e: Event) {
    const input = e.target as HTMLInputElement
    pdfFile.value = input.files?.[0] ?? null
    selectedFileName.value = pdfFile.value?.name || ''
    previewFields.value = []
    msg.value = ''
}

async function parsePdf() {
    if (!pdfFile.value) return
    parsing.value = true
    msg.value = ''
    try {
        const res = await parseMonthlyPdf(pdfFile.value)
        previewFields.value = res.fields
        msg.value = `解析完成，共识别 ${res.fields.filter((f) => f.value).length} 个字段`
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message || '解析失败'
        msgType.value = 'err'
        previewFields.value = []
    } finally {
        parsing.value = false
    }
}

async function generateReport() {
    if (!pdfFile.value || !selectedTemplate.value) return
    generating.value = true
    msg.value = ''
    try {
        const res = await generateMonthlyReport(
            pdfFile.value,
            selectedTemplate.value,
        )
        downloadBase64File(res.base64, res.filename)
        msg.value = `月报已生成：${res.filename}`
        msgType.value = 'ok'
    } catch (e) {
        msg.value = (e as Error).message || '生成失败'
        msgType.value = 'err'
    } finally {
        generating.value = false
    }
}

function downloadBase64File(b64: string, filename: string) {
    const bin = atob(b64)
    const bytes = new Uint8Array(bin.length)
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
    const blob = new Blob([bytes], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
}

onMounted(loadTemplates)
</script>

<style scoped>
.hidden-input {
    display: none;
}

.card {
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.step-title {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: #1f2d3d;
    display: flex;
    align-items: center;
    gap: 8px;
}

.step-num {
    display: inline-block;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #2d6cdf;
    color: #fff;
    font-size: 12px;
    text-align: center;
    line-height: 22px;
}

.preview-meta {
    font-size: 12px;
    color: #909399;
    font-weight: 400;
    margin-left: 4px;
}

.hint {
    margin: 0;
    font-size: 12px;
    color: #909399;
    line-height: 1.6;
}

.hint code {
    padding: 1px 6px;
    background: #f4f4f5;
    border-radius: 3px;
    color: #606266;
}

.row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.input {
    height: 32px;
    padding: 0 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 13px;
    outline: none;
}

.input:focus {
    border-color: #2d6cdf;
}

.select {
    min-width: 260px;
}

.template-info {
    font-size: 12px;
    color: #909399;
}

.file-input {
    font-size: 13px;
    flex: 1;
    min-width: 240px;
}

.file-name {
    margin: 0;
    font-size: 12px;
    color: #606266;
    word-break: break-all;
}

.msg {
    margin: 0;
    padding: 6px 10px;
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

.btn {
    height: 32px;
    padding: 0 16px;
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

.btn.ghost {
    background: #fff;
    color: #606266;
    border: 1px solid #dcdfe6;
}

.btn.ghost:hover:not(:disabled) {
    background: #f5f7fa;
}

.btn:disabled {
    color: #c0c4cc;
    cursor: not-allowed;
}

/* 预览表 */
.preview-wrap {
    max-height: 460px;
    border: 1px solid #f0f2f5;
    border-radius: 4px;
}

.preview-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

.preview-table th,
.preview-table td {
    padding: 6px 10px;
    border-bottom: 1px solid #f0f2f5;
    text-align: left;
    vertical-align: top;
}

.preview-table th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: #f5f7fa;
    color: #303133;
    font-weight: 600;
    font-size: 12px;
}

.preview-table tr.filled .value-cell {
    color: #1f2d3d;
    font-weight: 500;
}

.value-cell.empty {
    color: #c0c4cc;
}

.key-cell code {
    padding: 1px 5px;
    background: #f4f4f5;
    border-radius: 3px;
    font-size: 11px;
    color: #606266;
}

.empty-tip.small {
    padding: 12px 0 0;
    font-size: 12px;
    color: #909399;
}
</style>