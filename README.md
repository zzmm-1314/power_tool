# 电力工具助手

一个面向电力交易业务的桌面工具集，覆盖负荷 / 光伏分析、日前电价、价差分析、结算单更新、月报自动填充、统调电厂、申报系数预测与滚撮分析。上传的 Excel 即时解析入库作为唯一数据来源，支持节点维护、多文件上传，并可作为 Windows exe 分发与增量更新。

---

## 功能特性

### 负荷分析

- 双标签：**负荷曲线** / **光伏出力**，共用日期范围与上传入口
- 支持多日曲线**首尾拼接**（实际一条、预测一条），单日显示差值柱状图（预测 − 实际，次坐标轴）
- 96 点 / 48 点按文件格式自动识别，数据入库后按日期查询

### 日前电价

- **统一结算点**：48 点换算 24 点小时均价，按“行=小时、列=日期”展示红黄色阶表格，底部含日均值与总均值
- **电厂节点**：节点下拉选择，展示该节点各日期的 24 点热力图表格
- **节点编辑**：新增 / 编辑 / 删除 / 批量新增 / 批量删除；节点重命名或删除时同步处理库内该节点的价格数据

### 价差分析

- **统一结算点**与**电厂节点**，均使用 **48 点**计算：价差 = 日前 − 实时
- 双向色阶（正红负绿）、日均值行、总均值条
- 热力图上方新增「日前 vs 实时」48 点折线图，支持按日期切换

### 结算单更新

- **实际结算单更新**：按日期范围解析明细文件夹，填充信息汇总与结算明细
- **椒江模拟结算单**：固定申报功率、旬度策略、中长期持仓等参考文件
- **通用模拟结算单**：现货申报、月度策略、日前实时参考、合约参考等
- 「信息参考 / 日前实时参考 / 合约参考」可从数据目录自动生成
- 后台任务异步执行，前端实时进度与日志

### 月报数据填充

- Word 模板托管在 `my_app_src/data/monthly/templates/`
- 上传结算单 PDF 自动解析 100+ 字段，预览后一键生成 Word 月报
- 支持结算电费大写 `{{settlement_fee.cn}}`

### 统调电厂

- Excel 一键导入，数据存于 `my_app_src/data/unified-plants/统调电厂.xlsx`
- 左侧浙江省地图：按市聚合铭牌出力，颜色由浅红到深红
- 右侧分页表格，支持搜索、城市筛选、按市汇总（含占比进度条）

### 申报系数预测

- 数据源直接从日前 / 实时节点价差构建，无需上传历史 Excel
- 天气文件可选上传
- 天气参数配置弹窗（7 组 30+ 项），仅对本次预测生效
- 展示：修正前多策略曲线（可导出 CSV）、修正后系数、修正前后对比、三张天气面积图、修正明细堆叠图、48 点系数表格

### 滚撮分析

- 粘贴滚动撮合市场盘口 HTML 片段即可分析
- 24 点日前均价自动从统一结算点数据读取，无需上传
- 双图：价格曲线、买1价/卖1价与日前均价价差柱
- 一键导出 Excel（含色阶填色）

### 数据导入

- 多文件逐个上传，显示每个文件进度与总进度
- 上传模态窗按数据类型预选（负荷 / 光伏 / 日前统一 / 日前节点 / 实时 / 价差节点）
- 上传的 Excel 只做即时解析，解析结果写入业务数据库表 `tmp_curve_data`，项目目录不再保存副本
- 各模块统一从数据库读取，数据来源标识只有「数据库」与「暂无数据」两种

---

## 技术栈

| 层       | 技术                                                                    |
| -------- | ----------------------------------------------------------------------- |
| 前端     | Vue 3 + TypeScript + Vite + Pinia + Vue Router + ECharts + vue-echarts  |
| 后端     | Flask + Flask-Cors + python-dotenv + PyMySQL                          |
| 数据处理 | pandas、openpyxl、pdfplumber、docxtpl、BeautifulSoup4、lxml             |
| 预测模块 | scikit-learn（Ridge）、numpy、pandas                                    |
| 打包     | PyInstaller（onedir / onefile）+ desktop-app-source-updater（增量更新） |

---

## 项目结构

