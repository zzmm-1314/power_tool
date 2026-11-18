import re, glob, sys

APPLY = "--apply" in sys.argv

# ---------- 死代码：页面已改用 HeatmapGrid，这些表格类在模板中不存在 ----------
DEAD = {
    "src/views/day-ahead-price/PlantNode.vue":
        [".table-wrap", ".price-table", ".sticky-col", ".corner", ".value-td",
         ".avg-", ".overall-avg", ".legend-", ".empty-tip"],
    "src/views/day-ahead-price/UnifiedSettlement.vue":
        [".table-wrap", ".price-table", ".sticky-col", ".corner", ".value-td",
         ".avg-", ".overall-avg", ".legend-", ".empty-tip", ".input"],
    "src/views/price-spread/PlantNode.vue":
        [".table-wrap", ".price-table", ".sticky-col", ".corner", ".value-td",
         ".avg-", ".overall-avg", ".legend-", ".empty-tip"],
    "src/views/price-spread/UnifiedSettlement.vue":
        [".table-wrap", ".price-table", ".sticky-col", ".corner", ".value-td",
         ".avg-", ".overall-avg", ".legend-", ".empty-tip"],
}
DEAD_ALL_FILES = [":deep(.date-range .input)"]  # 遗留穿透（页面 .input 已删，组件走全局）

# ---------- 与 global.css 完全一致 → 任何文件都直接删 ----------
DUP = {
    ".input:focus", ".input:disabled", ".input.small", ".hidden-input",
    ".table-wrap.loading", ".empty-tip code", ".msg.err", ".msg.ok", ".mask",
    ".modal-header", ".modal-subtitle", ".modal-body", ".form-card",
    ".filter-item", ".filter-item label", ".lbl", ".separator", ".extra-group",
    ".stat-cards", ".stat-card", ".stat-label", ".stat-value",
    ".btn-clear", ".btn.primary", ".btn.primary:hover:not(:disabled)",
    ".btn.ghost", ".btn.ghost:hover:not(:disabled)", ".btn.small",
    ".btn:disabled", ".btn:hover:not(:disabled)", ".btn-primary:disabled",
    ".btn-upload", ".btn-upload:hover",
}

# ---------- 逐文件：None=删除；字符串=整条规则替换（仅保留页面特有属性） ----------
EDIT = {}
def E(path, sel, val):
    EDIT.setdefault(path, {})[sel] = val

P = {k: "src/views/" + k for k in []}  # noqa - keep paths literal below

