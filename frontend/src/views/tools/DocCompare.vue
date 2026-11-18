<template>
    <PageContainer title="文档逐字比对">
        <div class="compare-wrap">
            <!-- 顶部提示 -->
            <div class="hint-bar">
                支持 TXT / MD / DOCX / PDF 格式，系统会<b>逐字比对</b>，并自动忽略<b>语气词、标点符号、空白字符</b>等停用词，仅高亮真正的新增 / 修改内容。
            </div>

            <!-- 上传区 -->
            <div class="upload-grid">
                <div class="card">
                    <div class="panel-head">
                        <div class="title"><span class="dot old"></span>旧版文件（原文）</div>
                        <div class="counter">{{ fmtCount(textOld) }}</div>
                    </div>
                    <div class="drop" :class="{ over: dropOldOver, loading: dropOldLoading }"
                        @click="triggerFile('old')" @dragover.prevent="dropOldOver = true"
                        @dragleave.prevent="dropOldOver = false" @drop.prevent="handleDrop($event, 'old')">
                        <template v-if="dropOldLoading">正在解析…</template>
                        <template v-else-if="fileOldName">已载入：{{ fileOldName }}<small>点击可重新选择文件</small></template>
                        <template v-else>拖拽文件到此处，或点击选择<small>支持 .txt / .md / .docx / .pdf</small></template>
                    </div>
                    <input type="file" ref="fileInputOld" hidden accept=".txt,.md,.csv,.json,.docx,.pdf,.log"
                        @change="handleFileChange($event, 'old')" />
                    <textarea v-model="textOld" placeholder="也可以直接在这里粘贴旧版内容…"></textarea>
                </div>

                <div class="card">
                    <div class="panel-head">
                        <div class="title"><span class="dot new"></span>新版文件（修改后）</div>
                        <div class="counter">{{ fmtCount(textNew) }}</div>
                    </div>
                    <div class="drop" :class="{ over: dropNewOver, loading: dropNewLoading }"
                        @click="triggerFile('new')" @dragover.prevent="dropNewOver = true"
                        @dragleave.prevent="dropNewOver = false" @drop.prevent="handleDrop($event, 'new')">
                        <template v-if="dropNewLoading">正在解析…</template>
                        <template v-else-if="fileNewName">已载入：{{ fileNewName }}<small>点击可重新选择文件</small></template>
                        <template v-else>拖拽文件到此处，或点击选择<small>支持 .txt / .md / .docx / .pdf</small></template>
                    </div>
                    <input type="file" ref="fileInputNew" hidden accept=".txt,.md,.csv,.json,.docx,.pdf,.log"
                        @change="handleFileChange($event, 'new')" />
                    <textarea v-model="textNew" placeholder="也可以直接在这里粘贴新版内容…"></textarea>
                </div>
            </div>

            <!-- 规则配置 -->
            <div class="card options">
                <div class="opt-title">比对规则（被忽略的内容不参与差异判定）</div>
                <div class="opt-row">
                    <label class="chk"><input type="checkbox" v-model="opts.punct">忽略标点符号</label>
                    <label class="chk"><input type="checkbox" v-model="opts.modal">忽略语气词（啊/呀/吧/呢/吗…）</label>
                    <label class="chk"><input type="checkbox" v-model="opts.space">忽略空白（空格/换行/制表符）</label>
                    <label class="chk"><input type="checkbox" v-model="opts.particle">忽略常见虚词（的/了/着/过…）</label>
                </div>
                <div class="custom-stop">
                    <span>自定义停用词：</span>
                    <input type="text" v-model="opts.customStop" placeholder="输入需要额外忽略的字符，例如：嗯 呃 这个 那个（可留空）">
                </div>
            </div>

            <!-- 按钮组 -->
            <div class="actions">
                <button class="btn primary" :disabled="running" @click="runCompare">
                    {{ running ? '比对中…' : '开始比对' }}
                </button>
                <button class="btn ghost" :disabled="running" @click="loadDemo">加载示例</button>
                <button class="btn ghost" :disabled="running" @click="swapText">交换两版</button>
                <button class="btn ghost" :disabled="running" @click="clearAll">清空</button>
            </div>

            <!-- 比对结果 -->
            <div class="result" v-if="hasResult">
                <div v-if="warnHtml" v-html="warnHtml"></div>

                <div class="stats" v-html="statsHtml"></div>

                <div class="diff-grid">
                    <!-- 左侧文档 -->
                    <div class="card">
                        <div class="diff-head"><span>旧版（原文）</span><span>{{ countOld }} 个有效字</span></div>
                        <div class="pane-wrapper">
                            <div class="diff-body" ref="leftPane" v-html="renderDoc(oldChars, marksA)"
                                @scroll="onScroll($event, 'left')"></div>
                            <!-- 独立翻页器 -->
                            <div class="pager">
                                <button class="btn ghost small" :disabled="leftPageInfo.page <= 1"
                                    @click="turnPage('left', -1)">
                                    ⬅ 上一页
                                </button>
                                <span class="page-text">第 {{ leftPageInfo.page }} / {{ leftPageInfo.total }} 页</span>
                                <button class="btn ghost small" :disabled="leftPageInfo.page >= leftPageInfo.total"
                                    @click="turnPage('left', 1)">
                                    下一页 ➡
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- 右侧文档 -->
                    <div class="card">
                        <div class="diff-head"><span>新版（修改后）</span><span>{{ countNew }} 个有效字</span></div>
                        <div class="pane-wrapper">
                            <div class="diff-body" ref="rightPane" v-html="renderDoc(newChars, marksB)"
                                @scroll="onScroll($event, 'right')"></div>
                            <!-- 独立翻页器 -->
                            <div class="pager">
                                <button class="btn ghost small" :disabled="rightPageInfo.page <= 1"
                                    @click="turnPage('right', -1)">
                                    ⬅ 上一页
                                </button>
                                <span class="page-text">第 {{ rightPageInfo.page }} / {{ rightPageInfo.total }} 页</span>
                                <button class="btn ghost small" :disabled="rightPageInfo.page >= rightPageInfo.total"
                                    @click="turnPage('right', 1)">
                                    下一页 ➡
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="legend" v-html="legendHtml"></div>
            </div>
            <div class="empty" v-else-if="!running">尚未比对，请上传或粘贴两版内容后点击「开始比对」</div>
            <div class="empty" v-else>正在计算差异，请稍候…（大文档可能需要几秒）</div>
        </div>
    </PageContainer>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import PageContainer from '@/components/PageContainer.vue'
