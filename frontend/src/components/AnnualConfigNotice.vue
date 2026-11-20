<template>
    <div v-if="!hidden" :class="['notice-bar', level]">
        <span class="notice-icon">{{ icon }}</span>
        <div class="notice-body">
            <div class="notice-title">{{ title }}</div>
            <div class="notice-text">
                新年度的典型曲线与年度节假日需在 <b>1 月 1 日</b> 重新上传到数据库，
                否则本年度合约分解会沿用旧年度系数，导致电量与日期类型错位。
                当天更新完成前，请勿用「按输入电量分解」生成结算单。
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * 年度基础配置更新提醒。
 *
 * 12 月为「临近」高亮，1 月 1 日起 14 天内为「紧急」高亮，
 * 其余月份淡出为浅灰提示（仍可见，只是弱化）。
 */
const props = withDefaults(
    defineProps<{
        /** 用于判断月份，默认当前日期 */
        date?: Date | string | null
        /** 完全隐藏（如页面内已有其他位置提示） */
        hidden?: boolean
    }>(),
    { date: null, hidden: false }
)

const today = computed<Date>(() => {
    if (props.date instanceof Date) return props.date
    if (typeof props.date === 'string' && props.date.trim()) {
        const d = new Date(props.date)
        if (!Number.isNaN(d.getTime())) return d
    }
    return new Date()
})

const month = computed(() => today.value.getMonth() + 1)
const day = computed(() => today.value.getDate())

/** urgent = 1 月 1 日起 14 天内；near = 12 月；muted = 其他月份淡出 */
const level = computed<'urgent' | 'near' | 'muted'>(() => {
    if (month.value === 1) return day.value <= 14 ? 'urgent' : 'muted'
    if (month.value === 12) return 'near'
    return 'muted'
})

const icon = computed(() => {
    if (level.value === 'urgent') return '⚠️'
    if (level.value === 'near') return '📌'
    return '·'
})

const title = computed(() => {
    if (level.value === 'urgent') return '请先完成本年度基础配置更新'
    if (level.value === 'near') return '临近 1 月 1 日，请准备更新基础配置'
    return '每年 1 月 1 日请更新基础配置文件'
})
</script>

<style scoped>
.notice-bar {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 10px 12px;
    margin-bottom: 14px;
    border: 1px solid #faecd8;
    border-left: 3px solid #e6a23c;
    border-radius: 6px;
    background: #fdf6ec;
    transition: background 0.3s, border-color 0.3s, box-shadow 0.3s;
}

/* 临近：12 月，橙色提示 */
.notice-bar.near {
    border-color: #f3d19e;
    border-left-color: #e6a23c;
    background: #fdf6ec;
}

/* 紧急：1 月 1 日起 14 天内，红色高亮 */
.notice-bar.urgent {
    border-color: #fbc4c4;
    border-left-color: #f56c6c;
    background: #fef0f0;
    box-shadow: 0 1px 6px rgba(245, 108, 108, 0.12);
}

/* 平时：淡出为浅灰，不再抢注意力 */
.notice-bar.muted {
    border-color: #eef0f3;
    border-left-color: #dcdfe6;
    background: #fafafa;
}

.notice-icon {
    font-size: 15px;
    line-height: 20px;
    flex-shrink: 0;
}

.notice-bar.muted .notice-icon {
    color: #c0c4cc;
}

.notice-body {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.notice-title {
    font-size: 13px;
    font-weight: 600;
    color: #b88230;
}

.notice-bar.urgent .notice-title {
    color: #c45656;
}

.notice-bar.muted .notice-title {
    color: #909399;
    font-weight: 500;
}

.notice-text {
    font-size: 12px;
    line-height: 1.7;
    color: #8a6d3b;
}

.notice-bar.muted .notice-text {
    color: #b1b3b8;
}

.notice-bar.urgent .notice-text {
    color: #a15050;
}

.notice-text b {
    color: #e6a23c;
}

.notice-bar.muted .notice-text b {
    color: #b1b3b8;
    font-weight: 600;
}

.notice-bar.urgent .notice-text b {
    color: #f56c6c;
}
</style>