# —— 组件 ——
E("src/components/DateRangeInput.vue", ".input", ".input { width: 160px; }")
E("src/components/PathInput.vue", ".input", ".input { flex: 1; font-family: 'Consolas', 'Monaco', monospace; }")
E("src/components/DateMultiInput.vue", ".textarea", ".textarea { flex: 1; min-height: 64px; font-family: 'Consolas', 'Monaco', monospace; }")
E("src/components/PriceFilePicker.vue", ".select", ".select { min-width: 160px; }")
E("src/components/PriceFilePicker.vue", ".msg", None)  # 全局 msg 已有 padding/radius/font-size
E("src/components/PriceFilePicker.vue", ".link", ".link { border: none; background: transparent; color: var(--danger); font-size: 12px; cursor: pointer; text-decoration: underline; }")
E("src/components/PriceFilePicker.vue", ".row", ".row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }")
E("src/components/PriceFilePicker.vue", ".row-label", ".row-label { width: 40px; flex-shrink: 0; font-size: 12px; color: var(--text-4); }")
E("src/components/WeatherConfigModal.vue", ".input", ".input { width: 120px; font-size: 12px; }")
E("src/components/WeatherConfigModal.vue", ".modal", ".modal { width: 720px; max-width: 94vw; max-height: 88vh; display: flex; flex-direction: column; overflow: hidden; }")
E("src/components/WeatherConfigModal.vue", ".modal-footer", None)
E("src/components/WeatherConfigModal.vue", ".modal-title", None)
E("src/components/WeatherConfigModal.vue", ".form-item", ".form-item { display: flex; align-items: center; gap: 8px; }")
E("src/components/WeatherConfigModal.vue", ".form-item label", None)
E("src/components/WeatherConfigModal.vue", ".group-title", ".group-title { font-size: 13px; font-weight: 600; color: var(--text-1); padding: 4px 0 8px; border-bottom: 1px dashed var(--border); margin-bottom: 10px; }")
E("src/components/TaskMonitor.vue", ".title", ".title { font-size: 14px; font-weight: 600; color: var(--text-1); }")
E("src/components/TaskMonitor.vue", ".progress-wrap", ".progress-wrap { display: flex; align-items: center; gap: 10px; }")
E("src/components/UploadPreview.vue", ".preview-meta", ".preview-meta { font-size: 12px; color: var(--text-4); flex: 1; }")
E("src/components/UploadModal.vue", ".modal-title", ".modal-title { font-size: 17px; }")
E("src/components/UploadModal.vue", ".modal-body", None)
E("src/components/UploadModal.vue", ".msg", None)
E("src/components/UploadModal.vue", ".form-item", ".form-item { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }")
E("src/components/UploadModal.vue", ".form-item label", None)
E("src/components/UploadModal.vue", ".progress-wrap", None)
E("src/components/PageContainer.vue", ":deep(.btn-upload)", None)
E("src/components/PageContainer.vue", ":deep(.btn-upload:hover)", None)
E("src/components/PageContainer.vue", ".page-header", ".page-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px; background: var(--bg-card); border-radius: var(--radius-md); box-shadow: var(--shadow-md); flex-wrap: wrap; }")
E("src/components/PageContainer.vue", ".page-title", ".page-title { margin: 0; font-size: 17px; font-weight: 600; color: var(--text-1); }")
E("src/components/HeatmapGrid.vue", ".legend-block", ".legend-block { display: flex; align-items: center; gap: 8px; }")
E("src/components/HeatmapGrid.vue", ".legend-label", None)
E("src/components/HeatmapGrid.vue", ".corner", None)
E("src/components/HeatmapGrid.vue", ".row-label", ".row-label { background: var(--bg-header); color: var(--text-2); font-weight: 500; font-size: 11px; }")
E("src/components/HeatmapGrid.vue", ".avg-label", ".avg-label { background: var(--primary-light); color: var(--primary); font-weight: 600; }")
E("src/components/HeatmapGrid.vue", ".overall-avg", ".overall-avg { font-size: 13px; color: var(--text-3); white-space: nowrap; }")
E("src/components/HeatmapGrid.vue", ".overall-avg strong", ".overall-avg strong { color: var(--primary); font-size: 14px; font-weight: 700; }")
E("src/components/HeatmapGrid.vue", ".heat-wrap", ".heat-wrap { display: flex; flex-direction: column; gap: 8px; background: var(--bg-card); border-radius: var(--radius-md); padding: 12px; box-shadow: var(--shadow-sm); }")
E("src/components/ChartPanel.vue", ".chart-title", ".chart-title { margin-bottom: 8px; font-size: 14px; font-weight: 600; color: var(--text-2); }")
E("src/components/ChartPanel.vue", ".chart", ".chart { width: 100%; height: 100%; }")

# —— 视图 ——
E("src/views/load-analysis/index.vue", ".input", None)  # 死代码（无对应元素）
E("src/views/load-analysis/index.vue", ".input:focus", None)
E("src/views/load-analysis/index.vue", ".tab-btn", ".tab-btn { height: 28px; padding: 0 16px; border: none; border-radius: var(--radius-sm); background: transparent; color: var(--text-3); font-size: 13px; cursor: pointer; transition: background 0.15s, color 0.15s; }")
E("src/views/load-analysis/index.vue", ".tab-btn:hover", ".tab-btn:hover { color: var(--primary); }")
E("src/views/load-analysis/index.vue", ".tab-btn.active", ".tab-btn.active { background: var(--bg-card); color: var(--primary); font-weight: 600; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08); }")
E("src/views/load-analysis/index.vue", ".legend-tip", ".legend-tip { display: flex; align-items: center; gap: 6px; padding: 8px 16px; background: var(--bg-card); border-radius: var(--radius-sm); box-shadow: var(--shadow-sm); font-size: 12px; color: var(--text-3); }")
E("src/views/load-analysis/index.vue", ".chart", None)  # .chart 全局已有 width100%/height100%