import { readAnyFile } from '@/utils/docParser'

// 停用词
const STOP_PUNCT = new Set(['，', '。', '！', '？', '；', '：', '、', '“', '”', '‘', '’', '（', '）', '〔', '〕', '【', '】', '《', '》', '〈', '〉', '「', '」', '『', '』', '…', '—', '～', '·', '﹏', '　', '•', '§', '¶', ',', '.', '!', '?', ';', ':', '"', "'", '(', ')', '[', ']', '{', '}', '<', '>', '|', '/', '\\', '@', '#', '$', '%', '^', '&', '*', '_', '+', '=', '~', '`', '-', '\u200b'])
const STOP_MODAL = new Set(Array.from('啊呀吧呢吗嘛哦哈嗯唉哎喂哇呗啦喽哟咯喔噢嘿哼呃呸咦嘘嘞呐喏吖唷嗨咧啵嘢'))
const STOP_PARTICLE = new Set(Array.from('的了着过地得之所而则乃也乎兮其焉哉矣耳尔'))

const textOld = ref('')
const textNew = ref('')
const fileOldName = ref('')
const fileNewName = ref('')
const running = ref(false)

const dropOldOver = ref(false)
const dropNewOver = ref(false)
const dropOldLoading = ref(false)
const dropNewLoading = ref(false)

const fileInputOld = ref<HTMLInputElement | null>(null)
const fileInputNew = ref<HTMLInputElement | null>(null)

const opts = reactive({
    punct: true,
    modal: true,
    space: true,
    particle: false,
    customStop: ''
})

