<template>
    <PageContainer title="中长期合约配置">
        <div class="config-container">
            <!-- 左侧：基础配置 -->
            <div class="panel panel-left">
                <div class="section-title">1. 基础配置 (全局共享)</div>

                <AnnualConfigNotice />

                <div class="form-group">
                    <label>典型曲线 (Excel)</label>
                    <label class="upload-area" :class="{ 'has-file': baseFiles.curve }">
                        <input type="file" accept=".xlsx,.xls" class="hidden-input"
                            @change="handleBaseUpload($event, 'curve')" />
                        <div class="upload-content">
                            <span class="icon">📄</span>
                            <span class="text">{{ baseFiles.curve ? '重新上传典型曲线' : '点击或拖拽上传典型曲线' }}</span>
                        </div>
                    </label>
                </div>

                <div class="form-group">
                    <div class="label-row">
                        <label>年度节假日 (Excel)</label>
                        <a :href="apiUrl('/contract/template')" target="_blank" class="link">下载模板</a>
                    </div>
                    <label class="upload-area" :class="{ 'has-file': baseFiles.holiday }">
                        <input type="file" accept=".xlsx,.xls" class="hidden-input"
                            @change="handleBaseUpload($event, 'holiday')" />
                        <div class="upload-content">
                            <span class="icon">📅</span>
                            <span class="text">{{ baseFiles.holiday ? '重新上传节假日配置' : '点击或拖拽上传节假日配置' }}</span>
                        </div>
                    </label>
                </div>
            </div>

            <!-- 右侧：节点数据上传 -->
            <div class="panel panel-right scroll-y">
                <div class="section-title">2. 节点数据配置</div>

                <div class="form-group">
                    <label>选择电厂节点</label>
                    <div style="width: 300px;">
                        <SearchableSelect v-model="selectedNode" :options="nodeOptions.map(n => n.name)" />
                    </div>
                </div>

                <div v-if="selectedNode" class="data-groups">
                    <!-- ===== 组1：合约 & 省内滚撮 ===== -->
                    <div class="data-group">
                        <div class="group-header">
                            <span class="group-title">📋 合约与省内滚撮</span>
                            <span class="group-hint">作用于「电厂合约仓位」页面</span>
                        </div>
                        <div class="group-body">
                            <div class="upload-item">
                                <span class="item-title">年度合约电量</span>
                                <label class="upload-btn">
                                    <input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                        @change="(e) => handleDataUpload(e, 'year')" />
                                    <span class="btn-text">📤 选择文件</span>
                                </label>
                            </div>
                            <div class="upload-item">
                                <span class="item-title">月度合约电量</span>
                                <label class="upload-btn">
                                    <input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                        @change="(e) => handleDataUpload(e, 'month')" />
                                    <span class="btn-text">📤 选择文件</span>
                                </label>
                            </div>
                            <div class="upload-item">
                                <span class="item-title">上旬合约电量</span>
                                <label class="upload-btn">
                                    <input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                        @change="(e) => handleDataUpload(e, 'tenday1')" />
                                    <span class="btn-text">📤 选择文件</span>
                                </label>
                            </div>
                            <div class="upload-item">
                                <span class="item-title">中旬合约电量</span>
                                <label class="upload-btn">
                                    <input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                        @change="(e) => handleDataUpload(e, 'tenday2')" />
                                    <span class="btn-text">📤 选择文件</span>
                                </label>
                            </div>
                            <div class="upload-item">
                                <span class="item-title">下旬合约电量</span>
                                <label class="upload-btn">
                                    <input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                        @change="(e) => handleDataUpload(e, 'tenday3')" />
                                    <span class="btn-text">📤 选择文件</span>
                                </label>
                            </div>
                            <div class="upload-item">
                                <span class="item-title">省内滚撮数据</span>
                                <label class="upload-btn">
                                    <input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                        @change="(e) => handleDataUpload(e, 'province_rolling')" />
                                    <span class="btn-text">📤 选择文件</span>
                                </label>
                            </div>
                        </div>
                    </div>

                    <!-- ===== 组2：日内单独滚撮 ===== -->
                    <div class="data-group">
                        <div class="group-header">
                            <span class="group-title">🔄 日内单独滚撮</span>
                            <span class="group-hint">作用于「滚撮收益模拟」页面</span>
                        </div>
                        <div class="group-body">
                            <div class="upload-item" style="grid-column: 1 / -1;">
                                <span class="item-title">日内滚撮数据（需先选择操作日期）</span>
                                <div class="trade-upload-row">
                                    <input type="date" v-model="rollingOpDate" class="trade-date-input"
                                        style="width: 140px;" />
                                    <div style="flex: 1; min-width: 200px;">
                                        <UploadFile v-model="rollingFiles" :multiple="true" text="选择滚撮文件"
                                            :disabled="!rollingOpDate" @change="uploadRollingData" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- ===== 组3：长三角省间 ===== -->
                    <div class="data-group">
                        <div class="group-header">
                            <span class="group-title">🌏 长三角省间滚撮</span>
                            <span class="group-hint">作用于「长三角省间交易收益模拟」页面</span>
                        </div>
                        <div class="group-body">
                            <div class="upload-item" style="grid-column: 1 / -1;">
                                <span class="item-title">长三角省间交易数据</span>
                                <label class="upload-btn">
                                    <input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                        @change="(e) => handleDataUpload(e, 'cross_province')" />
                                    <span class="btn-text">📤 选择文件</span>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>

                <div v-else class="empty-tip">
                    请先在上方选择电厂节点，然后上传相应的数据文件。
                </div>
            </div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import { listPlantNodes, fetchGlobalNode, type PlantNode } from '@/api/modules/nodes'