for v in ["settlement/ActualSettlement", "settlement/JiaojiangSim", "settlement/generalSim"]:
    f = "src/views/" + v + ".vue"
    E(f, ".btn", None)          # 基线统一：全部吃全局 .btn
    E(f, ".input", ".input { width: 180px; }" if v != "settlement/ActualSettlement" else None)
    E(f, ".form-card", None)
    E(f, ".picker-wrap", ".picker-wrap { flex: 1; min-width: 0; padding: 8px 12px; background: var(--bg-header); border-radius: var(--radius-sm); border: 1px solid var(--border); }")
    E(f, ".msg", None)
E("src/views/settlement/ActualSettlement.vue", ".form-row", ".form-row { align-items: flex-start; gap: 12px; margin-bottom: 14px; }")
E("src/views/settlement/JiaojiangSim.vue", ".form-row", ".form-row { align-items: flex-start; gap: 12px; }")
E("src/views/settlement/generalSim.vue", ".form-row", ".form-row { align-items: flex-start; gap: 12px; }")
E("src/views/settlement/ActualSettlement.vue", ".form-row>label", ".form-row>label { width: 110px; }")
E("src/views/settlement/JiaojiangSim.vue", ".form-row>label", ".form-row>label { width: 110px; }")
E("src/views/settlement/generalSim.vue", ".form-row>label", ".form-row>label { width: 130px; }")
E("src/views/settlement/ActualSettlement.vue", ".form-actions", ".form-actions { padding-left: 110px; }")
E("src/views/settlement/JiaojiangSim.vue", ".form-actions", ".form-actions { padding-left: 110px; margin-top: 8px; }")
E("src/views/settlement/generalSim.vue", ".form-actions", ".form-actions { padding-left: 130px; margin-top: 8px; }")
E("src/views/settlement/generalSim.vue", ".hint", None)
E("src/views/settlement/generalSim.vue", ".msg", None)
E("src/views/settlement/ActualSettlement.vue", ".tenday-row", None)  # 保留原定义→见文件内检查

# 上面这条不确定，直接移除
EDIT["src/views/settlement/ActualSettlement.vue"].pop(".tenday-row", None)

E("src/views/contract/ContractDecomposition.vue", ".form-row", ".form-row { align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }")
E("src/views/contract/ContractDecomposition.vue", ".table-wrap", ".table-wrap { flex: 1; }")
E("src/views/contract/ContractDecomposition.vue", ".result-card", ".result-card { margin-top: 16px; }")
E("src/views/contract/ContractDecomposition.vue", ".filter-bar", ".filter-bar { align-items: center; }")
E("src/views/contract/ContractDecomposition.vue", ".empty-tip", ".empty-tip { flex: 1; display: flex; align-items: center; justify-content: center; }")
E("src/views/contract/ContractPosition.vue", ".table-wrap", ".table-wrap { flex: 1; }")
E("src/views/contract/ContractPosition.vue", ".result-card", None)
E("src/views/contract/ContractPosition.vue", ".filter-bar", ".filter-bar { align-items: center; }")
E("src/views/contract/ContractPosition.vue", ".empty-tip", ".empty-tip { display: flex; height: 100%; align-items: center; justify-content: center; }")
E("src/views/contract/ContractPosition.vue", ".tab-btn", ".tab-btn { padding: 6px 20px; border: none; background: transparent; font-size: 14px; color: var(--text-3); border-radius: var(--radius-sm); cursor: pointer; transition: all 0.2s; }")
E("src/views/contract/ContractPosition.vue", ".tab-btn.active", ".tab-btn.active { background: var(--bg-card); color: var(--primary); font-weight: 600; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1); }")
E("src/views/contract/ContractPosition.vue", ".chart", None)
E("src/views/contract/ContractDecomposition.vue", ".sticky-col", ".sticky-col { position: sticky; background: var(--row-bg, #fff); z-index: 5; border-right: 1px solid var(--border-strong); }")
E("src/views/contract/ContractDecomposition.vue", ".result-table", ".result-table { border-collapse: separate; border-spacing: 0; font-size: 12px; text-align: right; white-space: nowrap; min-width: max-content; }")
E("src/views/contract/ContractDecomposition.vue", ".result-table th", ".result-table th { background: var(--bg-header); position: sticky; top: 0; z-index: 10; text-align: center; }")
E("src/views/contract/ContractDecomposition.vue", ".result-table th, .result-table td", ".result-table th, .result-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); border-right: 1px solid var(--border); }")