const hasResult = ref(false)
const leftPane = ref<HTMLElement | null>(null)
const rightPane = ref<HTMLElement | null>(null)

const oldChars = ref<string[]>([])
const newChars = ref<string[]>([])
const marksA = ref<any[]>([])
const marksB = ref<any[]>([])
const statsHtml = ref('')
const warnHtml = ref('')
const legendHtml = ref('')
const countOld = ref(0)
const countNew = ref(0)

// ===== 独立的翻页信息 =====
const leftPageInfo = reactive({ page: 1, total: 1 })
const rightPageInfo = reactive({ page: 1, total: 1 })

const fmtCount = (text: string) => text.length.toLocaleString() + ' 字'

function triggerFile(type: 'old' | 'new') {
    if (type === 'old') fileInputOld.value?.click()
    else fileInputNew.value?.click()
}

function swapText() {
    const tmp = textOld.value
    textOld.value = textNew.value
    textNew.value = tmp
    const tmpName = fileOldName.value
    fileOldName.value = fileNewName.value
    fileNewName.value = tmpName
}

function clearAll() {
    textOld.value = ''
    textNew.value = ''
    fileOldName.value = ''
    fileNewName.value = ''
    hasResult.value = false
}

function loadDemo() {
    textOld.value = `人工智能技术在最近几年取得了显著的进步。深度学习模型在图像识别、自然语言处理等领域表现优异。\n很多公司已经开始把人工智能应用到实际业务中，比如说客服机器人、智能推荐系统等等。\n不过，人工智能的发展也带来了一些问题，比如数据隐私、算法偏见等等，这些问题需要引起重视啊。`
    textNew.value = `人工智能技术在最近几年取得了令人瞩目的突破。大规模预训练模型在图像识别、自然语言处理等核心领域表现优异。\n越来越多的企业已经将人工智能深度应用到实际业务场景中，例如智能客服、个性化推荐系统等。\n然而，人工智能的快速发展也带来了一系列挑战，比如数据隐私保护、算法公平性等问题，亟需引起高度重视呢。`
    runCompare()
}

async function uploadAndExtract(file: File, type: 'old' | 'new') {
    const isOld = type === 'old'
    if (isOld) { dropOldLoading.value = true; fileOldName.value = '' }
    else { dropNewLoading.value = true; fileNewName.value = '' }

    try {
        const text = await readAnyFile(file, (msg) => { })
        if (isOld) {
            textOld.value = text
            fileOldName.value = file.name
        } else {
            textNew.value = text
            fileNewName.value = file.name
        }
    } catch (e) {
        alert((e as Error).message || '文件解析失败')
    } finally {
        if (isOld) dropOldLoading.value = false
        else dropNewLoading.value = false
    }
}

function handleFileChange(e: Event, type: 'old' | 'new') {
    const target = e.target as HTMLInputElement
    const f = target.files?.[0]
    if (f) uploadAndExtract(f, type)
    target.value = ''
}

function handleDrop(e: DragEvent, type: 'old' | 'new') {
    if (type === 'old') dropOldOver.value = false
    else dropNewOver.value = false
    const f = e.dataTransfer?.files?.[0]
    if (f) uploadAndExtract(f, type)
}

// ================= 翻页逻辑 =================
function onScroll(e: Event, side: 'left' | 'right') {
    const el = e.target as HTMLElement
    const pageHeight = el.clientHeight
    if (pageHeight <= 0) return

    // 计算总页数（防止最后无法整除的问题，适当留余量）
    const total = Math.max(1, Math.ceil(el.scrollHeight / pageHeight))
    // 计算当前页码
    const page = Math.round(el.scrollTop / pageHeight) + 1

    if (side === 'left') {
        leftPageInfo.total = total
        leftPageInfo.page = Math.min(page, total)
    } else {
        rightPageInfo.total = total
        rightPageInfo.page = Math.min(page, total)
    }
}

function turnPage(side: 'left' | 'right', dir: number) {
    const el = side === 'left' ? leftPane.value : rightPane.value
    if (!el) return
    const pageHeight = el.clientHeight
    if (pageHeight <= 0) return

    const targetTop = el.scrollTop + (dir * pageHeight)
    el.scrollTo({ top: targetTop, behavior: 'smooth' })
}

