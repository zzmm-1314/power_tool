<template>
    <Teleport to="body">
        <Transition name="fade">
            <div v-if="visible" class="mask" @click.self="close">
                <div class="modal">
                    <div class="modal-header">
                        <h3 class="modal-title">⚙ 天气参数配置</h3>
                        <p class="modal-subtitle">
                            以下参数仅对「本次预测」生效，不会修改系统默认值。
                        </p>
                    </div>

                    <div class="modal-body scroll-y">
                        <div v-for="group in GROUPS" :key="group.title" class="group">
                            <div class="group-title">{{ group.title }}</div>
                            <div class="group-body">
                                <div v-for="key in group.keys" :key="key" class="form-item">
                                    <label :title="key">{{ labelOf(key) }}</label>

                                    <!-- 布尔 -->
                                    <input v-if="typeof model[key] === 'boolean'" v-model="model[key]" type="checkbox"
                                        class="checkbox" />

                                    <!-- 枚举 -->
                                    <select v-else-if="ENUM_KEYS.includes(key)" v-model="model[key]" class="input">
                                        <option value="linear">linear（线性）</option>
                                        <option value="nonlinear">nonlinear（非线性）</option>
                                    </select>

                                    <select v-else-if="key === 'RADIATION_STRATEGY'" v-model="model[key]" class="input">
                                        <option value="single">single（单字段）</option>
                                        <option value="composite">composite（综合）</option>
                                    </select>

                                    <!-- 数值 -->
                                    <input v-else v-model.number="model[key]" type="number" step="0.001"
                                        class="input" />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="modal-footer">
                        <button class="btn ghost" :disabled="saving" @click="resetDefaults">
                            恢复默认
                        </button>
                        <button class="btn ghost" :disabled="saving" @click="close">
                            取消
                        </button>
                        <button class="btn primary" :disabled="saving" @click="apply">
                            应用配置
                        </button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { fetchWeatherConfigDefaults } from '@/api/modules/coefficient'

const props = defineProps<{
    modelValue: boolean
    /** 外部已有的配置（若存在则优先使用） */
    initial?: Record<string, any>
}>()

const emit = defineEmits<{
    (e: 'update:modelValue', v: boolean): void
    (e: 'confirm', value: Record<string, any>): void
}>()

const visible = ref(props.modelValue)
const saving = ref(false)
const defaults = ref<Record<string, any>>({})
const model = reactive<Record<string, any>>({})

const ENUM_KEYS = ['WEATHER_CORRECTION_MODE']

/** 分组展示，key 必须是 coefficient_config.py 中的 WEATHER_CONFIG_KEYS */
const GROUPS = [
    {
        title: '总开关 / 权重',
        keys: ['WEATHER_ENABLED', 'WEATHER_WEIGHT'],
    },
    {
        title: '基础偏移因子',
        keys: [
            'PV_OFFSET_FACTOR',
            'TEMP_OFFSET_FACTOR',
            'WIND_OFFSET_FACTOR',
            'TEMP_BASE',
            'WIND_BASE',
        ],
    },
    {
        title: '非线性模式',
        keys: [
            'WEATHER_CORRECTION_MODE',
            'PV_SIGMOID_SLOPE',
            'PV_SIGMOID_SHIFT',
            'TEMP_SIGMOID_SLOPE',
            'TEMP_SIGMOID_THRESHOLD',
            'WIND_TANH_SCALE',
            'WIND_TANH_SHIFT',
        ],
    },
    {
        title: '湿度 / 热指数',
        keys: ['HUMIDITY_THRESHOLD', 'HUMIDITY_AMP', 'HEAT_INDEX_MAX_OFFSET'],
    },
    {
        title: '辐射',
        keys: [
            'RADIATION_STRATEGY',
            'USE_DIRECT_RADIATION',
            'USE_DIFFUSE_RADIATION',
            'USE_DNI',
            'USE_SUNSHINE_DURATION',
            'USE_CLOUD_COVER',
            'DIRECT_WEIGHT',
            'DIFFUSE_WEIGHT',
            'RADIATION_MAX_CLEAR_SKY',
            'RADIATION_WEIGHT',
            'SUNSHINE_DURATION_MAX',
        ],
    },
    {
        title: '发电风险',
        keys: ['GEN_RISK_TEMP_THRESHOLD', 'GEN_RISK_PENALTY'],
    },
    {
        title: '极端天气',
        keys: [
            'EXTREME_WEATHER_ENABLED',
            'EXTREME_WIND_THRESHOLD',
            'EXTREME_TEMP_THRESHOLD',
            'EXTREME_WEATHER_OFFSET',
            'EXTREME_WIND_OFFSET',
            'EXTREME_TEMP_OFFSET',
        ],
    },
]

