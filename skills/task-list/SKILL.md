---
name: task-list
description: Analyze PRD documents and generate structured task breakdowns with dependency graphs, priority tracking, and visual dashboards. Use this skill when the user wants to break down a PRD into implementable tasks, view task progress, update task status, or get next actionable items. Trigger on mentions of task decomposition, PRD analysis, task lists, work breakdown, sprint planning, or project task tracking.
argument-hint: <prd-path> | status | update <task-id> <status> | regen | next
---

# /task-list -- PRD 任务分解与可视化

## Description

Analyze a PRD and generate a structured task breakdown with dependency graph, JSON data file, terminal ASCII dashboard, and self-contained HTML visualization.

## Instructions

### Subcommands

- `/task-list <prd-path>` -- 分析 PRD，生成 tasks.json + tasks.html，显示终端摘要
- `/task-list status` -- 终端 ASCII 查看当前任务状态
- `/task-list update <task-id> <status>` -- 更新任务状态，级联解除阻塞，同步数据文件
- `/task-list regen` -- 重新生成 HTML 模板和数据文件
- `/task-list next` -- 显示下一批可执行任务（无阻塞 + 最高优先级）

### Output Location

Tasks are saved to `specs/tasks/` relative to the project root:
- `specs/tasks/tasks.json` -- 结构化任务数据（Claude Code 读写）
- `specs/tasks/tasks-data.js` -- 浏览器数据镜像（tasks.json 的 JSONP 包装，每次 update 同步）
- `specs/tasks/tasks.html` -- 可视化页面（静态模板，仅首次生成或模板变更时重写）

---

## `/task-list <prd-path>` -- 分析 PRD 生成任务

### Step 1: 读取并理解 PRD

1. 用 Read 工具读取完整 PRD 文档
2. 识别以下结构要素：
   - **阶段/里程碑**：PRD 中的 Phase、Sprint、Milestone 或类似分段
   - **功能模块**：按领域划分的功能组（如"用户管理"、"支付系统"）
   - **MVP 范围**：PRD 中明确标注为 MVP 或第一期的内容
   - **技术架构**：技术选型、数据模型、API 设计等约束
   - **排除项**：明确标注不做或推迟的功能

### Step 1.5: 设计资产扫描与提取

扫描项目中的 UI 设计文件。如果发现 .pen 设计稿但缺少已提取的规格文件，自动提取生成。
设计规格文件（screen-specs、screenshots、design-tokens）是 UI 任务拆分（UI-Layout / UI-Logic）的前提——没有它们，Layout 任务无法引用精确的视觉规格，自主开发循环会产出与设计脱节的 UI。

#### 阶段 A：检查已提取的设计规格

1. 使用 Glob 扫描 `specs/ui/screen-specs/*.md`
2. 如果找到 screen-spec 文件（≥1 个）：
   a. 读取每个 .md 头部提取屏幕名称（`# Screen N — Name`）、平台前缀（`ios-` / `mac-` / `component-`）、关联截图路径（`**Screenshot**: specs/ui/screenshots/XXXXX.png`）
   b. 确认 `specs/ui/design-tokens.md` 存在
   c. 确认 `specs/ui/screenshots/` 下有对应 PNG
   d. 构建屏幕清单：`{ type: "screen_spec", file: "<.md路径>", screenshot: "<.png路径>", screen_name: "<屏幕名>", platform: "ios|mac|component" }`
   e. **跳过阶段 B**（已有完整规格，无需重新提取）

#### 阶段 B：从设计源文件提取规格（仅当阶段 A 未找到规格时）

支持以下设计源（按优先级依次处理）：

