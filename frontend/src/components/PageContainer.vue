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
    gap: 16px;
    /* 间距稍微拉大，更有呼吸感 */
    padding-bottom: 20px;
}

.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 16px 20px;
    /* 增加内边距 */
    background: #fff;
    border-radius: 8px;
    /* 从 6px 提升到 8px */
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
    /* 更柔和的阴影 */
    flex-wrap: wrap;
}

.page-title {
    margin: 0;
    font-size: 17px;
    /* 字体稍微加大 */
    font-weight: 600;
    color: #1f2d3d;
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
    gap: 16px;
}

:deep(.btn-upload:hover) {
    background: #2d6cdf;
    color: #fff;
}
</style>