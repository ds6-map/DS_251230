# 项目规格书：校园室内导航系统 (Project Specification)

## 1. 项目概述 (Project Overview)

构建**移动端优先的校园室内导航 Web 应用**。
系统核心功能包括：

1. **自我定位**：用户上传一张周围环境的照片（如教室门口、走廊路口、地标），系统识别当前位置。
2. **搜索目的地**：用户输入关键词（如"304室"、"男洗手间"）。
3. **获取导航**：基于室内地图的拓扑结构，利用 A* 算法计算最短路径并进行导航。
4. **可视化地图**：在底图上显示节点位置和导航路径，提供直观的可视化导航体验。
5. **地图编辑器**：管理员通过可视化界面标注节点位置，上传底图并设置节点坐标。

## 2. 技术栈 (Tech Stack)

### 后端 (Python)

* **框架**：FastAPI (全异步架构)。
* **数据库**： PostgreSQL ，用 **SQLAlchemy (Async)** + **Alembic** 进行迁移管理。
* **数据校验**：Pydantic V2。
* **文件存储**：服务器本地文件系统（存储底图文件）。
* **AI/机器学习**：
* **视觉定位**：`sentence-transformers` (CLIP 模型) 或 `transformers` 库，用于提取图像向量特征。
* **向量检索**：FAISS (如果在节点<1000的情况下，也可以写简单的余弦相似度计算)。
* **OCR**：PaddleOCR (作为可选的辅助识别手段)。
* **路径规划**：自定义 Python 实现的 **A* (A-Star)** 算法。
* **图像处理**：Pillow (PIL)。

### 前端 (Web)

* **框架**：Vue 3 (Composition API) + TypeScript + Vite。
* **UI 组件库**：Vant UI (专为移动端设计)。
* **状态管理**：Pinia。
* **HTTP 客户端**：Axios。
* **可视化**：Canvas API（用于地图渲染和路径绘制）。
* **拖拽交互**：`vue-draggable` 或 `@dnd-kit/core`（用于编辑器节点拖拽）。

---

## 3. 目录结构 (Directory Structure)

基于以下结构构建项目脚手架：

```text
root/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 启动入口
│   │   ├── core/              # 全局配置, 安全设置, 事件处理
│   │   ├── api/               # 路由层 (v1)
│   │   │   ├── endpoints/
│   │   │   │   ├── navigation.py  # 路径规划相关接口 (Route)
│   │   │   │   ├── recognition.py # 图片上传与 AI 识别接口
│   │   │   │   └── maps.py        # 地图和编辑器相关接口
│   │   ├── models/            # SQLAlchemy 数据库模型 (Table定义)
│   │   ├── schemas/           # Pydantic 数据传输对象 (DTO)
│   │   ├── services/
│   │   │   ├── graph_service.py   # A* 算法实现与图结构逻辑
│   │   │   ├── ai_service.py      # CLIP 模型加载与 FAISS 检索逻辑
│   │   │   └── map_service.py     # 地图文件上传和管理逻辑
│   │   ├── utils/             # 工具函数
│   │   │   └── navigation_text.py # 导航指令生成工具
│   │   └── db/                # 数据库连接与 Session 管理
│   ├── data/                  # 存放地图原始图片和向量索引文件
│   │   └── maps/              # 底图文件存储目录
│   ├── scripts/               # 数据导入脚本
│   │   └── import_map_data.py # JSON 数据导入脚本
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── api/               # Axios 请求封装
│   │   ├── components/        # 可复用的 Vue 组件
│   │   │   ├── MapCanvas.vue      # 地图 Canvas 渲染组件
│   │   │   └── NavigationMap.vue  # 导航地图可视化组件
│   │   ├── views/             # 页面视图
│   │   │   ├── Home.vue           # 首页 (搜索目的地)
│   │   │   ├── Recognition.vue    # 定位确认页
│   │   │   ├── Navigation.vue     # 导航结果页
│   │   │   └── MapEditor.vue      # 地图编辑器页面（公开页面，无需登录）
│   │   ├── stores/            # Pinia 状态库 (存储当前位置, 地图数据)
│   │   ├── assets/
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.ts
└── README.md

```

---

## 4. 核心功能与实现细节 (Core Features)

### 功能 A：基于图的地图系统 (Graph-Based Map System)

* **数据模型**：
* `Map` (地图): 楼层, 底图URL, 底图宽度, 底图高度。
* `Node` (节点): ID, 名称, 楼层, 坐标_X, 坐标_Y (像素坐标，相对于底图), 详细位置, 类型 (教室, 楼梯, 电梯, 走廊)。
* `Edge` (边): 起点ID, 终点ID, 权重 (距离), 边类型 (normal/stairs/lifts), 是否垂直 (用于标记楼梯/电梯)。
* **数据来源**：
* 节点和边的数据通过 JSON 文件手动录入（格式参考 `campus_map.json`）。
* 节点坐标 (x, y) 通过地图编辑器可视化标注获得。
* **算法逻辑**：
* 在 `graph_service.py` 中实现 **A* (A-Star)** 算法。
* 启发函数 (Heuristic)：计算当前节点到目标节点的欧几里得距离。
* **重要**：为了性能，应用启动时应将图结构从数据库加载到内存（字典或邻接表）中。

### 功能 B：视觉定位 (Visual Positioning - AI)

* **业务逻辑**：

1. 用户调用接口 `POST /api/v1/recognize` 上传图片。
2. 后端接收图片。
3. **步骤 1 (OCR - 占位/可选)**：尝试识别图中文字（如 "305"）。如果置信度高，直接返回对应节点。
4. **步骤 2 (视觉检索)**：

* 使用预加载的 CLIP 模型 (如 `openai/clip-vit-base-patch32`) 将图片转为向量。
* 将向量与预存的节点向量库进行比对 (Simulated 或 FAISS)。