**源 1：.pen 文件（Pencil MCP 结构化设计）**
1. 使用 Glob 扫描 `specs/ui/*.pen`、`design/*.pen`
2. 如果找到且 Pencil MCP 可用：
   a. 使用 `open_document` 打开设计文件
   b. 使用 `get_editor_state` 获取所有顶层 frame 列表（id + name）
   c. 对每个 frame，使用 `batch_get`（patterns: `["id=<frame_id>"]`, resolveVariables: true）提取完整节点树（字体、颜色、间距、布局属性）
   d. **生成 3 类文件**：
      - `specs/ui/design-tokens.md`：从所有 frame 数据中汇总提取通用设计令牌（typography scale, color palette, spacing scale, icon system），包含代码片段（如 SwiftUI enum）
      - `specs/ui/screenshots/<frame_id>.png`：对每个 frame 使用 `export_nodes`（nodeIds: [frame_id], format: "png", scale: 2）导出截图（每批 ≤3 个节点，避免超时）
      - `specs/ui/screen-specs/<platform>-<NN>-<name>.md`：每个 frame 一个 markdown 文件，包含 Pencil ID、尺寸、截图路径、完整的层级结构（从节点树转译），每个元素标注精确的字体/颜色/间距/布局值
   e. 文件命名规则：
      - platform 前缀：frame name 含 "iOS"/"iPhone" → `ios-`，含 "mac"/"macOS" → `mac-`，其他 → `component-`
      - 编号：按平台分组从 01 递增
      - name：从 frame name 简化为 kebab-case（如 "iOS — Bookshelf" → `ios-01-bookshelf.md`）
   f. 构建屏幕清单（同阶段 A 格式）

**源 2：UI 设计图片（PNG/JPG/WebP）**（无 .pen 文件时的降级方案）
1. 使用 Glob 扫描 `specs/ui/*.{png,jpg,jpeg,webp}`、`design/*.{png,jpg,jpeg,webp}`
2. 如果找到：
   a. 使用 Read 工具查看图片内容（多模态识别）
   b. 识别图片中的独立屏幕/页面
   c. 为每个识别出的屏幕生成简化版 screen-spec（基于视觉识别，精度低于 .pen 提取）
   d. 将原始图片复制到 `specs/ui/screenshots/` 作为截图
   e. 构建屏幕清单

**源 3：PRD 内嵌 UI 描述**（无图形设计时的最低降级）
1. 如果 PRD 中包含 ASCII mockup、Mermaid UI 图、或详细的 UI 布局描述段落
2. 生成文本描述版 screen-spec（无像素精度，仅结构参考）
3. 构建屏幕清单

如果没有找到任何设计资产，跳过此步骤，后续 UI 任务不拆分 Layout/Logic（向后兼容）。
多种源可以共存（如 .pen 文件 + 补充图片），合并为统一屏幕清单。

### Step 2: 任务分解

按以下规则将 PRD 拆分为具体任务：

**粒度原则**：
- 每个任务代表一个 Claude Code 会话的工作量（可在一次会话中完成）
- 如果一个任务涉及超过 5 个文件，考虑拆分
- 如果一个任务同时包含"搭建基础设施"和"实现功能"，拆为两个任务
- 基础设施/框架任务与业务逻辑任务分开

**分层顺序**（自然的构建顺序）：
1. 项目初始化与基础架构
2. 数据模型与持久层
3. 核心业务逻辑 / 服务层
4. UI 组件与页面
5. 集成与联调
6. 优化与打磨

如果 PRD 已有明确的阶段划分，优先使用 PRD 的阶段结构，在阶段内部再按上述分层拆分。

**分类维度**：
每个任务标注三个维度，用于多角度审查完整性：
- `phase`：项目阶段（来自 PRD）
- `module`：功能模块（如"书架管理"、"阅读引擎"），同一功能不同技术层共享 module
- `tech_layer`：技术层（UI-Layout / UI-Logic / Service / Data / Infra / Integration）

判断标准：
- 主要产出是用户可见界面的视觉布局、样式还原（使用 mock 数据展示） → UI-Layout
- 主要产出是界面的数据绑定、交互逻辑、ViewModel 对接 → UI-Logic
- 主要产出是业务规则、算法、服务接口 → Service
- 主要产出是数据结构、Schema、持久化 → Data
- 主要产出是项目脚手架、构建、部署 → Infra
- 主要产出是对接外部系统或组装多模块 → Integration