// ================= 算法核心区域 =================
let diffTimedOut = false
const DIFF_TIME_LIMIT = 12000

function lcsDiff(A: any[], aLo: number, aHi: number, B: any[], bLo: number, bHi: number, out: any[]) {
    const n = aHi - aLo, m = bHi - bLo;
    const W = m + 1;
    const dp = new Int32Array((n + 1) * W);

    for (let i = n - 1; i >= 0; i--) {
        const row = i * W, nextRow = (i + 1) * W;
        for (let j = m - 1; j >= 0; j--) {
            if (A[aLo + i] === B[bLo + j]) dp[row + j] = dp[nextRow + j + 1] + 1;
            else dp[row + j] = dp[nextRow + j] >= dp[row + j + 1] ? dp[nextRow + j] : dp[row + j + 1];
        }
    }

    let i = 0, j = 0;
    while (i < n && j < m) {
        if (A[aLo + i] === B[bLo + j]) { out.push({ op: 'eq', ai: aLo + i, bj: bLo + j }); i++; j++; }
        else if (dp[(i + 1) * W + j] >= dp[i * W + j + 1]) { out.push({ op: 'del', ai: aLo + i }); i++; }
        else { out.push({ op: 'ins', bj: bLo + j }); j++; }
    }
    while (i < n) { out.push({ op: 'del', ai: aLo + i }); i++; }
    while (j < m) { out.push({ op: 'ins', bj: bLo + j }); j++; }
}

function bisect(A: any[], aLo: number, aHi: number, B: any[], bLo: number, bHi: number, deadline: number) {
    const N = aHi - aLo, M = bHi - bLo;
    const maxD = Math.ceil((N + M) / 2) + 1;
    const vOffset = maxD;
    const vLen = 2 * maxD + 3;
    const v1 = new Int32Array(vLen).fill(-1);
    const v2 = new Int32Array(vLen).fill(-1);
    v1[vOffset + 1] = 0;
    v2[vOffset + 1] = 0;

    const delta = N - M;
    const front = (delta % 2 !== 0);
    let k1start = 0, k1end = 0, k2start = 0, k2end = 0;

    for (let d = 0; d < maxD; d++) {
        if ((d & 31) === 0 && Date.now() > deadline) return null;

        for (let k1 = -d + k1start; k1 <= d - k1end; k1 += 2) {
            const k1o = vOffset + k1;
            let x1;
            if (k1 === -d || (k1 !== d && v1[k1o - 1] < v1[k1o + 1])) x1 = v1[k1o + 1];
            else x1 = v1[k1o - 1] + 1;
            let y1 = x1 - k1;
            while (x1 < N && y1 < M && A[aLo + x1] === B[bLo + y1]) { x1++; y1++; }
            v1[k1o] = x1;

            if (x1 > N) k1end += 2;
            else if (y1 > M) k1start += 2;
            else if (front) {
                const k2o = vOffset + delta - k1;
                if (k2o >= 0 && k2o < vLen && v2[k2o] !== -1) {
                    const x2 = N - v2[k2o];
                    if (x1 >= x2) return { x: aLo + x1, y: bLo + y1 };
                }
            }
        }

        for (let k2 = -d + k2start; k2 <= d - k2end; k2 += 2) {
            const k2o = vOffset + k2;
            let x2;
            if (k2 === -d || (k2 !== d && v2[k2o - 1] < v2[k2o + 1])) x2 = v2[k2o + 1];
            else x2 = v2[k2o - 1] + 1;
            let y2 = x2 - k2;
            while (x2 < N && y2 < M && A[aHi - 1 - x2] === B[bHi - 1 - y2]) { x2++; y2++; }
            v2[k2o] = x2;

            if (x2 > N) k2end += 2;
            else if (y2 > M) k2start += 2;
            else if (!front) {
                const k1o = vOffset + delta - k2;
                if (k1o >= 0 && k1o < vLen && v1[k1o] !== -1) {
                    const x1 = v1[k1o];
                    const y1 = x1 - (k1o - vOffset);
                    const x2r = N - x2;
                    if (x1 >= x2r) return { x: aLo + x1, y: bLo + y1 };
                }
            }
        }
    }
    return null;
}

