# 校园室内导航系统

一个移动端优先的校园室内导航 Web 应用，支持视觉定位、路径规划和可视化导航。

## 功能

- **自己定位**：上传周围环境照片，AI 识别当前位置（支持 CLIP + ChromaDB 向量检索）
- **搜索目的地**：输入关键词搜索目标位置，支持模糊匹配
- **路径规划**：使用 A* 算法计算最短路径，支持多楼层导航
- **可视化导航**：在底图上显示节点位置和导航路径，支持 2D 和 3D 视图
- **地图编辑器**：可视化界面标注节点位置，上传底图，支持拖拽编辑
- **智能对话**：集成 OpenAI API 的智能助手，支持自然语言导航查询
- **外部导航**：集成 Google Maps API，支持校园外导航
- **3D 地图视图**：三维地图展示，支持楼层叠加和路径可视化

## 技术栈

### 后端

- **FastAPI** (全异步 Web 框架)
- **SQLAlchemy Async + SQLite** (异步 ORM，文件数据库，无需单独安装)
- **Alembic** (数据库迁移工具)
- **Pydantic V2** (数据验证和序列化)
- **A* 算法** (路径规划，启发式搜索)
- **OpenAI API** (大语言模型集成，支持工具调用)
- **Google Maps API** (外部导航服务)
- **CLIP + ChromaDB** (图像特征提取和向量检索)
- **Pillow** (图像处理)

### 前端

- **Vue 3 + TypeScript + Vite** (现代前端框架，类型安全，快速构建)
- **Vant UI** (移动端优先的组件库)
- **Pinia** (Vue 3 官方状态管理库)
- **Vue Router 4** (前端路由管理)
- **Canvas API + CSS 3D** (2D/3D 地图渲染)
- **Tailwind CSS** (实用优先的 CSS 框架)
- **Axios** (HTTP 客户端)
- **Marked** (Markdown 解析)

## 项目结构

```
├── backend/                          # 后端代码 / Backend Code
│   ├── app/
│   │   ├── main.py                   # FastAPI 应用入口 / FastAPI App Entry
│   │   ├── core/
│   │   │   └── config.py            # 应用配置 / App Configuration
│   │   ├── api/endpoints/            # API 端点 / API Endpoints
│   │   │   ├── navigation.py         # 导航 API / Navigation API
│   │   │   ├── recognition.py        # 图像识别 API / Image Recognition API
│   │   │   ├── maps.py               # 地图管理 API / Maps Management API
│   │   │   └── chat.py               # 智能对话 API / Chat API
│   │   ├── models/                   # 数据库模型 / Database Models
│   │   │   ├── node.py              # 节点模型 / Node Model
│   │   │   ├── edge.py              # 边模型 / Edge Model
│   │   │   └── map.py               # 地图模型 / Map Model
│   │   ├── schemas/                  # Pydantic 模式 / Pydantic Schemas
│   │   ├── services/                 # 业务逻辑服务 / Business Logic Services
│   │   │   ├── graph_service.py     # 图算法和路径规划 / Graph Algorithm & Path Planning
│   │   │   ├── vision_client.py     # 视觉识别服务 / Vision Recognition Service
│   │   │   ├── navigation_client.py # 外部导航客户端 / External Navigation Client
│   │   │   └── ai_service.py        # AI 服务 / AI Service
│   │   ├── utils/
│   │   │   └── navigation_text.py   # 导航文本生成 / Navigation Text Generation
│   │   └── db/
│   │       └── database.py          # 数据库连接 / Database Connection
│   ├── data/                        # 数据存储 / Data Storage
│   │   ├── campus_nav.db           # SQLite 数据库 / SQLite Database
│   │   └── maps/                   # 地图图片存储 / Map Images Storage
│   ├── scripts/                     # 数据导入脚本 / Data Import Scripts
│   │   ├── import_map_data.py      # 地图数据导入 / Map Data Import
│   │   ├── import_nodes_and_edges.py # 智能导入 / Smart Import
│   │   └── export_node_coordinates.py # 坐标导出 / Coordinates Export
│   ├── alembic/                     # 数据库迁移 / Database Migrations
│   ├── requirements.txt             # Python 依赖 / Python Dependencies
│   └── Dockerfile                   # Docker 配置 / Docker Configuration
│
├── frontend/                        # 前端代码 / Frontend Code
│   ├── src/
│   │   ├── main.ts                  # 应用入口 / App Entry
│   │   ├── App.vue                  # 根组件 / Root Component
│   │   ├── api/
│   │   │   └── index.ts            # API 客户端 / API Client
│   │   ├── components/              # 可复用组件 / Reusable Components
│   │   │   ├── Map3DInterface.vue # 3D 地图接口 / 3D Map Interface
│   │   │   ├── AgentChat.vue      # 智能助手聊天 / Agent Chat
│   │   │   ├── NavigationMap.vue   # 导航地图 / Navigation Map
│   │   │   ├── MapCanvas.vue       # 地图画布 / Map Canvas
│   │   │   └── ZoomableMapCanvas.vue # 可缩放地图画布 / Zoomable Map Canvas
│   │   ├── views/                  # 页面视图 / Page Views
│   │   │   ├── Home.vue           # 首页 / Home Page
│   │   │   ├── Navigation.vue     # 导航页面 / Navigation Page
│   │   │   ├── MapEditor.vue      # 地图编辑器 / Map Editor
│   │   │   ├── Map3DView.vue      # 3D 地图视图 / 3D Map View
│   │   │   └── Recognition.vue    # 图像识别页面 / Recognition Page
│   │   ├── stores/                 # Pinia 状态管理 / Pinia State Management
│   │   │   ├── navigation.ts      # 导航状态 / Navigation State
│   │   │   └── editor.ts          # 编辑器状态 / Editor State
│   │   ├── router/
│   │   │   └── index.ts           # 路由配置 / Route Configuration
│   │   └── assets/                 # 静态资源 / Static Assets
│   │       └── maps/               # 地图图片 / Map Images
│   ├── package.json                # Node.js 依赖 / Node.js Dependencies
│   ├── vite.config.ts              # Vite 配置 / Vite Configuration
│   └── tailwind.config.js          # Tailwind 配置 / Tailwind Configuration
│
├── image_data/                     # 图像数据集 / Image Dataset
│   ├── L1/                        # 1 楼图像 / Floor 1 Images
│   ├── L2/                        # 2 楼图像 / Floor 2 Images
│   └── ...                        # 其他楼层 / Other Floors
│
├── chroma/                        # 向量数据库 / Vector Database
├── project1230/                   # 项目数据 / Project Data
├── key.py                        # API 密钥配置 / API Key Configuration
└── README.md                      # 项目文档 / Project Documentation
```