```text
power-tool/
├── my_app_src/
│   ├── app.py                        # Flask 入口
│   ├── config.py                     # 读取 .env（含数据库连接配置）
│   ├── requirements.txt
│   ├── .env / .env.example
│   ├── api/
│   │   ├── __init__.py               # 注册蓝图
│   │   ├── load.py                   # 负荷 / 光伏
│   │   ├── price.py                  # 日前电价
│   │   ├── spread.py                 # 价差分析
│   │   ├── settlement.py             # 结算单更新
│   │   ├── monthly.py                # 月报填充
│   │   ├── upload.py                 # 数据导入（Excel 即时解析入库）
│   │   ├── nodes.py                  # 节点 CRUD
│   │   ├── unified_plants.py         # 统调电厂
│   │   ├── coefficient.py            # 申报系数预测
│   │   └── rolling.py                # 滚撮分析
│   ├── services/
│   │   ├── load_service.py           # 负荷/光伏读取与范围聚合
│   │   ├── load_parser.py            # 96 点解析
│   │   ├── day_ahead_service.py      # 日前 48→24、热力图构建、库内取数
│   │   ├── day_ahead_parser.py       # 48 点价格解析
│   │   ├── price_spread_service.py   # 48 点价差、日均价
│   │   ├── settlement/               # 实际/椒江/通用结算单
│   │   ├── monthly_service.py        # 月报模板与渲染
│   │   ├── node_manager.py           # 节点列表与库内数据同步
│   │   ├── db_store.py               # 业务库读写（上传点位入库 / 查询）
│   │   ├── database_provider.py      # 统一取数接口
│   │   ├── unified_plant_service.py  # 统调电厂解析与地图聚合
│   │   ├── rolling_analysis.py       # 滚撮分析
│   │   └── coefficient/              # 申报系数预测（原独立工具迁移）
│   ├── utils/
│   │   ├── response.py               # success / fail
│   │   ├── dataframe.py              # DataFrame → 曲线点
│   │   ├── dates.py
│   │   ├── excel_utils.py
│   │   ├── number_format.py
│   │   └── pdf_parser.py             # 月报 PDF 解析
│   └── data/
│       ├── plant_nodes.json          # 节点清单（由「节点编辑」维护）
│       ├── monthly/templates/        # 月报 Word 模板
│       ├── unified-plants/统调电厂.xlsx
│       ├── contract/                 # 合约配置（典型曲线 / 节假日 / 节点）
│       └── settlement_workspace/     # 结算分时价格工作表（中间产物，超 24h 自动清理）
├── frontend/
│   ├── public/geo/zhejiang.json      # 浙江省 GeoJSON（需自行下载）
│   ├── src/
│   │   ├── api/                      # 请求与各业务 API
│   │   ├── components/               # 布局、上传弹窗、日期范围、任务监控等
│   │   ├── layouts/BasicLayout.vue
│   │   ├── router/index.ts
│   │   ├── stores/                   # app / user（登录暂不使用）
│   │   ├── views/                    # 各功能页面
│   │   ├── plugins/echarts.ts        # 全局 ECharts 注册
│   │   └── assets/styles/global.css
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
└── README.md
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+ / pnpm / npm
- Windows 10+（打包 exe 主要面向 Windows）

### 后端启动

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

默认监听 `http://127.0.0.1:5000`，前端开发时通过 Vite 代理 `/api` 访问。

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

默认 `http://localhost:5173`。

### 环境变量

复制 `.env.example` 为 `.env`：

```dotenv
# Flask
FLASK_ENV=development
FLASK_DEBUG=true
FLASK_PORT=5000
SECRET_KEY=change-me

# 上传
MAX_UPLOAD_MB=50

# 业务数据库（上传解析后的数据入库、各模块取数的唯一来源）
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASS=change-me
DB_NAME=power_tool

# 日志
POWER_TOOL_LOG_LEVEL=INFO
POWER_TOOL_LOG_FILE=
```

说明：

| 变量                    | 说明                                       |
| ----------------------- | ------------------------------------------ |
| `FLASK_PORT`          | 后端端口，默认 5000                        |
| `MAX_UPLOAD_MB`       | 单次请求最大上传体积                       |
| `DB_HOST` / `DB_PORT` | 业务数据库地址与端口                       |
| `DB_USER` / `DB_PASS` | 数据库账号与密码                           |
| `DB_NAME`             | 数据库名，首次启动自动建表 `tmp_curve_data` |
| `POWER_TOOL_LOG_LEVEL` | 日志级别：`DEBUG` / `INFO` / `WARNING` / `ERROR`，默认 `INFO` |
| `POWER_TOOL_LOG_FILE`  | 日志文件路径，留空则写 `<项目根>/logs/app.log`；填 `off` 则只输出控制台 |

