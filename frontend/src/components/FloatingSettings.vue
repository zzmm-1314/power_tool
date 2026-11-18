<template>
    <div class="floating-settings" :style="{ left: pos.x + 'px', top: pos.y + 'px' }">
        <button class="settings-btn" :class="{ dragging }" title="节点配置（可拖动）" @mousedown="onDragStart" @click="onClick">
            ⚙️
        </button>
        <GlobalSettingsModal v-model="show" />
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import GlobalSettingsModal from '@/components/GlobalSettingsModal.vue'

const STORAGE_KEY = 'floating-settings-pos'
const BUTTON_SIZE = 44

const show = ref(false)
const dragging = ref(false)
const pos = reactive({ x: 0, y: 0 })

let startX = 0
let startY = 0
let startPosX = 0
let startPosY = 0
let moved = false

function clampX(x: number) {
    return Math.max(0, Math.min(window.innerWidth - BUTTON_SIZE, x))
}
function clampY(y: number) {
    return Math.max(0, Math.min(window.innerHeight - BUTTON_SIZE, y))
}

function initPos() {
    const defX = window.innerWidth - BUTTON_SIZE - 24
    const defY = 24
    try {
        const saved = localStorage.getItem(STORAGE_KEY)
        if (saved) {
            const p = JSON.parse(saved)
            if (typeof p.x === 'number' && typeof p.y === 'number') {
                pos.x = clampX(p.x)
                pos.y = clampY(p.y)
                return
            }
        }
    } catch {
        // ignore
    }
    pos.x = defX
    pos.y = defY
}

function onDragStart(e: MouseEvent) {
    dragging.value = true
    moved = false
    startX = e.clientX
    startY = e.clientY
    startPosX = pos.x
    startPosY = pos.y
    document.addEventListener('mousemove', onDragMove)
    document.addEventListener('mouseup', onDragEnd)
}

function onDragMove(e: MouseEvent) {
    if (!dragging.value) return
    const dx = e.clientX - startX
    const dy = e.clientY - startY
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) moved = true
    pos.x = clampX(startPosX + dx)
    pos.y = clampY(startPosY + dy)
}

function onDragEnd() {
    dragging.value = false
    document.removeEventListener('mousemove', onDragMove)
    document.removeEventListener('mouseup', onDragEnd)
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ x: pos.x, y: pos.y }))
    } catch {
        // ignore
    }
}

function onClick() {
    if (moved) return // 拖动不触发点击
    show.value = true
}

function onResize() {
    pos.x = clampX(pos.x)
    pos.y = clampY(pos.y)
}

onMounted(() => {
    initPos()
    window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
    window.removeEventListener('resize', onResize)
    document.removeEventListener('mousemove', onDragMove)
    document.removeEventListener('mouseup', onDragEnd)
})
</script>

<style scoped>
.floating-settings {
    position: fixed;
    z-index: 9998;
    user-select: none;
}

.settings-btn {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: none;
    background: #1f2d3d;
    color: #fff;
    font-size: 20px;
    cursor: grab;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
    transition: transform 0.15s, box-shadow 0.15s, background 0.2s;
}

.settings-btn:hover {
    background: #2d6cdf;
    transform: scale(1.05);
    box-shadow: 0 6px 20px rgba(45, 108, 223, 0.4);
}

.settings-btn:active,
.settings-btn.dragging {
    cursor: grabbing;
    transform: scale(0.98);
}
</style>