for v in ["contract/CrossProvinceProfit", "contract/RollingProfit"]:
    f = "src/views/" + v + ".vue"
    E(f, ".data-table", ".data-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: center; }")
    E(f, ".data-table th", None)
    E(f, ".data-table th, .data-table td", ".data-table th, .data-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); white-space: nowrap; }")
    E(f, ".table-wrap", ".table-wrap { flex: 1; }")
    E(f, ".result-card", ".result-card { margin-top: 16px; max-height: calc(100vh - 320px); }")
    E(f, ".empty-tip", ".empty-tip { flex: 1; display: flex; align-items: center; justify-content: center; padding: 40px; }")
    E(f, ".hidden-input", None)
E("src/views/contract/CrossProvinceProfit.vue", ".filter-bar", ".filter-bar { align-items: flex-end; }")
E("src/views/contract/CrossProvinceProfit.vue", ".action-btns", ".action-btns { display: flex; gap: 12px; }")
E("src/views/contract/CrossProvinceProfit.vue", ".sticky-col", ".sticky-col { position: sticky; left: 0; z-index: 3; background: var(--bg-body) !important; color: var(--text-2); font-weight: 500; }")
E("src/views/contract/RollingProfit.vue", ".filter-bar", ".filter-bar { align-items: center; }")
E("src/views/contract/RollingProfit.vue", ".btn-primary", None)

E("src/views/rolling/index.vue", ".input", ".input { width: 140px; }")
E("src/views/rolling/index.vue", ".btn-primary", ".btn-primary { margin-left: auto; }")
E("src/views/rolling/index.vue", ".table-wrap", ".table-wrap { flex: 1; }")
E("src/views/rolling/index.vue", ".data-table", ".data-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 12px; text-align: center; white-space: nowrap; }")
E("src/views/rolling/index.vue", ".data-table th", None)
E("src/views/rolling/index.vue", ".data-table th, .data-table td", ".data-table th, .data-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); border-right: 1px solid var(--border); font-variant-numeric: tabular-nums; }")
E("src/views/rolling/index.vue", ".sticky-col", ".sticky-col { position: sticky; background: var(--bg-header); z-index: 1; border-right: 1px solid var(--border-strong); }")
E("src/views/rolling/index.vue", ".empty-tip", ".empty-tip { flex: 1; display: flex; align-items: center; justify-content: center; }")
E("src/views/rolling/index.vue", ".legend-tip", ".legend-tip { display: flex; align-items: center; gap: 8px; background: var(--bg-card); padding: 10px 16px; border-radius: var(--radius-md); box-shadow: var(--shadow-sm); font-size: 12px; color: var(--text-3); margin-top: 12px; }")
E("src/views/rolling/index.vue", ".form-group", ".form-group { display: flex; align-items: center; gap: 8px; }")
E("src/views/rolling/index.vue", ".result-card", ".result-card { margin-top: 16px; max-height: calc(100vh - 240px); }")

E("src/views/coefficient/index.vue", ".table-wrap", ".table-wrap { max-height: 540px; border: 1px solid var(--border); }")
E("src/views/coefficient/index.vue", ".data-table", None)
E("src/views/coefficient/index.vue", ".data-table th", None)
E("src/views/coefficient/index.vue", ".data-table th, .data-table td", ".data-table th, .data-table td { padding: 6px 12px; border-bottom: 1px solid var(--border); text-align: center; }")
E("src/views/coefficient/index.vue", ".input", ".input { width: auto; }")
E("src/views/coefficient/index.vue", ".input.small", ".input.small { width: 90px; }")
E("src/views/coefficient/index.vue", ".btn", None)
E("src/views/coefficient/index.vue", ".msg", None)
E("src/views/coefficient/index.vue", ".file-input", None)
E("src/views/coefficient/index.vue", ".chart", ".chart { height: 420px; }")
E("src/views/coefficient/index.vue", ".chart-card", ".chart-card { display: flex; flex-direction: column; gap: 10px; }")
E("src/views/coefficient/index.vue", ".chart-header", ".chart-header { display: flex; align-items: center; justify-content: space-between; }")
E("src/views/coefficient/index.vue", ".chart-title", None)
E("src/views/coefficient/index.vue", ".chart-body", ".chart-body { min-height: 420px; }")
E("src/views/coefficient/index.vue", ".form-row", ".form-row { align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }")

