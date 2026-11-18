<template>
    <PageContainer title="中长期合约配置">
        <div class="config-container">
            <!-- 左侧：基础配置（全厂共享） -->
            <div class="panel panel-left">
                <div class="section-title">1. 基础配置 (全局共享)</div>

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
            <div class="panel panel-right">
                <div class="section-title">2. 节点数据配置</div>

                <div class="form-group">
                    <label>选择电厂节点</label>
                    <div style="width: 300px;">
                        <SearchableSelect v-model="selectedNode" :options="nodeOptions.map(n => n.name)" />
                    </div>
                </div>

                <div class="data-grid" v-if="selectedNode">
                    <!-- 合约类 -->
                    <div class="upload-item">
                        <span class="item-title">年度合约电量</span>
                        <label class="upload-btn"><input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                @change="(e) => handleDataUpload(e, 'year')" /><span class="btn-text">📤
                                选择文件</span></label>
                    </div>
                    <div class="upload-item">
                        <span class="item-title">月度合约电量</span>
                        <label class="upload-btn"><input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                @change="(e) => handleDataUpload(e, 'month')" /><span class="btn-text">📤
                                选择文件</span></label>
                    </div>
                    <div class="upload-item">
                        <span class="item-title">上旬合约电量</span>
                        <label class="upload-btn"><input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                @change="(e) => handleDataUpload(e, 'tenday1')" /><span class="btn-text">📤
                                选择文件</span></label>
                    </div>
                    <div class="upload-item">
                        <span class="item-title">中旬合约电量</span>
                        <label class="upload-btn"><input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                @change="(e) => handleDataUpload(e, 'tenday2')" /><span class="btn-text">📤
                                选择文件</span></label>
                    </div>
                    <div class="upload-item">
                        <span class="item-title">下旬合约电量</span>
                        <label class="upload-btn"><input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                @change="(e) => handleDataUpload(e, 'tenday3')" /><span class="btn-text">📤
                                选择文件</span></label>
                    </div>

                    <!-- 交易类：单独分组美化 -->
                    <div class="trade-group">
                        <div class="trade-title">📦 滚撮交易数据上传</div>
                        <div class="trade-grid">
                            <!-- 省内滚撮 -->
                            <div class="upload-item">
                                <span class="item-title">日内滚撮数据</span>
                                <div class="trade-upload-row" style="flex-wrap: wrap; gap: 8px;">
                                    <!-- 额外的日期参数 -->
                                    <input type="date" v-model="rollingOpDate" class="trade-date-input"
                                        style="width: 130px;" />

                                    <!-- 文件上传组件 -->
                                    <div style="flex: 1; min-width: 180px;">
                                        <UploadFile v-model="rollingFiles" :drag="false" :multiple="true" text="选择滚撮文件"
                                            :disabled="!rollingOpDate" @change="uploadRollingData" />
                                    </div>
                                </div>
                            </div>
                            <!-- 长三角省间滚撮 -->
                            <div class="upload-item">
                                <span class="item-title">长三角省间交易</span>
                                <div class="trade-upload-row">
                                    <label class="upload-btn" style="width: 100%; margin-top: 4px;">
                                        <input type="file" accept=".xlsx,.xls" multiple class="hidden-input"
                                            @change="(e) => handleDataUpload(e, 'cross_province')" />
                                        <span class="btn-text">📤 选择文件上传</span>
                                    </label>
                                </div>
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
import { listPlantNodes, type PlantNode } from '@/api/modules/nodes'
import { request } from '@/api/request'
import SearchableSelect from '@/components/SearchableSelect.vue'
import UploadFile from '@/components/UploadFile.vue'
import { apiUrl } from '@/utils/apiBase'
const nodeOptions = ref<PlantNode[]>([])
const selectedNode = ref('')
const rollingOpDate = ref('') // 新增
const baseFiles = ref({ curve: false, holiday: false })
const dataFiles = ref<Record<string, boolean>>({})
const rollingFiles = ref<File[]>([])
onMounted(async () => {
    try {
        nodeOptions.value = await listPlantNodes()
    } catch {
        nodeOptions.value = []
    }
})
// 控制按钮透明度
function uploadStyle(dateVal: string) {
    return {
        opacity: dateVal ? 1 : 0.5,
        cursor: dateVal ? 'pointer' : 'not-allowed'
    }
}
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
    } catch (err) {
        alert('保存失败')
    }
}

async function handleDataUpload(e: Event, type: string) {
    const files = (e.target as HTMLInputElement).files
    if (!files || files.length === 0 || !selectedNode.value) return

    // 只保留滚撮的日期校验
    if (type === 'rolling' && !rollingOpDate.value) return alert('请先选择滚撮操作日期')

    const formData = new FormData()
    formData.append('node_name', selectedNode.value)
    formData.append('data_type', type)

    if (type === 'rolling') {
        formData.append('op_date', rollingOpDate.value)
    }

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
        dataFiles.value[type] = true
        alert(`${type} 上传成功`)
    } catch (err: any) {
        alert('上传失败：\n' + (err.message || '未知错误'))
    }
}
async function uploadRollingData(files: File[]) {
    if (files.length === 0 || !rollingOpDate.value) return

    const formData = new FormData()
    formData.append('node_name', selectedNode.value)
    formData.append('data_type', 'rolling')
    formData.append('op_date', rollingOpDate.value)

    // 将选中的文件列表全部塞进去
    files.forEach(f => formData.append('files', f))

    try {
        await request({ url: '/contract/config/node-data', method: 'post', data: formData })
        alert('滚撮数据上传成功')
        rollingFiles.value = [] // 清空组件里的文件
    } catch (e) {
        alert('上传失败')
    }
}
</script>

<style scoped>
/* 整体布局 */
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
}

.section-title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2d3d;
    margin-bottom: 24px;
    padding-bottom: 12px;
    border-bottom: 1px solid #ebeef5;
}

/* 表单公共样式 */
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
    transition: color 0.2s;
}

.link:hover {
    color: #1e4ca1;
    text-decoration: underline;
}

/* ====== 左侧：虚线上传框样式 ====== */
.hidden-input {
    display: none;
}

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

/* ====== 右侧：下拉框 ====== */
.select-wrapper {
    position: relative;
    width: 100%;
    max-width: 320px;
}

.custom-select {
    width: 100%;
    height: 36px;
    padding: 0 12px;
    font-size: 14px;
    color: #303133;
    background-color: #fff;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    outline: none;
    appearance: none;
    /* 隐藏原生箭头 */
    transition: border-color 0.2s;
    cursor: pointer;
}

.custom-select:focus,
.custom-select:hover {
    border-color: #2d6cdf;
}

/* 给下拉框加一个自定义箭头 */
.select-wrapper::after {
    content: '▾';
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #909399;
    pointer-events: none;
    font-size: 14px;
}

/* ====== 右侧：数据网格与按钮 ====== */
.data-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
    margin-top: 16px;
    padding-top: 24px;
    border-top: 1px dashed #ebeef5;
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

/* ====== 底部主按钮 ====== */
.btn-primary {
    margin-top: auto;
    height: 38px;
    background: #2d6cdf;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 2px 6px rgba(45, 108, 223, 0.2);
}

.btn-primary:hover {
    background: #2459b8;
    box-shadow: 0 4px 12px rgba(45, 108, 223, 0.3);
}

.btn-primary:active {
    transform: translateY(1px);
}

.trade-group {
    grid-column: 1 / -1;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
    margin-top: 10px;
}

.trade-title {
    font-size: 14px;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.trade-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.trade-upload-row {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 4px;
}

.trade-date-input {
    flex: 1;
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