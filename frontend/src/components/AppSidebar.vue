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
        title: '结算单更新',
        children: [
            { title: '实际结算单更新', path: '/settlement/actual' },
            { title: '椒江模拟结算单更新', path: '/settlement/jiaojiang' },
            { title: '现代模拟结算单更新', path: '/settlement/xiandai' },
        ],
    },
    { title: '申报系数预测', path: '/coefficient' },
    { title: '滚撮分析', path: '/rolling' },
    { title: '月报数据部分填充', path: '/monthly-report' },
    { title: '统调电厂', path: '/unified-plants' },
    { title: '节点编辑', path: '/node-edit' },
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
    width: 200px;
    background: #fff;
    border-right: 1px solid #e4e7ed;
    transition: width 0.2s;
}

.app-sidebar.collapsed {
    width: 0;
    overflow: hidden;
    border-right: none;
}

.menu {
    padding: 8px 0;
}

.menu-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 18px;
    color: #303133;
    font-size: 14px;
    text-decoration: none;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
}

.menu-item:hover {
    background: #f0f5ff;
    color: #2d6cdf;
}

.menu-item.active {
    background: #ecf3ff;
    color: #2d6cdf;
    font-weight: 500;
    border-right: 3px solid #2d6cdf;
}

.group-title {
    font-weight: 500;
}

.arrow {
    font-size: 12px;
    transition: transform 0.2s;
    transform: rotate(-90deg);
}

.arrow.open {
    transform: rotate(0deg);
}

.submenu {
    background: #fafbfc;
}

.sub-item {
    padding-left: 34px;
    font-size: 13px;
    color: #5a6472;
}
</style>