function diffCharsRange(A: any[], aLo: number, aHi: number, B: any[], bLo: number, bHi: number, out: any[], deadline: number, depth: number) {
    while (aLo < aHi && bLo < bHi && A[aLo] === B[bLo]) {
        out.push({ op: 'eq', ai: aLo, bj: bLo });
        aLo++; bLo++;
    }
    let sA = aHi, sB = bHi;
    while (sA > aLo && sB > bLo && A[sA - 1] === B[sB - 1]) { sA--; sB--; }

    if (aLo === sA) {
        for (let j = bLo; j < sB; j++) out.push({ op: 'ins', bj: j });
    } else if (bLo === sB) {
        for (let i = aLo; i < sA; i++) out.push({ op: 'del', ai: i });
    } else {
        const n = sA - aLo, m = sB - bLo;
        if (n <= 200 && m <= 200) {
            lcsDiff(A, aLo, sA, B, bLo, sB, out);
        } else if (depth > 120) {
            diffTimedOut = true;
            for (let i = aLo; i < sA; i++) out.push({ op: 'del', ai: i });
            for (let j = bLo; j < sB; j++) out.push({ op: 'ins', bj: j });
        } else {
            const sp = bisect(A, aLo, sA, B, bLo, sB, deadline);
            if (sp && (sp.x > aLo || sp.y > bLo)) {
                diffCharsRange(A, aLo, sp.x, B, bLo, sp.y, out, deadline, depth + 1);
                diffCharsRange(A, sp.x, sA, B, sp.y, sB, out, deadline, depth + 1);
            } else {
                diffTimedOut = true;
                for (let i = aLo; i < sA; i++) out.push({ op: 'del', ai: i });
                for (let j = bLo; j < sB; j++) out.push({ op: 'ins', bj: j });
            }
        }
    }
    while (sA < aHi) { out.push({ op: 'eq', ai: sA, bj: sB }); sA++; sB++; }
}

function computeDiff(A: any[], B: any[], deadline: number) {
    diffTimedOut = false;
    const out: any[] = [];
    diffCharsRange(A, 0, A.length, B, 0, B.length, out, deadline, 0);
    return out;
}

function esc(s: string) {
    return s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c] as string))
}

function renderDoc(chars: string[], marks: any[]) {
    const parts: string[] = []
    let i = 0
    while (i < chars.length) {
        const m = marks[i]
        let j = i + 1
        while (j < chars.length && marks[j]?.type === m.type) {
            j++
        }

        const chunk = esc(chars.slice(i, j).join(''))
        if (m.type === 'same') {
            parts.push(chunk)
        } else {
            parts.push(`<span class="hl ${m.type}">${chunk}</span>`)
        }
        i = j
    }
    return parts.join('')
}