E("src/views/monthly-report/index.vue", ".card", ".card { padding: 16px 20px; display: flex; flex-direction: column; gap: 10px; }")
E("src/views/monthly-report/index.vue", ".select", ".select { min-width: 260px; }")
E("src/views/monthly-report/index.vue", ".msg", None)
E("src/views/monthly-report/index.vue", ".hint", ".hint { margin: 0; line-height: 1.6; }")
E("src/views/monthly-report/index.vue", ".file-input", None)
E("src/views/monthly-report/index.vue", ".btn", None)
E("src/views/monthly-report/index.vue", ".hidden-input", None)
E("src/views/monthly-report/index.vue", ".row", ".row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }")
E("src/views/monthly-report/index.vue", ".preview-meta", ".preview-meta { font-size: 12px; color: var(--text-4); font-weight: 400; margin-left: 4px; }")

E("src/views/monthly-report/PdfExtract.vue", ".file-input", None)
E("src/views/monthly-report/PdfExtract.vue", ".panel", ".panel { padding: 16px; }")
E("src/views/monthly-report/PdfExtract.vue", ".panel-left", ".panel-left { flex: 0 0 320px; }")
E("src/views/monthly-report/PdfExtract.vue", ".panel-right", ".panel-right { flex: 1; overflow: hidden; }")
E("src/views/monthly-report/PdfExtract.vue", ".table-wrap", ".table-wrap { flex: 1; border: 1px solid var(--border); }")
E("src/views/monthly-report/PdfExtract.vue", ".empty-tip", ".empty-tip { flex: 1; display: flex; align-items: center; justify-content: center; border: 1px dashed var(--border-strong); border-radius: var(--radius-sm); }")
E("src/views/monthly-report/PdfExtract.vue", ".hidden-input", None)
E("src/views/monthly-report/PdfExtract.vue", ".msg", None)
E("src/views/monthly-report/PdfExtract.vue", ".msg.err", None)
E("src/views/monthly-report/PdfExtract.vue", ".upload-area", ".upload-area { border: 1px dashed var(--border-strong); border-radius: var(--radius-sm); padding: 24px 20px; text-align: center; cursor: pointer; transition: border-color 0.2s; background: var(--bg-header); word-break: break-all; }")
E("src/views/monthly-report/PdfExtract.vue", ".upload-area:hover", ".upload-area:hover { border-color: var(--primary); background: var(--primary-light); }")
E("src/views/monthly-report/PdfExtract.vue", ".section-title", ".section-title { margin: 0; font-size: 14px; font-weight: 600; color: var(--text-2); margin-bottom: 12px; }")
E("src/views/monthly-report/PdfExtract.vue", ".action-btns", ".action-btns { display: flex; gap: 8px; }")
E("src/views/monthly-report/PdfExtract.vue", ".result-table", ".result-table { width: 100%; border-collapse: collapse; font-size: 13px; }")
E("src/views/monthly-report/PdfExtract.vue", ".result-table th", None)
E("src/views/monthly-report/PdfExtract.vue", ".result-table th, .result-table td", ".result-table th, .result-table td { padding: 10px 12px; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }")
E("src/views/monthly-report/PdfExtract.vue", ".btn-text", ".btn-text { background: none; border: none; color: var(--danger); font-size: 12px; cursor: pointer; padding: 0; text-align: right; margin-top: 8px; text-decoration: underline; }")
E("src/views/monthly-report/PdfExtract.vue", ".upload-item", ".upload-item { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }")

E("src/views/node-edit/index.vue", ".textarea", ".textarea { font-family: 'Consolas', 'Monaco', monospace; min-height: 100px; }")
E("src/views/node-edit/index.vue", ".modal", ".modal { width: 440px; padding: 24px; }")
E("src/views/node-edit/index.vue", ".modal-title", ".modal-title { margin: 0 0 16px; }")
E("src/views/node-edit/index.vue", ".modal-footer", ".modal-footer { border-top: none; background: none; padding: 0; gap: 8px; margin-top: 16px; }")
E("src/views/node-edit/index.vue", ".mask", None)
E("src/views/node-edit/index.vue", ".btn", None)
E("src/views/node-edit/index.vue", ".btn.ghost", None)
E("src/views/node-edit/index.vue", ".hint", ".hint { margin: 2px 0 0; }")
E("src/views/node-edit/index.vue", ".form-item", ".form-item { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }")
E("src/views/node-edit/index.vue", ".form-item label", None)
E("src/views/node-edit/index.vue", ".table-wrap", ".table-wrap { background: var(--bg-card); box-shadow: var(--shadow-sm); }")