日志统一由 `my_app_src/utils/logger.py` 管理（业务代码不再使用 `print`）：同时输出到控制台与文件，单文件 2MB、保留 3 份滚动；启动器日志仍独立写在 `logs/launcher.log`。

前端如需修改 API 地址，可在 `frontend/.env.development` 中配置：

```dotenv
VITE_API_BASE_URL=/api
```

---

## 数据目录与存储

### 数据来源

- 数据读取链路：**上传 Excel → 即时解析 → 写入数据库表 `tmp_curve_data` → 各模块查库**
- 上传的文件只在系统临时目录里被解析一次，解析完立即删除，项目目录不保留副本
- 负荷 / 光伏 / 日前统一结算点 / 实时统一结算点：按（类型 + 设备 + 日期）整体替换入库
- 日前电厂节点 / 实时电厂节点：按（类型 + 节点名 + 日期）写入 48 个点位
- 数据库连接不可用时，接口返回空数据并在控制台打印 `[DbStore]` 错误日志

### 本地数据目录

`my_app_src/data/` 只存放非 Excel 曲线数据的正式文件：

| 位置 | 内容 | 维护入口 |
| --- | --- | --- |
| `plant_nodes.json` | 节点清单 | 「节点编辑」页面 |
| `monthly/templates/` | 月报 Word 模板 | 「月报填充」页面上传 |
| `unified-plants/统调电厂.xlsx` | 统调电厂数据 | 「统调电厂」页面导入 |
| `contract/` | 典型曲线、节假日、节点合约配置 | 「设置 - 中长期合约配置」 |
| `settlement_workspace/` | 结算分时价格工作表（中间产物，超 24 小时自动清理） | 结算单任务自动生成 |
| `storage_config.json` | 历史遗留文件，已不生效，可自行删除 | — |

### 节点管理

- 节点唯一来源为 `data/plant_nodes.json`，由「节点编辑」维护
- 上传日前 / 实时节点价格时只处理已录入节点，未录入节点会被忽略并在结果中提示
- 节点重命名时同步更新库内该节点的价格数据；删除节点会一并清除其库内数据（不可恢复）

---

## Excel 数据格式约定

### 负荷 / 光伏

- 表头自动定位，数据从表头下一行起
- 第 1 列为日期（如 `时间：2026-10-18`），第 2 列为设备名，第 3 列起为 96 点时间值
- 仅保留设备名 `浙江电网`
- 文件名需包含日期：`实际负荷20261018.xlsx`、`预测负荷20261018.xlsx`、`新能源总出力20261018.xlsx`、`光伏总出力预测（日）20261018.xlsx`

### 日前 / 实时价格

- 48 点宽表，表头行包含 `设备名`，数据从下一行起
- 日前统一结算点设备名为 `浙江`
- 实时统一结算点设备名为 `浙江电力`
- 日前 / 实时电厂节点为多设备行，按节点名匹配
- 文件名需包含 `YYYYMMDD` 日期

### 统调电厂

- 列顺序：调度命名、机组序号、铭牌出力(MW)、所在城市
- 城市名可带或不带“市”，后端自动规范化

### 天气文件（申报系数预测）

可选，需包含 `time` 列（可自动识别第一列为时间），推荐字段：

- `apparent_temperature (°C)`
- `cloud_cover_low (%)`
- `wind_speed_80m (km/h)`
- `relative_humidity_2m (%)`
- `direct_radiation (W/m²)`
- `diffuse_radiation (W/m²)`

---

## 主要接口概览

| 模块         | 路径前缀                | 说明                                                                                                              |
| ------------ | ----------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 负荷 / 光伏  | `/api/load`           | `/analysis`、`/pv`、`/devices`                                                                              |
| 日前电价     | `/api/price`          | `/day-ahead`、`/plant-nodes`、`/day-ahead/unified-heatmap`、`/day-ahead/plant-heatmap`                    |
| 价差分析     | `/api/spread`         | `/analysis`、`/unified-heatmap`、`/plant-heatmap`、`/daily-prices`                                        |
| 结算单更新   | `/api/settlement`     | `/start/<type>`、`/tasks/<id>`、`/parse-paths`、`/browse-file`、`/browse-folder`、`/build-price-file` |
| 月报填充     | `/api/monthly`        | `/templates`、`/parse`、`/generate`                                                                         |
| 数据导入     | `/api/upload`           | `POST /api/upload`（Excel 即时解析入库）                                                                 |
| 节点管理     | `/api/nodes`          | `/plant`、`/plant/batch`                                                                                      |
| 统调电厂     | `/api/unified-plants` | `/import`、`/list`、`/map`、`/cities`                                                                     |
| 申报系数预测 | `/api/coefficient`    | `/predict`、`/progress/<id>`、`/weather-config`                                                             |
| 滚撮分析     | `/api/rolling`        | `/analyze`、`/export`                                                                                         |