async function runCompare() {
    if (!textOld.value.trim() && !textNew.value.trim()) return alert('请先上传或输入两版内容')

    running.value = true
    hasResult.value = false

    await new Promise(r => setTimeout(r, 50))
    const t0 = performance.now()

    try {
        const stopSet = new Set<string>()
        if (opts.punct) STOP_PUNCT.forEach(c => stopSet.add(c))
        if (opts.modal) STOP_MODAL.forEach(c => stopSet.add(c))
        if (opts.particle) STOP_PARTICLE.forEach(c => stopSet.add(c))
        if (opts.customStop) for (const ch of opts.customStop) { if (!/\s/.test(ch)) stopSet.add(ch) }
        const ignoreSpace = opts.space

        const prepare = (text: string) => {
            const chars = Array.from(text.replace(/\r\n?/g, '\n'))
            const keep: number[] = []
            for (let i = 0; i < chars.length; i++) {
                const ch = chars[i]
                let ignored = false
                if (ignoreSpace && /\s/.test(ch)) ignored = true
                else if (stopSet.has(ch)) ignored = true
                if (!ignored) keep.push(i)
            }
            return { chars, keep }
        }

        const A = prepare(textOld.value)
        const B = prepare(textNew.value)

        oldChars.value = A.chars
        newChars.value = B.chars
        countOld.value = A.keep.length
        countNew.value = B.keep.length

        const a = A.keep.map(i => A.chars[i])
        const b = B.keep.map(i => B.chars[i])

        const deadline = Date.now() + DIFF_TIME_LIMIT
        const ops = computeDiff(a, b, deadline)

        const mA: any[] = new Array(A.chars.length).fill({ type: 'same' })
        const mB: any[] = new Array(B.chars.length).fill({ type: 'same' })

        let eqCount = 0, delCount = 0, insCount = 0

        for (const op of ops) {
            if (op.op === 'eq') {
                eqCount++
            } else if (op.op === 'del') {
                mA[A.keep[op.ai]] = { type: 'del' }
                delCount++
            } else {
                mB[B.keep[op.bj]] = { type: 'ins' }
                insCount++
            }
        }

        marksA.value = mA
        marksB.value = mB

        const elapsed = Math.round(performance.now() - t0)
        const denom = a.length + b.length
        const sim = denom === 0 ? 100 : (2 * eqCount / denom * 100)

        warnHtml.value = diffTimedOut ? `<div class="warn">⚠ 比对在 ${DIFF_TIME_LIMIT / 1000} 秒内未收敛，部分区块已按整块标记。</div>` : ''

        statsHtml.value = `
            <div class="stat ins"><span>新增</span><b>${insCount}</b><span>字</span></div>
            <div class="stat del"><span>删除</span><b>${delCount}</b><span>字</span></div>
            <div class="stat"><span>相同</span><b>${eqCount}</b><span>字</span></div>
            <div class="stat sim"><span>相似度</span><b>${sim.toFixed(1)}</b><span>%</span></div>
            <div class="stat"><span>耗时</span><b>${elapsed}</b><span>ms</span></div>
        `

        legendHtml.value = `
            <span><i class="ins"></i>新增 / 修改后的内容</span>
            <span><i class="del"></i>被删除 / 被修改的原内容</span>
            <span style="color:#94a3b8;">语气词、标点、空白等停用词不参与判定</span>
        `

        hasResult.value = true

        // 渲染完成后，重新计算并初始化左右两边的页数
        await nextTick()
        if (leftPane.value) onScroll({ target: leftPane.value } as unknown as Event, 'left')
        if (rightPane.value) onScroll({ target: rightPane.value } as unknown as Event, 'right')

    } catch (e) {
        alert('比对失败：' + (e as Error).message)
    } finally {
        running.value = false
    }
}
</script>

