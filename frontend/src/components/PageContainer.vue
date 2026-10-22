<template>
    <section class="page-container">
        <header v-if="title" class="page-header">
            <h2 class="page-title">{{ title }}</h2>
            <div class="page-extra">
                <slot name="extra" />
            </div>
        </header>

        <div class="page-body">
            <slot />
        </div>
    </section>
</template>

<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

<style scoped>
.page-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 16px;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    flex-wrap: wrap;
    /* ← 标题 + extra 整体可换行 */
}

.page-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    flex-shrink: 0;
}

.page-extra {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    flex-wrap: wrap;
    row-gap: 8px;
    min-width: 0;
    flex: 1;
    /* ← 新增：占满除标题外的宽度，方便第二行右对齐 */
}

.page-body {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

/* #extra 内统一按钮样式 */
:deep(.btn-upload) {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 30px;
    padding: 0 14px;
    border: 1px solid #2d6cdf;
    border-radius: 4px;
    background: #fff;
    color: #2d6cdf;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    white-space: nowrap;
}

:deep(.btn-upload:hover) {
    background: #2d6cdf;
    color: #fff;
}
</style>