所有接口统一返回：

```json
{ "code": 0, "msg": "ok", "data": {} }
```

---

## 打包与增量更新

项目最终打包为 Windows exe。推荐使用 **PyInstaller + desktop-app-source-updater**，将“启动器”与“业务源码”分离，日常更新只发布源码包。

### 1. 首次打包（全量）

```bash
pip install pyinstaller desktop-app-source-updater
pyinstaller --onefile --name power_tool_launcher launcher.py
```

分发目录结构：

```text
power_tool_install/
├── power_tool_launcher.exe
└── my_app_src/
    ├── __init__.py        # 包含 __version__ = "1.0.0"
    ├── app.py
    ├── api/
    ├── services/
    ├── utils/
    ├── static/            # 前端构建产物
    └── ...
```

启动器启动时会先检查 GitHub Release，再导入并运行 `my_app_src.app`。

### 2. 日常更新（只发源码）

1. 修改 `my_app_src/` 下代码或静态资源
2. 递增 `my_app_src/__init__.py` 的 `__version__`
3. 打包更新包：

```bash
cd my_app_src
zip -r ../power_tool_update_1.0.1.zip .
cd ..
```

4. 在 GitHub 创建 Release，Tag 为 `v1.0.1`，上传 `power_tool_update_1.0.1.zip` 作为资产
5. 用户重启 `power_tool_launcher.exe` 即自动更新

> 启动器配置中的 `asset_prefix` 需与 zip 文件名前缀一致（默认 `power_tool_update_`）。

### 3. 前端资源打包

前端执行：

```bash
cd frontend
npm run build
cd ..
# 复制到 static
Remove-Item .\static -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item .\frontend\dist\* .\static\ -Recurse -Force

# 启动（用 launcher.py 打包后的 exe）
.\power_tool_launcher.exe
```

将 `dist/` 内容放入 `my_app_src/static/`，Flask 以静态目录方式提供。

### 4. 地图文件

统调电厂页面需要浙江省 GeoJSON：

```text
frontend/public/geo/zhejiang.json
```

开发时放置于 `frontend/public/geo/`，打包后随 `static/geo/zhejiang.json` 一起分发。

---

## 常见问题

### 地图不显示

检查 `frontend/public/geo/zhejiang.json` 是否存在且为合法 JSON。前端会回退到 CDN，但生产环境建议本地托管。

### 上传成功但页面没有数据

- 确认数据库可连通（`.env` 中 `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_NAME`）
- 查看 `logs/app.log`（或控制台）中 `services.db_store`、`services.ingest` 开头的日志：建表失败、查询失败、入库降级都会记录在此
- 首次启动会自动创建表 `tmp_curve_data`；若账号没有建表权限，需要手工执行建表语句
- 文件名需带 `YYYYMMDD` 日期，否则解析不到日期会报「未解析到有效数据」

### 价差分析没有数据

价差需要**同一天同时存在日前和实时数据**。请确认：

- 日前统一结算点或对应节点已有数据
- 实时统一结算点或对应节点已有数据
- 日期范围包含该日期

### 通用模拟结算单提示“未找到汇总工作表”

目标文件 sheet 名称需包含「模拟结算」和「汇总」字样，或精确为 `模拟结算汇总表` / `模拟结算汇总`。后端会给出当前工作簿的 sheet 列表。

### 申报系数预测提示“有效价差数据不足”

至少需要 30 天同时存在日前与实时数据的日期。请先在日前 / 实时节点或统一结算点上传足够数据。

### 滚撮分析提示“未找到数据表格”

请确认粘贴的 HTML 片段包含：

- `div.el-table__body-wrapper` 内的 `table`，或
- `table.el-table__body`

且数据行使用 `tr.el-table__row`。

### 端口被占用

修改 `.env` 中 `FLASK_PORT`，或使用 PyInstaller 启动器时由系统自动分配端口。

---

## 说明

- 登录 / 注册与权限模块当前已移除；节点权限以「节点编辑」维护的节点列表为准
- 曲线类数据（负荷 / 光伏 / 电价 / 价差）唯一来源是业务数据库表 `tmp_curve_data`，原临时 Excel 存储功能已删除
- 所有价格类数据统一保留 3 位小数展示

---

## License

本项目为内部业务工具，未开放开源许可。如需对外分发，请联系项目维护者。