<style scoped>
.compare-wrap {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.hint-bar {
    background: #ecf5ff;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 13px;
    color: #606266;
}

.hint-bar b {
    color: #2d6cdf;
}

.card {
    background: #fff;
    border-radius: 6px;
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.upload-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.panel-head {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
}

.panel-head .title {
    font-size: 14px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
}

.dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
}

.dot.old {
    background: #f43f5e;
}

.dot.new {
    background: #10b981;
}

.counter {
    font-size: 12px;
    color: #909399;
}

.drop {
    border: 2px dashed #dcdfe6;
    border-radius: 6px;
    padding: 16px;
    text-align: center;
    color: #606266;
    cursor: pointer;
    transition: 0.2s;
    font-size: 13px;
    user-select: none;
}

.drop:hover,
.drop.over {
    border-color: #2d6cdf;
    background: #f0f5ff;
    color: #2d6cdf;
}

.drop.loading {
    border-color: #93c5fd;
    background: #f0f7ff;
}

.drop small {
    display: block;
    font-size: 11.5px;
    color: #909399;
    margin-top: 4px;
}

textarea {
    width: 100%;
    min-height: 168px;
    margin-top: 12px;
    padding: 12px;
    border: 1px solid #dcdfe6;
    border-radius: 6px;
    font-family: inherit;
    font-size: 13.5px;
    line-height: 1.75;
    resize: vertical;
    outline: none;
    background: #fafbfc;
}

textarea:focus {
    border-color: #2d6cdf;
    background: #fff;
}

.options {
    padding: 16px;
}

.opt-title {
    font-size: 13.5px;
    font-weight: 600;
    margin-bottom: 12px;
    color: #303133;
}

.opt-row {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}

.chk {
    font-size: 13px;
    color: #606266;
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
}

.chk input {
    accent-color: #2d6cdf;
}

.custom-stop {
    display: flex;
    gap: 10px;
    align-items: center;
    font-size: 13px;
    color: #606266;
}

.custom-stop input {
    flex: 1;
    max-width: 400px;
    padding: 8px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    outline: none;
}

.custom-stop input:focus {
    border-color: #2d6cdf;
}

.actions {
    display: flex;
    gap: 10px;
    margin: 6px 0;
}

.btn {
    padding: 8px 20px;
    border-radius: 4px;
    font-size: 13.5px;
    cursor: pointer;
    border: 1px solid transparent;
}

.btn.small {
    padding: 6px 14px;
    font-size: 13px;
}

.btn.primary {
    background: #2d6cdf;
    color: #fff;
}

.btn.primary:hover:not(:disabled) {
    background: #1e4ca1;
}

.btn.ghost {
    background: #fff;
    border-color: #dcdfe6;
    color: #606266;
}

.btn.ghost:hover:not(:disabled) {
    border-color: #2d6cdf;
    color: #2d6cdf;
}

.btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.empty {
    text-align: center;
    padding: 40px;
    color: #909399;
    font-size: 14px;
}

/* ===== 结果展示区 ===== */
.stats {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
}

.stat {
    background: #fff;
    padding: 8px 16px;
    border-radius: 6px;
    border: 1px solid #ebeef5;
    font-size: 13px;
    color: #606266;
    display: flex;
    align-items: center;
    gap: 8px;
}

.stat b {
    font-size: 16px;
}

.stat.del b {
    color: #f43f5e;
}

.stat.ins b {
    color: #10b981;
}

.stat.sim b {
    color: #2d6cdf;
}

.diff-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 16px;
}

.diff-head {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    font-weight: 600;
    color: #606266;
    margin-bottom: 8px;
}

/* 隐藏原生滚动条，并固定高度，作为阅读窗口 */
.pane-wrapper {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.diff-body {
    background: #fcfdff;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 16px;
    height: 60vh;
    /* 固定阅读高度 */
    overflow-y: auto;
    white-space: pre-wrap;
    line-height: 2;
    font-size: 14.5px;
    scrollbar-width: none;
    /* Firefox 隐藏滚动条 */
}

.diff-body::-webkit-scrollbar {
    display: none;
    /* Chrome 隐藏滚动条 */
}

/* 自定义翻页器 */
.pager {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #fafbfc;
    border: 1px solid #ebeef5;
    border-radius: 6px;
    padding: 8px 12px;
}

.page-text {
    font-size: 13px;
    color: #606266;
    font-weight: 500;
}

/* 动态生成的高亮样式（需要 :deep 穿透） */
.diff-body :deep(.hl) {
    border-radius: 3px;
    padding: 2px;
    transition: all 0.3s ease;
}

.diff-body :deep(.hl.del) {
    background: #ffe4e6;
    color: #be123c;
}

.diff-body :deep(.hl.ins) {
    background: #d1fae5;
    color: #047857;
}

.legend {
    display: flex;
    gap: 20px;
    margin-top: 16px;
    font-size: 12.5px;
    color: #606266;
}

.legend i {
    display: inline-block;
    width: 14px;
    height: 12px;
    border-radius: 3px;
    vertical-align: -1px;
    margin-right: 5px;
}

.legend i.del {
    background: #ffe4e6;
    border: 1px solid #fda4af;
}

.legend i.ins {
    background: #d1fae5;
    border: 1px solid #6ee7b7;
}

.warn {
    padding: 10px 14px;
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 6px;
    color: #92400e;
    font-size: 13px;
    margin-bottom: 16px;
}
</style>