import { request } from '@/api/request'
import SearchableSelect from '@/components/SearchableSelect.vue'
import UploadFile from '@/components/UploadFile.vue'
import AnnualConfigNotice from '@/components/AnnualConfigNotice.vue'
import { apiUrl } from '@/utils/apiBase'

const nodeOptions = ref<PlantNode[]>([])
const selectedNode = ref('')
const rollingOpDate = ref('')
const baseFiles = ref({ curve: false, holiday: false })
const rollingFiles = ref<File[]>([])

onMounted(async () => {
    try {
        nodeOptions.value = await listPlantNodes()
    } catch {
        nodeOptions.value = []
    }
    // ⭐ 默认使用「全局默认节点」
    try {
        const globalNode = await fetchGlobalNode()
        if (globalNode && nodeOptions.value.some(n => n.name === globalNode)) {
            selectedNode.value = globalNode
        }
    } catch {
        // ignore
    }
})

async function handleBaseUpload(e: Event, type: 'curve' | 'holiday') {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return

    const formData = new FormData()
    formData.append(type, file)

    try {
        await request({
            url: '/contract/config/base',
            method: 'post',
            data: formData,
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        baseFiles.value[type] = true
        alert('保存基础配置成功')
    } catch {
        alert('保存失败')
    }
}

async function handleDataUpload(e: Event, type: string) {
    const files = (e.target as HTMLInputElement).files
    if (!files || files.length === 0 || !selectedNode.value) return

    const formData = new FormData()
    formData.append('node_name', selectedNode.value)
    formData.append('data_type', type)

    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i])
    }

    try {
        await request({
            url: '/contract/config/node-data',
            method: 'post',
            data: formData,
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        alert(`${type} 上传成功`)
    } catch (err: any) {
        alert('上传失败：\n' + (err.message || '未知错误'))
    } finally {
        // 允许再次上传同名文件
        ; (e.target as HTMLInputElement).value = ''
    }
}

async function uploadRollingData(files: File[]) {
    if (files.length === 0 || !rollingOpDate.value || !selectedNode.value) return

    const formData = new FormData()
    formData.append('node_name', selectedNode.value)
    formData.append('data_type', 'rolling')
    formData.append('op_date', rollingOpDate.value)
    files.forEach(f => formData.append('files', f))

    try {
        await request({ url: '/contract/config/node-data', method: 'post', data: formData })
        alert('日内滚撮数据上传成功')
        rollingFiles.value = []
    } catch {
        alert('上传失败')
    }
}
</script>

<style scoped>
.config-container {
    display: flex;
    gap: 20px;
    height: calc(100vh - 140px);
}

.panel {
    background: #fff;
    border-radius: 8px;
    padding: 24px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
    display: flex;
    flex-direction: column;
}

.panel-left {
    flex: 0 0 340px;
}

.panel-right {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
}

.section-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2d3d;
    margin-bottom: 24px;
    padding-bottom: 12px;
    border-bottom: 1px solid #ebeef5;
}

.form-group {
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.form-group>label,
.item-title {
    font-size: 13px;
    color: #606266;
    font-weight: 500;
}

.label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.link {
    color: #2d6cdf;
    text-decoration: none;
    font-size: 13px;
}

.link:hover {
    text-decoration: underline;
}

.hidden-input {
    display: none;
}

/* 左侧上传框 */
.upload-area {
    display: flex;
    justify-content: center;
    align-items: center;
    border: 1px dashed #dcdfe6;
    border-radius: 6px;
    background: #fafbfc;
    padding: 20px 10px;
    cursor: pointer;
    transition: all 0.3s ease;
}

.upload-area:hover {
    border-color: #2d6cdf;
    background: #f0f5ff;
}

.upload-area.has-file {
    border-color: #67c23a;
    background: #f0f9eb;
}

.upload-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
}

.upload-content .icon {
    font-size: 24px;
}

.upload-content .text {
    font-size: 13px;
    color: #606266;
}

.upload-area.has-file .text {
    color: #67c23a;
    font-weight: 500;
}

/* ===== 右侧：分组 ===== */
.data-groups {
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-top: 8px;
}

.data-group {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
}

.group-header {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px dashed #cbd5e1;
}

.group-title {
    font-size: 14px;
    font-weight: 600;
    color: #1e293b;
}

.group-hint {
    font-size: 12px;
    color: #94a3b8;
}

.group-body {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
}

.upload-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.upload-btn {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    height: 34px;
    border: 1px solid #2d6cdf;
    border-radius: 6px;
    background: #fff;
    color: #2d6cdf;
    cursor: pointer;
    transition: all 0.2s;
}

.upload-btn:hover {
    background: #2d6cdf;
    color: #fff;
}

.btn-text {
    font-size: 13px;
    font-weight: 500;
}

.trade-upload-row {
    display: flex;
    gap: 8px;
    align-items: center;
}

.trade-date-input {
    height: 34px;
    padding: 0 8px;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    outline: none;
}

.trade-date-input:focus {
    border-color: #2d6cdf;
}

.empty-tip {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #909399;
    font-size: 14px;
    background: #fafbfc;
    border-radius: 8px;
    border: 1px dashed #dcdfe6;
    margin-top: 16px;
}
</style>