E("src/views/settings/ContractConfig.vue", ".btn-primary", ".btn-primary { margin-top: auto; }")
E("src/views/settings/ContractConfig.vue", ".panel", ".panel { padding: 24px; box-shadow: var(--shadow-md); }")
E("src/views/settings/ContractConfig.vue", ".panel-left", ".panel-left { flex: 0 0 340px; }")
E("src/views/settings/ContractConfig.vue", ".upload-area", ".upload-area { display: flex; justify-content: center; align-items: center; border: 1px dashed var(--border-strong); border-radius: var(--radius-sm); background: var(--bg-header); padding: 20px 10px; cursor: pointer; transition: all 0.25s var(--ease); }")
E("src/views/settings/ContractConfig.vue", ".upload-area:hover", ".upload-area:hover { border-color: var(--primary); background: var(--primary-light); }")
E("src/views/settings/ContractConfig.vue", ".upload-area.has-file", ".upload-area.has-file { border-color: var(--success); background: var(--success-bg); }")
E("src/views/settings/ContractConfig.vue", ".upload-content", ".upload-content { display: flex; flex-direction: column; align-items: center; gap: 8px; }")
E("src/views/settings/ContractConfig.vue", ".upload-item", ".upload-item { display: flex; flex-direction: column; gap: 8px; }")
E("src/views/settings/ContractConfig.vue", ".section-title", ".section-title { margin: 0; font-size: 16px; font-weight: 600; color: var(--text-1); margin-bottom: 24px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }")
E("src/views/settings/ContractConfig.vue", ".empty-tip", ".empty-tip { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 14px; background: var(--bg-header); border: 1px dashed var(--border-strong); border-radius: var(--radius-md); margin-top: 16px; }")
E("src/views/settings/ContractConfig.vue", ".form-group", ".form-group { margin-bottom: 20px; display: flex; flex-direction: column; gap: 8px; }")
E("src/views/settings/ContractConfig.vue", ".hidden-input", None)
E("src/views/settings/ContractConfig.vue", ".link", ".link { color: var(--primary); text-decoration: none; font-size: 13px; transition: color 0.2s; }")
E("src/views/settings/ContractConfig.vue", ".btn-text", ".btn-text { font-size: 13px; font-weight: 500; }")
E("src/views/settings/ContractConfig.vue", ".btn-clear", None)
E("src/views/settings/ContractConfig.vue", ".btn-clear:hover", None)

E("src/views/unified-plants/index.vue", ".btn", None)
E("src/views/unified-plants/index.vue", ".btn.ghost", None)
E("src/views/unified-plants/index.vue", ".btn.small", None)
E("src/views/unified-plants/index.vue", ".msg", None)
E("src/views/unified-plants/index.vue", ".file-input", None)
E("src/views/unified-plants/index.vue", ".input", ".input { width: auto; }")
E("src/views/unified-plants/index.vue", ".table-wrap", ".table-wrap { flex: 1; min-height: 0; border: 1px solid var(--border); }")
E("src/views/unified-plants/index.vue", ".data-table", None)
E("src/views/unified-plants/index.vue", ".data-table th", None)
E("src/views/unified-plants/index.vue", ".data-table th, .data-table td", ".data-table th, .data-table td { padding: 8px 12px; border-bottom: 1px solid var(--border); text-align: left; }")
E("src/views/unified-plants/index.vue", ".tab-btn", ".tab-btn { height: 28px; padding: 0 16px; border: none; border-radius: var(--radius-sm); background: transparent; color: var(--text-3); font-size: 13px; cursor: pointer; transition: background 0.15s, color 0.15s; }")
E("src/views/unified-plants/index.vue", ".tab-btn:hover", ".tab-btn:hover { color: var(--primary); }")
E("src/views/unified-plants/index.vue", ".tab-btn.active", ".tab-btn.active { background: var(--bg-card); color: var(--primary); font-weight: 600; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08); }")
E("src/views/unified-plants/index.vue", ".chart", ".chart { min-height: 440px; }")