一个任务只标一个 tech_layer（取主要产出）。UI-Layout 和 UI-Logic 必须成对出现（见下方 UI 任务拆分规则）。无设计资产时可使用单一 `UI` 层（向后兼容）。

**优先级规则**：
- **P0**：在 MVP 范围内，且在关键路径上（阻塞多个后续任务）
- **P1**：在 MVP 范围内，但可与关键路径并行推进
- **P2**：在产品路线图中但不在 MVP 范围内
- **P3**：Nice-to-have，或 PRD 明确推迟的功能

**依赖关系规则**：
- 数据模型任务在业务逻辑之前
- 业务逻辑在 UI-Layout 之前
- UI-Logic 必须依赖同一功能的 UI-Layout 兄弟任务（先布局正确，再接数据）
- UI-Logic 同时依赖对应的 Service 层任务（需要真实数据源）
- 核心功能在集成功能之前
- 同一阶段内识别可并行的任务（无依赖关系）
- 跨阶段任务通常依赖前一阶段的完成

**验证标准**：
- 每个任务必须有具体、可测试的验证描述
- 优先描述功能行为（"能成功解析 EPUB 文件并提取目录"），避免描述代码结构（"文件已创建"）
- 验证描述应包含以下维度（按任务类型选择适用项）：

  **1. 功能断言**：核心功能的正确性描述
     示例："能创建、查询、更新数据模型，App 重启后数据不丢失"

  **2. Edge Case 枚举**：明确列出必须覆盖的边界情况
     示例："必须覆盖：无封面、无作者、无 TOC、嵌套 TOC（3+ 层）、非 UTF-8 编码、大文件（>50MB）、加密文件（应优雅拒绝）"

  **3. 性能断言**：对有性能要求的任务，给出具体数值门限
     示例："解析 100 本文件元数据 < 5 秒"、"500 条记录筛选 < 50ms"

  **4. 组合/集成测试**：跨功能交互的验证矩阵
     示例："字体切换 × 字号变更 × 行距变更 × 横竖屏，至少 8 种组合"

  **5. 数据完整性**：持久化和恢复的验证
     示例："100 条记录批量保存和恢复无遗漏"、"持久化数据中不含绝对坐标"

  **6. 降级/容错**：异常场景的处理验证
     示例："主方案失效时降级方案能正确工作"、"网络错误时给出明确提示"

  **7. 设计还原验证**（仅 UI-Layout 任务）：将设计规格与实际 UI 进行视觉对比
     - **screen-spec 文件**（首选）：读取任务 `design_spec` 中的 .md 文件获取精确布局规格（间距、颜色、字体等），使用 Read 工具查看 `design_screenshot` 中的 .png 截图获取视觉参考，与实际 UI 截图逐项对比
     - **design-tokens.md**：对比全局设计令牌（字体、颜色、间距）是否正确应用
     - `.pen` 文件（补充）：如 screen-spec 不充分，使用 Pencil MCP `get_screenshot` 获取额外参考
     - 图片文件（补充）：使用 Read 工具查看设计图
     示例："布局结构与 screen-spec 一致、主要间距误差 <4pt、配色与 design-tokens 色值匹配、字体字号与 spec 声明一致"

  P0 任务必须至少覆盖维度 1+2；涉及数据处理的任务加维度 3+5；集成验证任务加维度 4。UI-Layout 任务必须覆盖维度 7。UI-Logic 任务必须覆盖维度 1+2（功能断言 + 边界情况）。

**UI 任务拆分规则（当存在设计资产时）**：

如果 Step 1.5 发现了设计资产（screen-spec 文件或 .pen 文件），每个涉及用户界面的功能**不再创建单一 UI 任务**，而是拆分为 Layout + Logic 一对任务。这解决了自主开发循环中视觉还原与功能逻辑混杂导致的失败问题——Layout 任务用 mock 数据确保视觉保真，Logic 任务在视觉正确的基础上接入真实数据和交互。