5. **响应**：返回可能性最高的 Top 3 个节点及其置信度分数。

### 功能 C：导航与路径规划 (Navigation)

* **接口**：`POST /api/v1/route`
* **输入参数**：`start_node_id` (起点ID), `target_name` (模糊搜索的目标名)。
* **处理流程**：

1. 根据名称模糊匹配找到 `target_node_id`。
2. 运行 A* 算法计算路径。
3. 返回数据包括：
   * 节点列表 (Path)：路径上的所有节点ID。
   * 节点详细信息：包含坐标 (x, y)、名称、楼层等。
   * 总距离：路径总权重。
   * 分步文字导航指令（如"直行 10 米"，"在前方楼梯上 2 楼"）。
   * 涉及的楼层列表：用于前端切换底图显示。

* **辅助接口**：
* `GET /api/v1/maps/:floor`：获取指定楼层的底图信息（URL、尺寸等）。
* `GET /api/v1/nodes?floor=:floor`：获取指定楼层的所有节点（包含坐标）。

### 功能 D：移动端前端 (Mobile Frontend)

* **关键页面**：

1. **首页 (Home)**：包含巨大的"我在哪？"按钮 (调起相机) 和"去哪里？"搜索框。
2. **确认位置 (Confirm Location)**：展示 AI 返回的 Top 3 结果卡片，用户点击确认。
3. **导航视图 (Navigation View)**：展示路径和可视化地图。
   * 显示对应楼层的底图（从学校地图软件截图获得）。
   * 在底图上绘制所有节点位置（根据保存的坐标）。
   * 高亮显示导航路径（红色连线，起点绿色，终点红色）。
   * 显示分步文字导航指令（时间轴样式）。

### 功能 E：可视化地图 (Visual Map Display)

* **功能描述**：
* 在导航结果页面显示可视化地图，提供直观的导航体验。
* 底图来源：从学校地图软件截图，通过编辑器上传。
* **实现细节**：

1. **底图加载**：根据导航路径涉及的楼层，加载对应的底图。
2. **节点渲染**：根据数据库中保存的节点坐标 (x, y)，在底图上绘制节点标记。
3. **路径高亮**：根据导航算法返回的路径，在底图上绘制高亮连线。
   * 起点：绿色圆点标记
   * 终点：红色圆点标记
   * 路径：红色粗线连接
   * 中间节点：灰色半透明圆点
4. **跨楼层处理**：如果路径涉及多个楼层，需要切换底图显示或分楼层展示。

* **技术实现**：
* 使用 Canvas API 进行地图渲染。
* 支持底图缩放和平移（可选，根据需求）。
* 响应式设计，适配移动端屏幕。

### 功能 F：地图编辑器 (Map Editor)

* **功能描述**：
* 公开页面，无需用户登录验证。
* 管理员通过可视化界面标注节点位置，上传底图并设置节点坐标。
* **核心功能**：

1. **底图管理**：

   * 上传底图文件（PNG/JPG格式，从学校地图软件截图）。
   * 按楼层管理底图（每层一张底图）。
   * 显示底图尺寸信息（宽度、高度）。
2. **节点标注**：

   * 在底图上显示该楼层的所有节点（可拖拽的圆点）。
   * 支持拖拽节点到正确位置（对应地图上的实际位置）。
   * 实时显示节点坐标（x, y，相对于底图的像素坐标）。
   * 双击节点可编辑节点信息（可选功能）。
3. **坐标保存**：

   * 支持单个节点坐标保存。
   * 支持批量保存所有节点坐标。
   * 坐标格式：像素坐标（相对于底图左上角为原点 (0, 0)）。
4. **界面功能**：

   * 楼层选择下拉框（切换不同楼层进行编辑）。
   * 节点列表显示（显示所有节点及其坐标状态）。
   * 保存按钮（保存当前楼层的所有节点坐标）。

* **API 接口**：
* `POST /api/admin/maps/upload`：上传底图文件。
* `GET /api/admin/maps/:floor`：获取指定楼层的底图信息。
* `GET /api/admin/nodes?floor=:floor`：获取指定楼层的所有节点。
* `PUT /api/admin/nodes/:id/position`：更新单个节点的坐标。
* `PUT /api/admin/nodes/batch-update`：批量更新节点坐标。
* **技术实现**：
* 使用 Vue 3 + Canvas API 或 SVG 进行底图渲染。
* 使用拖拽库（`vue-draggable` 或 `@dnd-kit/core`）实现节点拖拽。
* 文件上传使用 FormData + multipart/form-data。

---

## 5. 编码规范 (Strict Requirements)

1. **类型提示**：所有 Python 代码必须使用严格的 Type Hints (例如 `def get_path(start: str) -> List[Node]:`)。
2. **异步编程**：所有 FastAPI 路由处理函数和数据库 IO 操作必须使用 `async def` / `await`。
3. **注释**：对复杂逻辑（特别是 A* 算法核心、向量检索部分、地图渲染逻辑）必须添加清晰的 Docstrings。
4. **AI Mock**：由于目前没有训练好的权重，请构建完整的 `ai_service.py` 结构，但内部逻辑可以使用 **Mock 数据** 或者自动下载 HuggingFace 的标准 CLIP 模型进行演示。
5. **错误处理**：优雅地处理"路径不存在 (Path not found)"、"图片无法识别"、"底图不存在"、"节点坐标未设置"等异常情况。
6. **文件存储**：底图文件存储在服务器本地文件系统（`backend/data/maps/` 目录），通过静态文件服务提供访问。
7. **权限控制**：地图编辑器为公开页面，无需用户登录验证。未来如需添加权限控制，可通过环境变量配置。