# day-ahead / price-spread 视图：只改文件里剩余要动的
E("src/views/day-ahead-price/PlantNode.vue", ".btn", None)
E("src/views/day-ahead-price/PlantNode.vue", ".input", None)   # 死代码
E("src/views/day-ahead-price/PlantNode.vue", ".input:focus", None)
E("src/views/day-ahead-price/PlantNode.vue", ".file-input", None)
E("src/views/day-ahead-price/PlantNode.vue", ".empty-tip", None)
E("src/views/day-ahead-price/UnifiedSettlement.vue", ".btn", None)
E("src/views/day-ahead-price/UnifiedSettlement.vue", ".empty-tip", None)
E("src/views/price-spread/PlantNode.vue", ".btn", None)
E("src/views/price-spread/PlantNode.vue", ".input", None)
E("src/views/price-spread/PlantNode.vue", ".input:focus", None)
E("src/views/price-spread/PlantNode.vue", ".file-input", None)
E("src/views/price-spread/PlantNode.vue", ".empty-tip", None)
E("src/views/price-spread/UnifiedSettlement.vue", ".btn", None)
E("src/views/price-spread/UnifiedSettlement.vue", ".empty-tip", None)

for f in ["day-ahead-price/PlantNode", "day-ahead-price/UnifiedSettlement",
          "price-spread/PlantNode", "price-spread/UnifiedSettlement"]:
    ff = "src/views/" + f + ".vue"
    E(ff, ".legend-bar-wrap", ".legend-bar-wrap { display: flex; align-items: center; gap: 10px; padding: 10px 16px; background: var(--bg-card); border-radius: var(--radius-sm); box-shadow: var(--shadow-sm); }")
    E(ff, ".legend-label", None)

# ---------- 处理 ----------

def top_rules(css):
    res, i, n = [], 0, len(css)
    while i < n:
        b = css.find("{", i)
        if b == -1:
            break
        depth, j = 1, b + 1
        while j < n and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        sel = " ".join(css[i:b].split())
        res.append((i, b, j, sel))
        i = j
    return res

def rebuild(css, edits, dead_pref):
    out, changed, n_del = [], 0, 0
    for s, b, e, sel in top_rules(css):
        raw = css[s:e]
        head = sel.split(" ")[0] if sel else ""
        if not sel:
            out.append(raw); continue
        if sel.startswith("@"):
            if sel.startswith(("@media", "@supports")):
                inner = css[b + 1:e - 1]
                ni, nc = rebuild(inner, edits, dead_pref)
                changed += nc
                if ni.strip():
                    out.append(sel + " {" + ni + "}")
            else:
                out.append(raw)
            continue
        if any(sel.startswith(p) for p in dead_pref) or sel in DEAD_ALL_FILES:
            changed += 1; n_del += 1; continue
        if sel in edits:
            changed += 1
            if edits[sel] is None:
                n_del += 1
            else:
                out.append("\n" + edits[sel].strip() + "\n")
            continue
        if sel in DUP:
            changed += 1; n_del += 1; continue
        out.append(raw)
    joined = "".join(out)
    if joined.strip():
        joined = re.sub(r"\n{3,}", "\n\n", joined).strip("\n") + "\n"
    else:
        joined = ""
    return joined, changed, n_del

grand = [0, 0]
for path in sorted(glob.glob("src/**/*.vue", recursive=True)):
    key = path.replace("\\", "/")
    edits = EDIT.get(key, {})
    dead_pref = DEAD.get(key, [])
    if not edits and not dead_pref:
        continue
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"<style[^>]*>", txt)
    o = m.end()
    c = txt.index("</style>", o)
    new_css, ch, nd = rebuild(txt[o:c], edits, dead_pref)
    grand[0] += ch; grand[1] += nd
    print("%-52s %5d -> %5d   改动 %2d 删除 %2d" % (key, c - o, len(new_css), ch, nd))
    if APPLY:
        open(path, "w", encoding="utf-8", newline="\n").write(txt[:o] + new_css + txt[c:])
    # 若 style 块空了，把 <style>...</style> 整段删掉
    if APPLY and not new_css.strip():
        t2 = open(path, encoding="utf-8").read()
        t2 = re.sub(r"\n?<style[^>]*>\s*</style>", "", t2)
        open(path, "w", encoding="utf-8", newline="\n").write(t2)
        print("   (style 块已清空并移除)")

print(("APPLY" if APPLY else "DRY-RUN"), "| 改动规则:", grand[0], "| 删除规则:", grand[1])