- **拆分规则**：每个原本的 UI 任务拆为两个：
  - **UI-Layout 任务**（`T-NNNa` 后缀）：使用 mock/硬编码数据实现视觉布局，目标是像素级还原设计稿
  - **UI-Logic 任务**（`T-NNNb` 后缀）：在 Layout 基础上接入 ViewModel、真实数据绑定、交互逻辑
- **分组规则**：将功能关联的屏幕合并为一对任务（如书架相关的 3-5 个屏幕合为一对 Layout + Logic 任务），避免过碎
- **命名**：
  - Layout: `{功能名} UI — 视图布局`（如 "书架 UI — 视图布局"）
  - Logic: `{功能名} UI — 数据绑定与交互`（如 "书架 UI — 数据绑定与交互"）
- **description**：
  - Layout: 说明需要按设计稿实现布局和样式，使用 mock 数据展示，列出覆盖的屏幕名称
  - Logic: 说明需要替换 mock 数据为真实数据绑定，实现交互逻辑，列出覆盖的交互行为
- **design_spec / design_screenshot**：两个任务都填写相同的设计引用（Layout 用于实现参考，Logic 用于回归验证）
- **依赖**：
  - Layout: 依赖其前置 Service/Data 层任务
  - Logic: 必须依赖同功能的 Layout 兄弟任务（`T-NNNa`），同时依赖对应的 Service 层任务
- **优先级**：Layout 和 Logic 与原 UI 任务同优先级（不降级，因为两者都是必需的）
- **verification**：
  - Layout: 必须包含维度 7（设计还原验证），使用 `design_spec` 和 `design_screenshot` 逐项核对
  - Logic: 必须包含维度 1+2（功能断言 + 边界情况）

如果 Step 1.5 没有发现设计资产，UI 任务不拆分，保持单一 `tech_layer: "UI"` 不变（向后兼容）。

### Step 3: DAG 验证

生成任务后，执行拓扑排序验证：
1. 构建依赖图
2. 检查每个 dependency ID 引用的任务确实存在
3. 检测循环依赖 -- 如果发现则调整依赖关系消除循环
4. 确保存在至少一个根任务（无依赖的起始点）

### Step 4: 生成 tasks.json

将任务写入 `specs/tasks/tasks.json`，使用以下 schema：

```json
{
  "metadata": {
    "project": "<从 PRD 标题提取>",
    "prd_source": "<PRD 文件路径>",
    "generated_at": "<ISO 8601 时间戳>",
    "updated_at": "<ISO 8601 时间戳>",
    "total_tasks": 0
  },
  "tasks": [
    {
      "id": "T-001",
      "name": "任务名称（简洁明确）",
      "description": "任务详细描述，说明需要实现什么、关键技术点",
      "phase": "Phase 1: 阶段名称",
      "module": "模块名称",
      "tech_layer": "Service",
      "priority": "P0",
      "status": "pending",
      "dependencies": [],
      "verification": "具体可测试的验证标准",
      "estimated_effort": "M",
      "files_involved": [],
      "notes": "",
      "design_spec": [],
      "design_screenshot": []
    }
  ]
}
```

**字段说明**：
- `id`：格式 `T-NNN`（普通任务）或 `T-NNNa` / `T-NNNb`（UI Layout/Logic 拆分对）。三位数字从 001 开始，`a` 后缀为 Layout，`b` 后缀为 Logic
- `status`：`pending`（待开始）、`in_progress`（进行中）、`completed`（已完成）、`blocked`（被阻塞）、`skipped`（跳过）
- `estimated_effort`：S（< 2小时）、M（2-4小时）、L（4-8小时）、XL（多会话）
- `files_involved`：预期涉及的文件路径（可选，初始生成时可以为空）
- `notes`：补充说明、注意事项（可选）
- `tech_layer`：技术层分类，标准值：
  - `UI-Layout` — 界面视觉布局、样式还原、mock 数据展示（SwiftUI 视图 + 预览）
  - `UI-Logic` — 界面数据绑定、ViewModel 对接、交互逻辑
  - `UI` — 无设计资产时的 UI 任务（向后兼容，不拆分）
  - `Service` — 业务逻辑、服务层、算法、数据处理
  - `Data` — 数据模型、持久化、数据库 Schema
  - `Infra` — 项目配置、CI/CD、构建系统、基础架构
  - `Integration` — 外部 API 对接、第三方 SDK、跨模块联调
