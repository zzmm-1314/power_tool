<template>
    <aside class="app-sidebar scroll-y" :class="{ collapsed }">
        <nav class="menu">
            <template v-for="(item, idx) in menus" :key="item.title">
                <!-- 无子菜单 -->
                <router-link v-if="!item.children" :to="item.path!" class="menu-item" active-class="active">
                    {{ item.title }}
                </router-link>

                <!-- 折叠框 -->
                <div v-else class="menu-group">
                    <div class="menu-item group-title" @click="toggle(idx)">
                        <span>{{ item.title }}</span>
                        <span class="arrow" :class="{ open: opened.includes(idx) }">▾</span>
                    </div>

                    <div v-show="opened.includes(idx)" class="submenu">
                        <router-link v-for="child in item.children" :key="child.path" :to="child.path"
                            class="menu-item sub-item" active-class="active">
                            {{ child.title }}
                        </router-link>
                    </div>
                </div>
            </template>
        </nav>
    </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface MenuChild {
    title: string
    path: string
}
interface MenuItem {
    title: string
    path?: string
    children?: MenuChild[]
}

defineProps<{ collapsed?: boolean }>()

const menus: MenuItem[] = [
    { title: '负荷分析', path: '/load-analysis' },
    {
        title: '日前电价',
        children: [
            { title: '统一结算点', path: '/day-ahead-price/unified' },
            { title: '电厂节点', path: '/day-ahead-price/plant' },
        ],
    },
    {
        title: '价差分析',
        children: [
            { title: '统一结算点', path: '/price-spread/unified' },
            { title: '电厂节点', path: '/price-spread/plant' },
        ],
    },
    {
        title: '中长期合约',
        children: [
            { title: '合约分解', path: '/contract/decomposition' },
            { title: '电厂合约仓位', path: '/contract/position' },
            { title: '滚撮收益模拟', path: '/contract/rolling-profit' },
            { title: '长三角省间交易收益模拟', path: '/contract/cross-province-profit' },
            { title: '合约配置', path: '/contract/config' },
        ],
    },
    {
        title: '结算单查询与下载',
        children: [
            { title: "电价对比", path: '/settlement/price-compare' },
            { title: '实际结算单更新', path: '/settlement/actual' },
        ],
    },
    // ⭐ 工具助手新增了原本的结算单更新子项及申报系数预测
    {
        title: '工具助手',
        children: [
            { title: '月报数据部分填充', path: '/monthly-report' },
            { title: '结算单 PDF 提取', path: '/monthly-extract' },
            { title: '文档逐字比对', path: '/tools/doc-compare' },
            { title: '模拟结算单更新', path: '/settlement/simulate' },
            { title: '申报系数预测', path: '/coefficient' },
        ],
    },
    { title: '滚撮分析', path: '/rolling' },
    { title: '统调电厂', path: '/unified-plants' },

]

/** 默认展开所有折叠框 */
const opened = ref<number[]>(menus.map((m, i) => (m.children ? i : -1)).filter((i) => i >= 0))

function toggle(idx: number) {
    const pos = opened.value.indexOf(idx)
    if (pos > -1) opened.value.splice(pos, 1)
    else opened.value.push(idx)
}
</script>

<style scoped>
.app-sidebar {
    width: 210px;
    /* 稍微加宽一点点 */
    background: #fff;
    border-right: 1px solid #ebeef5;
    transition: width 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    box-shadow: 1px 0 8px rgba(0, 0, 0, 0.02);
}

.app-sidebar.collapsed {
    width: 0;
    overflow: hidden;
    border-right: none;
}

.menu {
    padding: 12px 8px;
}

.menu-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 9px 14px;
    margin-bottom: 3px;
    color: #4a5568;
    font-size: 14px;
    text-decoration: none;
    cursor: pointer;
    border-radius: var(--radius-sm);
    transition: background 0.2s ease, color 0.2s ease;
}

.menu-item:hover {
    background: var(--bg-subtle);
    color: var(--text-1);
}

/* 统一激活态：左侧高亮竖条 + 浅色底（原先两段 .menu-item.active 相互覆盖，已合并） */
.menu-item.active {
    background: var(--primary-light);
    color: var(--primary);
    font-weight: 600;
    box-shadow: inset 3px 0 0 0 var(--primary);
}

.group-title {
    font-weight: 500;
    color: var(--text-2);
}

.arrow {
    font-size: 12px;
    color: var(--text-4);
    transition: transform 0.2s;
    transform: rotate(-90deg);
}

.arrow.open {
    transform: rotate(0deg);
}

.submenu {
    margin-top: -3px;
    margin-bottom: 8px;
}

.sub-item {
    padding-left: 32px;
    font-size: 13px;
    color: var(--text-3);
}

.sub-item.active {
    color: var(--primary);
    font-weight: 500;
    background: transparent;
    box-shadow: inset 2px 0 0 0 var(--primary);
}
</style>