## 快速开始

### 环境要求

- **Python 3.10+** (推荐 3.11)
- **Node.js 18+** (推荐 20+)
- **SQLite 3** (Python 内置，无需单独安装)
- **可选**: CUDA 支持的 GPU (用于 CLIP 模型加速)

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥（必需）
# 复制并编辑 key.py.example 为 key.py
cp key.py.example key.py
# 编辑 key.py，配置 OpenAI API 密钥和 Google Maps API 密钥

# 配置环境变量（可选）
# 创建 .env 文件（如果需要自定义配置）
# DATABASE_URL=sqlite+aiosqlite:///./data/campus_nav.db
# 默认使用 SQLite，无需额外配置

# 导入地图数据
# 方式1：导入单个文件
python scripts/import_map_data.py ../project1230/campus_map.json --clear

# 方式2：批量导入多个文件（推荐）
python scripts/import_map_data_batch.py ../project1230/campus_map.json ../project1230/campus_map_add.json --clear

# 方式3：导入目录下所有 JSON 文件
python scripts/import_map_data_batch.py ../project1230/ --clear

# 方式4：使用通配符导入
python scripts/import_map_data_batch.py ../project1230/*.json --clear

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 或使用 pnpm（如果已安装）
# pnpm install && pnpm dev
```

### 完整启动流程

```bash
# 1. 启动后端服务
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
python scripts/import_map_data_batch.py ../project1230/ --clear
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. 新开终端启动前端服务
cd frontend
npm install
npm run dev
```

### 访问地址

- **前端界面**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs (Swagger UI)
- **健康检查**: http://localhost:8000/health

## API 接口

### 导航 API / Navigation API

- `POST /api/v1/navigation/route` - 计算导航路径 (Calculate navigation route)
- `GET /api/v1/navigation/search` - 搜索节点 (Search nodes)
- `GET /api/v1/navigation/nodes` - 获取所有节点 (Get all nodes)
- `POST /api/v1/navigation/reload` - 重新加载图结构 (Reload graph structure)

### 图像识别 API / Recognition API

- `POST /api/v1/recognition/recognize` - 识别图片位置 (Recognize image location)

### 地图管理 API / Maps API

- `POST /api/v1/maps/upload` - 上传底图 (Upload base map)
- `GET /api/v1/maps/{floor}` - 获取楼层底图 (Get floor base map)
- `GET /api/v1/maps/` - 获取所有底图 (Get all base maps)
- `PUT /api/v1/maps/nodes/{id}/position` - 更新节点坐标 (Update node coordinates)
- `PUT /api/v1/maps/nodes/batch-update` - 批量更新坐标 (Batch update coordinates)

### 智能对话 API / Chat API

- `POST /api/chat` - 智能对话 (Intelligent chat)
- `GET /api/status` - 服务状态 (Service status)
- `GET /api/config` - 配置信息 (Configuration info)

## 数据格式

### 地图数据 JSON 格式 (campus_map.json)

```json
{
  "nodes": [
    {
      "id": "LT5",
      "name": "LectureTheater5",
      "detail": "NS2-02-07",
      "floor": 2
    }
  ],
  "edges": [
    {
      "from": "LT5",
      "to": "LT6",
      "weight": 20
    }
  ]
}
```

## 使用流程

### 1. 数据准备 / Data Preparation

**导入地图数据**：

- 使用 `scripts/import_map_data_batch.py` 批量导入 JSON 文件
- 支持多个文件、目录导入和通配符匹配
- 数据包含节点（位置）和边（连接关系）

### 2. 地图配置 / Map Configuration

**上传底图**：

- 在地图编辑器页面上传各楼层的底图图片（PNG/JPG）
- 系统自动识别图片尺寸并存储

**标注节点位置**：

- 在编辑器中可视化拖拽节点到地图上的正确位置
- 支持单个节点和批量更新坐标
- 坐标基于像素位置（左上角为原点）

### 3. AI 模型准备 / AI Model Preparation

**图像识别设置**：

- 系统自动下载 CLIP 模型用于图像特征提取
- 构建 ChromaDB 向量数据库存储位置特征
- 支持 Mock 模式（开发测试用）

### 4. 使用导航 / Using Navigation

**基本导航**：

- 在首页输入目的地关键词
- 系统计算并显示最短路径
- 支持 2D 和 3D 地图视图

**智能对话导航**：

- 使用智能助手进行自然语言查询
- 支持复杂导航需求（如"去最近的咖啡店"）
- 集成外部Google Map导航服务

**视觉定位**：

- 上传环境照片进行位置识别
- 返回多个候选位置供用户选择

## 开发说明

### 添加新节点 / Add New Nodes

1. 编辑 JSON 文件添加节点和边数据
2. 运行导入脚本更新数据库
3. 在地图编辑器中设置节点坐标

### AI 识别模块 / AI Recognition Module

**当前实现**：

- 使用 CLIP (openai/clip-vit-base-patch32) 提取图像特征
- ChromaDB 向量数据库进行相似度检索
- 支持 Top-K 候选位置返回

**Mock 模式**：

- 开发时可启用 Mock 模式跳过模型加载
- 返回随机候选位置用于界面测试

### 智能对话功能 / Intelligent Chat Feature

**工具调用 / Tool Calling**：

- 路径规划工具：计算导航路径
- 节点搜索工具：查找位置信息
- 外部导航工具：Google Maps 集成

**对话流程**：

- 用户自然语言输入
- LLM 理解意图并决定工具调用
- 执行相应功能返回结果
- 生成自然语言回复

## 部署和扩展 / Deployment & Scaling

### 开发环境 / Development

- 使用 `uvicorn --reload` 自动重载后端代码
- 前端使用 Vite 热重载开发服务器
- 支持前后端分离开发和调试

### 生产部署 / Production

**推荐配置**：

- 使用 Nginx 作为反向代理
- 配置 SSL 证书
- 设置适当的环境变量
- 考虑使用 Docker 容器化部署

### 性能优化 / Performance Optimization

- 图结构缓存到内存中
- 异步 I/O 处理提高并发
- ChromaDB 向量检索优化
- 前端虚拟滚动处理大数据

### 扩展性 / Scalability

**数据库扩展**：

- 可迁移到 PostgreSQL 支持更大规模
- 添加 Redis 缓存层

**AI 服务扩展**：

- 图像识别服务可独立部署
- 支持 GPU 加速推理
- 考虑分布式向量检索

## 故障排除 / Troubleshooting

### 常见问题 / Common Issues

**后端启动失败**：

- 检查 Python 版本 (3.10+)
- 确认依赖安装完成
- 验证 API 密钥配置

**前端构建失败**：

- 检查 Node.js 版本 (18+)
- 清理 node_modules 重新安装
- 检查网络连接

**地图不显示**：

- 确认底图已上传
- 检查节点坐标是否设置
- 验证图片格式和大小

填补方向参考：

- 集成 CLIP 模型进行视觉特征提取
- 使用 FAISS 进行向量检索
- 添加 OCR 识别辅助

## License

MIT