- `design_spec`：设计规格文件路径数组（可选）。格式：`["specs/ui/screen-specs/ios-01-bookshelf.md", ...]`，包含精确的布局、间距、颜色、字体规格。无设计规格时为空数组 `[]`
- `design_screenshot`：设计截图文件路径数组（可选）。格式：`["specs/ui/screenshots/y77r8.png", ...]`，与 design_spec 中的屏幕一一对应。无设计截图时为空数组 `[]`

同时生成 `specs/tasks/tasks-data.js`，内容为：
```js
window.__TASKS_DATA__ = <tasks.json 的完整 JSON 内容>;
```
此文件是 tasks.json 的浏览器可读镜像。每次更新 tasks.json 时必须同步更新此文件。

### Step 5: 生成 HTML 可视化页面

将以下 HTML 写入 `specs/tasks/tasks.html`。HTML 通过 `<script src="tasks-data.js">` 动态加载数据，不内嵌 JSON 内容。HTML 只需生成一次，后续数据变更只需更新 tasks-data.js，浏览器刷新即可看到最新状态。

HTML 页面包含以下部分：

**5.1 仪表盘区域（顶部）**：
- 项目名称 + 生成时间
- 总进度条：已完成 / 总数，百分比
- 四个状态卡片：Pending / In Progress / Completed / Blocked，各带数量和颜色
- 优先级分布柱状图（P0-P3）

**5.2 维度进度（中部）**：
- 顶部 Tab 切换：「按阶段」|「按功能模块」|「按技术层」
- 「按阶段」：每个 phase 一行，阶段名 + 进度条 + 完成数/总数（默认显示）
- 「按功能模块」：每个 module 一行，模块名 + 进度条 + 完成数/总数
- 「按技术层」：每个 tech_layer 一行，层名 + 进度条 + 完成数/总数

**5.3 依赖关系图**：
- 使用 Mermaid.js（CDN：`https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js`）
- 生成 `graph LR` 流程图
- 节点按状态着色：completed=绿色，in_progress=蓝色，pending=灰色，blocked=红色
- 点击节点滚动到对应任务卡片

**5.4 任务卡片列表（底部）**：
- 筛选栏：状态下拉、优先级下拉、阶段下拉、模块下拉、技术层下拉、搜索框
- 每个任务一张卡片，显示：
  - ID + 名称 + 状态徽章 + 优先级徽章
  - 阶段/模块/技术层标签
  - 描述文本
  - 依赖关系（可点击跳转）
  - 验证标准
  - 工作量估算

**HTML 设计要求**：
- 自包含：除 Mermaid CDN 外无外部依赖
- 深色主题为主，浅色主题通过 `prefers-color-scheme` 媒体查询支持
- 使用 CSS Grid + Flexbox 布局
- 使用 CSS custom properties 管理颜色
- 响应式设计，支持移动端查看
- 中文界面

以下是 HTML 模板的关键结构：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>任务看板 — PROJECT_NAME</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <style>
    /* CSS custom properties for theming */
    :root {
      --bg-primary: #1a1a2e;
      --bg-secondary: #16213e;
      --bg-card: #1e2a45;
      --text-primary: #e0e0e0;
      --text-secondary: #a0a0b0;
      --accent: #4fc3f7;
      --success: #66bb6a;
      --warning: #ffa726;
      --danger: #ef5350;
      --info: #42a5f5;
      --pending: #78909c;
      --in-progress: #42a5f5;
      --completed: #66bb6a;
      --blocked: #ef5350;
      --skipped: #9e9e9e;
      --p0: #ef5350;
      --p1: #ffa726;
      --p2: #42a5f5;
      --p3: #78909c;
      --border: #2a3a5e;
      --radius: 8px;
    }
    @media (prefers-color-scheme: light) {
      :root {
        --bg-primary: #f5f5f5;
        --bg-secondary: #ffffff;
        --bg-card: #ffffff;
        --text-primary: #212121;
        --text-secondary: #757575;
        --border: #e0e0e0;
      }
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
    }
    /* ... full styles generated inline ... */
  </style>
