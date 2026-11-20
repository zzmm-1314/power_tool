<template>
    <aside class="app-sidebar" :class="{ collapsed }">
        <!-- ===== 折叠态：图标书签 ===== -->
        <div v-if="collapsed" class="bookmarks">
            <div v-for="(item, idx) in menus" :key="item.title" class="bookmark" :title="item.title"
                @click="expandTo(idx)">
                <span class="bookmark-icon">{{ item.icon }}</span>
            </div>
        </div>

        <!-- ===== 展开态：完整菜单 ===== -->
        <template v-else>
            <div class="sidebar-header">
                <span class="logo">⚡</span>
                <span class="sidebar-title">电力工具助手</span>
                <button class="collapse-btn" title="收起侧栏" @click="appStore.toggleSidebar()">
                    ⏴
                </button>
            </div>

            <nav class="menu scroll-y">
                <template v-for="(item, idx) in menus" :key="item.title">
                    <!-- 无子菜单 -->
                    <router-link v-if="!item.children" :to="item.path!" class="menu-item" active-class="active">
                        <span class="menu-icon">{{ item.icon }}</span>
                        <span class="menu-text">{{ item.title }}</span>
                    </router-link>

                    <!-- 分组菜单 -->
                    <div v-else class="menu-group">
                        <div class="menu-item group-title" @click="toggle(idx)">
                            <span class="menu-icon">{{ item.icon }}</span>
                            <span class="menu-text">{{ item.title }}</span>
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
        </template>
    </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'

interface MenuChild {
    title: string
    path: string
}
interface MenuItem {
    title: string
    icon: string
    path?: string
    children?: MenuChild[]
}

const appStore = useAppStore()
const collapsed = computed(() => appStore.sidebarCollapsed)

const menus: MenuItem[] = [
    { title: '负荷分析', icon: '📊', path: '/load-analysis' },
    {
        title: '日前电价',
        icon: '💰',
        children: [
            { title: '统一结算点', path: '/day-ahead-price/unified' },
            { title: '电厂节点', path: '/day-ahead-price/plant' },
        ],
    },
    {
        title: '价差分析',
        icon: '📈',
        children: [
            { title: '统一结算点', path: '/price-spread/unified' },
            { title: '电厂节点', path: '/price-spread/plant' },
        ],
    },
    {
        title: '中长期合约',
        icon: '📋',
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
        icon: '🧾',
        children: [
            { title: '电价对比', path: '/settlement/price-compare' },
            { title: '实际结算单更新', path: '/settlement/actual' },
        ],
    },
    {
        title: '工具助手',
        icon: '🛠️',
        children: [
            { title: '月报数据部分填充', path: '/tools/monthly-report' },   // ← 原 /monthly-report
            { title: '结算单 PDF 提取', path: '/tools/monthly-extract' },   // ← 原 /monthly-extract
            { title: '文档逐字比对', path: '/tools/doc-compare' },
            { title: '模拟结算单更新', path: '/settlement/simulate' },
            { title: '申报系数预测', path: '/tools/coefficient' },          // ← 原 /coefficient
        ],
    },
    { title: '滚撮分析', icon: '🔄', path: '/rolling' },
    { title: '统调电厂', icon: '🏭', path: '/unified-plants' },
]

/** 默认展开所有分组 */
const opened = ref<number[]>(
    menus.map((m, i) => (m.children ? i : -1)).filter((i) => i >= 0),
)

function toggle(idx: number) {
    const pos = opened.value.indexOf(idx)
    if (pos > -1) opened.value.splice(pos, 1)
    else opened.value.push(idx)
}

/** 点击书签：展开侧边栏；若为分组，确保该组展开 */
function expandTo(idx: number) {
    appStore.toggleSidebar()
    const item = menus[idx]
    if (item.children && !opened.value.includes(idx)) {
        opened.value.push(idx)
    }
}
</script>

<style scoped>
.app-sidebar {
    width: 210px;
    flex-shrink: 0;
    background: #fff;
    border-right: 1px solid #ebeef5;
    box-shadow: 1px 0 8px rgba(0, 0, 0, 0.02);
    display: flex;
    flex-direction: column;
    transition: width 0.28s cubic-bezier(0.25, 0.8, 0.25, 1);
    overflow: hidden;
}

.app-sidebar.collapsed {
    width: 56px;
    overflow: hidden;
}

/* ===== 展开态头部 ===== */
.sidebar-header {
    display: flex;
    align-items: center;
    gap: 8px;
    height: 52px;
    padding: 0 10px 0 16px;
    border-bottom: 1px solid #f0f2f5;
    flex-shrink: 0;
}

.logo {
    font-size: 18px;
}

.sidebar-title {
    flex: 1;
    font-size: 14px;
    font-weight: 600;
    color: #1f2d3d;
    letter-spacing: 0.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.collapse-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: #909399;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.2s, color 0.2s;
}

.collapse-btn:hover {
    background: #ecf3ff;
    color: #2d6cdf;
}

/* ===== 展开态菜单 ===== */
.menu {
    flex: 1;
    padding: 12px 8px;
    overflow-y: auto;
    overflow-x: hidden;
}

.menu-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 14px;
    margin-bottom: 3px;
    color: #4a5568;
    font-size: 14px;
    text-decoration: none;
    cursor: pointer;
    border-radius: 6px;
    transition: background 0.2s ease, color 0.2s ease;
}

.menu-item:hover {
    background: #f0f2f5;
    color: #1f2d3d;
}

.menu-item.active {
    background: #ecf3ff;
    color: #2d6cdf;
    font-weight: 600;
    box-shadow: inset 3px 0 0 0 #2d6cdf;
}

.menu-icon {
    flex-shrink: 0;
    width: 18px;
    text-align: center;
    font-size: 15px;
    line-height: 1;
}

.menu-text {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.group-title {
    font-weight: 500;
    color: #303133;
}

.arrow {
    flex-shrink: 0;
    font-size: 12px;
    color: #909399;
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
    padding-left: 40px;
    font-size: 13px;
    color: #606266;
}

.sub-item.active {
    color: #2d6cdf;
    font-weight: 500;
    background: transparent;
    box-shadow: inset 2px 0 0 0 #2d6cdf;
}

/* ===== 折叠态：图标书签 ===== */
.bookmarks {
    height: 100%;
    padding: 10px 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: none;
}

.bookmarks::-webkit-scrollbar {
    display: none;
}

.bookmark {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f5f7fa;
    color: #4a5568;
    border-left: 3px solid transparent;
    border-radius: 0 8px 8px 0;
    cursor: pointer;
    user-select: none;
    transition: background 0.2s, border-color 0.2s, transform 0.15s;
}

.bookmark:hover {
    background: #ecf3ff;
    border-left-color: #2d6cdf;
    transform: translateX(2px);
}

.bookmark-icon {
    font-size: 18px;
    line-height: 1;
}
</style>