const LABELS: Record<string, string> = {
    WEATHER_ENABLED: '天气修正总开关',
    WEATHER_WEIGHT: '天气叠加权重',
    PV_OFFSET_FACTOR: '光伏偏移因子',
    TEMP_OFFSET_FACTOR: '温度偏移因子',
    WIND_OFFSET_FACTOR: '风速偏移因子',
    TEMP_BASE: '温度基准(℃)',
    WIND_BASE: '风速基准(km/h)',
    WEATHER_CORRECTION_MODE: '修正模式',
    PV_SIGMOID_SLOPE: '光伏 Sigmoid 斜率',
    PV_SIGMOID_SHIFT: '光伏 Sigmoid 偏移',
    TEMP_SIGMOID_SLOPE: '温度 Sigmoid 斜率',
    TEMP_SIGMOID_THRESHOLD: '温度转折点(℃)',
    WIND_TANH_SCALE: '风速 Tanh 缩放',
    WIND_TANH_SHIFT: '风速 Tanh 偏移',
    HUMIDITY_THRESHOLD: '湿度阈值(%)',
    HUMIDITY_AMP: '湿度热指数系数',
    HEAT_INDEX_MAX_OFFSET: '热指数上限(℃)',
    RADIATION_STRATEGY: '辐射策略',
    USE_DIRECT_RADIATION: '使用直接辐射',
    USE_DIFFUSE_RADIATION: '使用散射辐射',
    USE_DNI: '使用法向直射',
    USE_SUNSHINE_DURATION: '使用日照时长',
    USE_CLOUD_COVER: '使用云量',
    DIRECT_WEIGHT: '直射权重',
    DIFFUSE_WEIGHT: '散射权重',
    RADIATION_MAX_CLEAR_SKY: '晴空辐射上限(W/m²)',
    RADIATION_WEIGHT: '辐射综合权重',
    SUNSHINE_DURATION_MAX: '日照时长上限(s)',
    GEN_RISK_TEMP_THRESHOLD: '发电风险温度阈值(℃)',
    GEN_RISK_PENALTY: '发电风险惩罚系数',
    EXTREME_WEATHER_ENABLED: '极端天气开关',
    EXTREME_WIND_THRESHOLD: '极端风速阈值(km/h)',
    EXTREME_TEMP_THRESHOLD: '极端温度阈值(℃)',
    EXTREME_WEATHER_OFFSET: '极端天气统一偏移',
    EXTREME_WIND_OFFSET: '极端大风偏移',
    EXTREME_TEMP_OFFSET: '极端高温偏移',
}

function labelOf(key: string): string {
    return LABELS[key] || key
}

async function loadDefaults() {
    try {
        const res = await fetchWeatherConfigDefaults()
        defaults.value = res.defaults || {}
        if (props.initial && Object.keys(props.initial).length) {
            Object.assign(model, defaults.value, props.initial)
        } else {
            Object.assign(model, defaults.value)
        }
    } catch (e) {
        console.warn('加载天气配置默认值失败', e)
    }
}

function resetDefaults() {
    Object.assign(model, defaults.value)
}

function apply() {
    emit('confirm', { ...model })
    close()
}

function close() {
    visible.value = false
}

watch(
    () => props.modelValue,
    (v) => {
        visible.value = v
        if (v) loadDefaults()
    },
)
watch(visible, (v) => emit('update:modelValue', v))
</script>

<style scoped>
.mask {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}

.modal {
    width: 720px;
    max-width: 94vw;
    max-height: 88vh;
    display: flex;
    flex-direction: column;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
    overflow: hidden;
}

.modal-header {
    padding: 18px 24px 12px;
    border-bottom: 1px solid #f0f2f5;
}

.modal-title {
    margin: 0 0 4px;
    font-size: 16px;
    font-weight: 600;
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

.group {
    margin-bottom: 16px;
}

.group-title {
    font-size: 13px;
    font-weight: 600;
    color: #1f2d3d;
    padding: 4px 0 8px;
    border-bottom: 1px dashed #ebeef5;
    margin-bottom: 10px;
}

.group-body {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 20px;
}

.form-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.form-item>label {
    flex: 1;
    font-size: 12px;
    color: #606266;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.input {
    height: 28px;
    width: 120px;
    padding: 0 8px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 12px;
    outline: none;
}

.input:focus {
    border-color: #2d6cdf;
}

.checkbox {
    width: 16px;
    height: 16px;
    accent-color: #2d6cdf;
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

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>