</head>
<body>
  <div id="app">
    <header><!-- project name, timestamp --></header>
    <section id="dashboard"><!-- progress bar, status cards, priority chart --></section>
    <section id="phases"><!-- phase progress bars --></section>
    <section id="dependency-graph"><div class="mermaid"><!-- generated --></div></section>
    <section id="filters"><!-- filter controls --></section>
    <section id="task-cards"><!-- task card list --></section>
  </div>
  <script src="tasks-data.js"></script>
  <script>
    const DATA = window.__TASKS_DATA__;
    if (!DATA) {
      document.getElementById('app').innerHTML =
        '<p style="padding:2rem;color:var(--danger)">无法加载 tasks-data.js，请确保该文件与 tasks.html 在同一目录</p>';
    } else {
      // Rendering logic: dashboard, filters, cards, mermaid graph
      mermaid.initialize({ startOnLoad: false, theme: 'dark' });
      // ... rendering functions ...
    }
  </script>
</body>
</html>
```

HTML 通过外部 `tasks-data.js` 加载数据（JSONP 风格，兼容 file:// 协议），不内嵌 JSON。数据更新后浏览器刷新即可，无需重新生成 HTML。

### Step 6: 终端 ASCII 摘要

生成并输出以下格式的终端摘要：

```
================================================================
  TASK LIST — {project}  ·  {prd_source}  ·  {date}
================================================================

  PROGRESS  [##########....................] 12/38 (31%)

  STATUS                     PRIORITY
  + Completed   12           P0  ##############  18
  ~ In Progress  3           P1  ########        10
  . Pending     20           P2  ####             6
  x Blocked      3           P3  ##               4

  PHASE PROGRESS
  Phase 1  基础阅读器     [####################] 5/5  +
  Phase 2  标注系统       [##########..........] 3/6  ~
  Phase 3  样式系统       [####................] 2/5  ~
  Phase 4  书架管理       [....................] 0/7  .

  TECH LAYER
  UI-Layout    [######..............] 3/10
  UI-Logic     [####................] 2/10
  Service      [############........] 6/12
  Data         [####################] 5/5
  Infra        [####################] 3/3
  Integration  [########............] 2/7

  NEXT ACTIONABLE (unblocked, highest priority)
  T-008  P0  WKWebView 渲染层自定义 CSS 注入
  T-009  P0  滚动模式章节无缝衔接
  T-015  P1  SVG 马克笔效果高亮渲染

  Output: specs/tasks/tasks.json
  Visual: specs/tasks/tasks.html (open in browser)
================================================================
```

然后用 `open specs/tasks/tasks.html` 在浏览器中打开可视化页面。

---

## `/task-list status` -- 查看当前状态

1. 读取 `specs/tasks/tasks.json`
2. 输出上述 Step 6 格式的终端 ASCII 摘要（不重新生成文件）

---

## `/task-list update <task-id> <status>` -- 更新任务状态

1. 读取 `specs/tasks/tasks.json`
2. 找到指定 task-id，更新其 status
3. **级联检查**：如果状态变为 `completed`，检查所有 `blocked` 的任务：
   - 如果一个 blocked 任务的所有 dependencies 都已 `completed`，将其状态改为 `pending`
4. 更新 `metadata.updated_at`
5. 写回 `specs/tasks/tasks.json`
6. 同步更新 `specs/tasks/tasks-data.js`（将更新后的 JSON 包装为 `window.__TASKS_DATA__ = ...;`）
7. 输出变更摘要：
```
  T-008 status: pending -> completed
  T-012 unblocked: blocked -> pending (all deps met)
  Updated: specs/tasks/tasks.json + tasks-data.js
  浏览器刷新 tasks.html 即可查看最新状态
```

合法的状态值：`pending`, `in_progress`, `completed`, `blocked`, `skipped`

---

## `/task-list regen` -- 重新生成 HTML 和数据文件

1. 读取 `specs/tasks/tasks.json`
2. 重新生成 `specs/tasks/tasks-data.js`（同步数据镜像）
3. 重新生成 `specs/tasks/tasks.html`（按 Step 5 模板，仅在首次或模板需更新时必要）
4. 用 `open specs/tasks/tasks.html` 打开

---

## `/task-list next` -- 显示下一批可执行任务

1. 读取 `specs/tasks/tasks.json`
2. 筛选条件：status 为 `pending` 且所有 dependencies 的 status 为 `completed`
3. 按优先级排序（P0 > P1 > P2 > P3）
4. 输出前 5 个任务的详细信息：

```
================================================================
  NEXT — 3 actionable tasks
================================================================
  T-008a  P0  阅读界面 UI — 视图布局  [UI-Layout]
          "构建阅读界面基础 UI..."
          deps: T-004 +, T-005 +
          design: ios-02-reader.md, mac-02-reader.md (+1 more)
          verify: 布局与设计稿一致，间距误差 <4pt

  T-009  P0  WKWebView 渲染层自定义 CSS 注入  [Service]
         "实现 WKWebView + 自定义 CSS/JS 注入框架..."
         deps: T-001 +, T-002 +
         verify: WebView 正确渲染 EPUB 章节内容，CSS 覆盖生效

  T-015  P1  SVG 马克笔效果高亮渲染  [Service]
         "在文本下方生成不规则 SVG 路径..."
         deps: T-008 +
         verify: 高亮半透明、不遮挡文字、有手绘感
================================================================
```

输出格式说明：
- 任务名后标注 `[tech_layer]` 标签（如 `[UI-Layout]`、`[Service]`）
- UI-Layout / UI-Logic 任务额外输出 `design:` 行，显示关联的 screen-spec 文件名（超过 3 个时折叠为 `+N more`）

---

## Rules

1. 生成的任务 ID 必须唯一且按顺序递增
2. 依赖关系必须形成有效 DAG（无循环）
3. 每个任务必须有非空的 verification 字段
4. tasks.json 使用 UTF-8 编码
5. HTML 文件除 Mermaid CDN 和同目录的 `tasks-data.js` 外无外部依赖
6. 不要在任务描述中包含具体代码实现，只描述需要做什么
7. 任务名称简洁（不超过 30 个字符），详细信息放在 description 中
8. 每个任务必须标注 phase、module、tech_layer 三个维度，不可为空
9. UI-Layout 和 UI-Logic 必须成对出现，共享 T-NNN 基础编号（a=Layout, b=Logic）
10. UI-Layout 的 design_spec 和 design_screenshot 不可为空
11. UI-Logic 的 dependencies 必须包含其 Layout 兄弟 ID

## Anti-Patterns

- 不要创建粒度过细的任务（如"创建某个文件"），任务应该是功能级别的
- 不要创建没有 design_spec 的 UI-Layout 任务
- 不要在 UI-Layout 中引入真实数据绑定或 ViewModel
- 不要在 UI-Logic 中重做布局
- 不要将 UI-Layout 和 UI-Logic 合并为一个任务
- 不要创建没有验证标准的任务
- 不要让所有任务线性依赖（应识别可并行的任务）
- 不要在任务中混淆"做什么"和"怎么做"，任务描述关注"做什么"
- 不要忽略 PRD 中的非功能需求（性能、安全、兼容性等），它们也应该有对应任务
- 不要写模糊的验证标准（如"功能正常"、"界面正确"），验证标准必须包含具体的 edge case 和可量化的断言
