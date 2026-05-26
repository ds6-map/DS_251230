# 项目架构总结 / Project Architecture Summary

## 项目概述 / Project Overview

**中文：** 校园室内导航系统是一个基于 Web 的智能导航应用，支持视觉定位、路径规划和可视化导航。系统采用前后端分离架构，后端使用 FastAPI 提供 RESTful API，前端使用 Vue 3 构建响应式用户界面。

**English:** Campus Indoor Navigation System is a web-based intelligent navigation application that supports visual positioning, route planning, and visual navigation. The system adopts a frontend-backend separation architecture, with FastAPI providing RESTful APIs on the backend and Vue 3 building responsive user interfaces on the frontend.

---

## 技术栈 / Technology Stack

### 后端 / Backend

| 技术                       | 用途               | Technology       | Purpose                           |
| -------------------------- | ------------------ | ---------------- | --------------------------------- |
| **FastAPI**          | 异步 Web 框架      | FastAPI          | Async Web Framework               |
| **SQLAlchemy Async** | 异步 ORM           | SQLAlchemy Async | Async ORM                         |
| **SQLite**           | 轻量级数据库       | SQLite           | Lightweight Database              |
| **Alembic**          | 数据库迁移工具     | Alembic          | Database Migration Tool           |
| **Pydantic V2**      | 数据验证和序列化   | Pydantic V2      | Data Validation & Serialization   |
| **A* 算法**            | 路径规划算法       | A* Algorithm     | Path Planning Algorithm           |
| **OpenAI API**       | 大语言模型集成     | OpenAI API       | LLM Integration                   |
| **Google Maps API**  | 外部导航服务       | Google Maps API  | External Navigation Service       |
| **CLIP + ChromaDB**  | 图像识别和向量检索 | CLIP + ChromaDB  | Image Recognition & Vector Search |

### 前端 / Frontend

| 技术                   | 用途                  | Technology   | Purpose                        |
| ---------------------- | --------------------- | ------------ | ------------------------------ |
| **Vue 3**        | 渐进式前端框架        | Vue 3        | Progressive Frontend Framework |
| **TypeScript**   | 类型安全的 JavaScript | TypeScript   | Type-safe JavaScript           |
| **Vite**         | 快速构建工具          | Vite         | Fast Build Tool                |
| **Vant UI**      | 移动端组件库          | Vant UI      | Mobile Component Library       |
| **Pinia**        | 状态管理              | Pinia        | State Management               |
| **Vue Router**   | 路由管理              | Vue Router   | Route Management               |
| **Canvas API**   | 地图渲染              | Canvas API   | Map Rendering                  |
| **Tailwind CSS** | 实用优先的 CSS 框架   | Tailwind CSS | Utility-first CSS Framework    |

---

## 系统架构 / System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 / Frontend Layer                │
├─────────────────────────────────────────────────────────────┤
│  Vue 3 + TypeScript + Vite                                   │
│  ├── 视图层 / Views (Home, Navigation, MapEditor, etc.)     │
│  ├── 组件层 / Components (Map3D, AgentChat, etc.)          │
│  ├── 状态管理 / State Management (Pinia Stores)             │
│  └── API 封装 / API Wrapper                                 │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/REST API
┌─────────────────────────────────────────────────────────────┐
│                        后端层 / Backend Layer                 │
├─────────────────────────────────────────────────────────────┤
│  FastAPI (Async)                                             │
│  ├── API 路由 / API Routes                                   │
│  │   ├── /api/v1/navigation/*  (导航相关)                   │
│  │   ├── /api/v1/recognition/* (图像识别)                   │
│  │   ├── /api/v1/maps/*       (地图管理)                    │
│  │   └── /api/chat            (智能对话)                    │
│  ├── 服务层 / Services                                       │
│  │   ├── GraphService        (图算法和路径规划)             │
│  │   ├── VisionClient        (图像识别)                     │
│  │   ├── NavigationClient    (外部导航服务)                 │
│  │   └── AIService           (AI 服务)                      │
│  └── 数据层 / Data Layer                                     │
│      ├── Models (SQLAlchemy ORM)                             │
│      ├── Schemas (Pydantic)                                  │
│      └── Database (SQLite)                                   │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    外部服务 / External Services              │
├─────────────────────────────────────────────────────────────┤
│  ├── OpenAI API (大语言模型)                                 │
│  ├── Google Maps API (外部导航)                              │
│  └── ChromaDB (向量数据库)                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 目录结构 / Directory Structure

```
项目根目录 / Project Root
│
├── backend/                          # 后端代码 / Backend Code
│   ├── app/
│   │   ├── main.py                   # FastAPI 应用入口 / FastAPI App Entry
│   │   ├── core/                     # 核心配置 / Core Configuration
│   │   │   └── config.py            # 应用配置 / App Configuration
│   │   ├── api/                      # API 路由 / API Routes
│   │   │   └── endpoints/            # 端点定义 / Endpoint Definitions
│   │   │       ├── navigation.py     # 导航 API / Navigation API
│   │   │       ├── recognition.py   # 识别 API / Recognition API
│   │   │       ├── maps.py           # 地图 API / Maps API
│   │   │       └── chat.py           # 聊天 API / Chat API
│   │   ├── models/                   # 数据库模型 / Database Models
│   │   │   ├── node.py              # 节点模型 / Node Model
│   │   │   ├── edge.py              # 边模型 / Edge Model
│   │   │   └── map.py               # 地图模型 / Map Model
│   │   ├── schemas/                  # Pydantic 模式 / Pydantic Schemas
│   │   │   ├── navigation.py        # 导航模式 / Navigation Schema
│   │   │   ├── recognition.py      # 识别模式 / Recognition Schema
│   │   │   └── ...
│   │   ├── services/                 # 业务逻辑层 / Business Logic Layer
│   │   │   ├── graph_service.py    # 图算法服务 / Graph Algorithm Service
│   │   │   ├── vision_client.py    # 视觉识别服务 / Vision Recognition Service
│   │   │   ├── navigation_client.py # 导航客户端 / Navigation Client
│   │   │   └── ai_service.py       # AI 服务 / AI Service
│   │   ├── utils/                    # 工具函数 / Utility Functions
│   │   │   └── navigation_text.py   # 导航文本生成 / Navigation Text Generation
│   │   └── db/                       # 数据库连接 / Database Connection
│   │       └── database.py          # 数据库配置 / Database Configuration
│   ├── scripts/                      # 数据导入脚本 / Data Import Scripts
│   │   ├── import_map_data.py       # 导入地图数据 / Import Map Data
│   │   ├── import_nodes_and_edges.py # 智能导入 / Smart Import
│   │   └── export_node_coordinates.py # 导出坐标 / Export Coordinates
│   ├── data/                         # 数据目录 / Data Directory
│   │   ├── campus_nav.db            # SQLite 数据库 / SQLite Database
│   │   └── maps/                     # 地图图片存储 / Map Images Storage
│   ├── alembic/                      # 数据库迁移 / Database Migrations
│   └── requirements.txt               # Python 依赖 / Python Dependencies
│
├── frontend/                         # 前端代码 / Frontend Code
│   ├── src/
│   │   ├── main.ts                   # 应用入口 / App Entry
│   │   ├── App.vue                   # 根组件 / Root Component
│   │   ├── api/                      # API 封装 / API Wrapper
│   │   │   └── index.ts             # API 客户端 / API Client
│   │   ├── views/                    # 页面视图 / Page Views
│   │   │   ├── Home.vue             # 首页 / Home Page
│   │   │   ├── Navigation.vue       # 导航页 / Navigation Page
│   │   │   ├── MapEditor.vue        # 地图编辑器 / Map Editor
│   │   │   ├── Map3DView.vue        # 3D 地图视图 / 3D Map View
│   │   │   └── Recognition.vue      # 识别页 / Recognition Page
│   │   ├── components/               # 可复用组件 / Reusable Components
│   │   │   ├── Map3DInterface.vue  # 3D 地图接口 / 3D Map Interface
│   │   │   ├── AgentChat.vue       # 智能助手聊天 / Agent Chat
│   │   │   ├── NavigationMap.vue    # 导航地图 / Navigation Map
│   │   │   └── ZoomableMapCanvas.vue # 可缩放地图画布 / Zoomable Map Canvas
│   │   ├── stores/                   # Pinia 状态管理 / Pinia State Management
│   │   │   ├── navigation.ts        # 导航状态 / Navigation State
│   │   │   └── editor.ts            # 编辑器状态 / Editor State
│   │   ├── router/                   # 路由配置 / Route Configuration
│   │   │   └── index.ts             # 路由定义 / Route Definitions
│   │   └── assets/                   # 静态资源 / Static Assets
│   │       └── maps/                 # 地图图片 / Map Images
│   └── package.json                  # Node.js 依赖 / Node.js Dependencies
│
├── image_data/                       # 图像数据集 / Image Dataset
│   ├── L1/                          # 1 楼图像 / Floor 1 Images
│   ├── L2/                          # 2 楼图像 / Floor 2 Images
│   └── ...                          # 其他楼层 / Other Floors
│
├── project1230/                      # 项目数据 / Project Data
│   └── campus_map.json              # 地图数据 JSON / Map Data JSON
│
└── README.md                         # 项目说明 / Project Documentation
```

---

## 核心模块 / Core Modules

### 1. 图服务模块 / Graph Service Module

**中文：** 实现 A* 路径规划算法，管理图结构（节点和边），提供最短路径计算功能。

**English:** Implements A* path planning algorithm, manages graph structure (nodes and edges), and provides shortest path calculation functionality.

**关键功能 / Key Features:**

- 图结构加载和缓存 / Graph structure loading and caching
- A* 算法路径规划 / A* algorithm path planning
- 多楼层路径支持 / Multi-floor path support
- 节点搜索功能 / Node search functionality

**文件位置 / File Location:** `backend/app/services/graph_service.py`

### 2. 视觉识别模块 / Vision Recognition Module

**中文：** 使用 CLIP 模型进行图像特征提取，通过 ChromaDB 进行向量检索，实现基于图像的室内定位。

**English:** Uses CLIP model for image feature extraction, performs vector search through ChromaDB, and implements image-based indoor positioning.

**关键功能 / Key Features:**

- CLIP 模型图像编码 / CLIP model image encoding
- 向量数据库检索 / Vector database search
- 相似度计算和排序 / Similarity calculation and ranking
- 多候选位置返回 / Multiple candidate location returns

**文件位置 / File Location:** `backend/app/services/vision_client.py`

### 3. 导航客户端模块 / Navigation Client Module

**中文：** 集成 Google Maps API，提供外部导航服务，支持多种交通方式（驾车、步行、公共交通等）。

**English:** Integrates Google Maps API, provides external navigation services, and supports multiple transportation modes (driving, walking, transit, etc.).

**关键功能 / Key Features:**

- Google Maps 路线规划 / Google Maps route planning
- 自然语言解析 / Natural language parsing
- 多种交通方式支持 / Multiple transportation mode support

**文件位置 / File Location:** `backend/app/services/navigation_client.py`

### 4. AI 服务模块 / AI Service Module

**中文：** 集成 OpenAI API，提供智能对话和自然语言理解功能，支持工具调用（Tool Calling）。

**English:** Integrates OpenAI API, provides intelligent conversation and natural language understanding, and supports tool calling.

**关键功能 / Key Features:**

- LLM 对话管理 / LLM conversation management
- 工具调用集成 / Tool calling integration
- 上下文管理 / Context management

**文件位置 / File Location:** `backend/app/services/ai_service.py`

### 5. 3D 地图组件 / 3D Map Component

**中文：** 使用 Canvas API 和 CSS 3D 变换实现三维地图可视化，支持楼层切换、路径显示和交互操作。

**English:** Uses Canvas API and CSS 3D transforms to implement 3D map visualization, supports floor switching, path display, and interactive operations.

**关键功能 / Key Features:**

- 3D 场景渲染 / 3D scene rendering
- 楼层叠加显示 / Floor overlay display
- 路径可视化 / Path visualization
- 交互式控制 / Interactive controls

**文件位置 / File Location:** `frontend/src/components/Map3DInterface.vue`

---

## 数据流 / Data Flow

### 路径规划流程 / Path Planning Flow

```
用户输入起点和终点
User Inputs Start & End Points
         ↓
前端发送 API 请求
Frontend Sends API Request
         ↓
后端 GraphService 加载图结构
Backend GraphService Loads Graph Structure
         ↓
A* 算法计算最短路径
A* Algorithm Calculates Shortest Path
         ↓
生成导航步骤和指令
Generate Navigation Steps & Instructions
         ↓
返回路径数据给前端
Return Path Data to Frontend
         ↓
前端在地图上渲染路径
Frontend Renders Path on Map
```

### 图像识别流程 / Image Recognition Flow

```
用户上传图片
User Uploads Image
         ↓
前端发送 Base64 编码图片
Frontend Sends Base64 Encoded Image
         ↓
后端 VisionClient 处理图片
Backend VisionClient Processes Image
         ↓
CLIP 模型提取特征向量
CLIP Model Extracts Feature Vector
         ↓
ChromaDB 向量检索相似位置
ChromaDB Vector Search for Similar Locations
         ↓
返回候选位置列表
Return Candidate Location List
         ↓
前端显示识别结果
Frontend Displays Recognition Results
```

### 智能对话流程 / Intelligent Chat Flow

```
用户发送消息
User Sends Message
         ↓
前端发送到 /api/chat
Frontend Sends to /api/chat
         ↓
后端调用 OpenAI API
Backend Calls OpenAI API
         ↓
LLM 分析意图并决定是否调用工具
LLM Analyzes Intent & Decides Tool Calling
         ↓
如果调用导航工具，执行路径规划
If Navigation Tool Called, Execute Path Planning
         ↓
LLM 生成自然语言回复
LLM Generates Natural Language Reply
         ↓
返回回复和路线数据
Return Reply & Route Data
         ↓
前端显示对话和地图
Frontend Displays Chat & Map
```

---

## API 设计 / API Design

### 导航 API / Navigation API

| 端点                          | 方法 | 说明           | Endpoint                      | Method | Description                |
| ----------------------------- | ---- | -------------- | ----------------------------- | ------ | -------------------------- |
| `/api/v1/navigation/route`  | POST | 计算导航路径   | `/api/v1/navigation/route`  | POST   | Calculate navigation route |
| `/api/v1/navigation/search` | GET  | 搜索节点       | `/api/v1/navigation/search` | GET    | Search nodes               |
| `/api/v1/navigation/nodes`  | GET  | 获取所有节点   | `/api/v1/navigation/nodes`  | GET    | Get all nodes              |
| `/api/v1/navigation/reload` | POST | 重新加载图结构 | `/api/v1/navigation/reload` | POST   | Reload graph structure     |

### 识别 API / Recognition API

| 端点                              | 方法 | 说明         | Endpoint                          | Method | Description              |
| --------------------------------- | ---- | ------------ | --------------------------------- | ------ | ------------------------ |
| `/api/v1/recognition/recognize` | POST | 识别图片位置 | `/api/v1/recognition/recognize` | POST   | Recognize image location |

### 地图 API / Maps API

| 端点                                 | 方法 | 说明         | Endpoint                             | Method | Description             |
| ------------------------------------ | ---- | ------------ | ------------------------------------ | ------ | ----------------------- |
| `/api/v1/maps/upload`              | POST | 上传底图     | `/api/v1/maps/upload`              | POST   | Upload base map         |
| `/api/v1/maps/{floor}`             | GET  | 获取楼层底图 | `/api/v1/maps/{floor}`             | GET    | Get floor base map      |
| `/api/v1/maps/nodes/{id}/position` | PUT  | 更新节点坐标 | `/api/v1/maps/nodes/{id}/position` | PUT    | Update node coordinates |

### 聊天 API / Chat API

| 端点            | 方法 | 说明     | Endpoint        | Method | Description        |
| --------------- | ---- | -------- | --------------- | ------ | ------------------ |
| `/api/chat`   | POST | 智能对话 | `/api/chat`   | POST   | Intelligent chat   |
| `/api/status` | GET  | 服务状态 | `/api/status` | GET    | Service status     |
| `/api/config` | GET  | 配置信息 | `/api/config` | GET    | Configuration info |

---

## 数据库设计 / Database Design

### 节点表 / Nodes Table

| 字段          | 类型        | 说明         | Field         | Type        | Description                   |
| ------------- | ----------- | ------------ | ------------- | ----------- | ----------------------------- |
| `id`        | String(50)  | 节点唯一标识 | `id`        | String(50)  | Unique node identifier        |
| `name`      | String(100) | 节点名称     | `name`      | String(100) | Node name                     |
| `detail`    | String(200) | 详细位置描述 | `detail`    | String(200) | Detailed location description |
| `floor`     | Integer     | 所在楼层     | `floor`     | Integer     | Floor number                  |
| `x`         | Float       | X 坐标       | `x`         | Float       | X coordinate                  |
| `y`         | Float       | Y 坐标       | `y`         | Float       | Y coordinate                  |
| `node_type` | Enum        | 节点类型     | `node_type` | Enum        | Node type                     |

### 边表 / Edges Table

| 字段             | 类型       | 说明         | Field            | Type       | Description          |
| ---------------- | ---------- | ------------ | ---------------- | ---------- | -------------------- |
| `id`           | Integer    | 主键         | `id`           | Integer    | Primary key          |
| `from_node_id` | String(50) | 起点节点 ID  | `from_node_id` | String(50) | Start node ID        |
| `to_node_id`   | String(50) | 终点节点 ID  | `to_node_id`   | String(50) | End node ID          |
| `weight`       | Float      | 权重（距离） | `weight`       | Float      | Weight (distance)    |
| `edge_type`    | Enum       | 边类型       | `edge_type`    | Enum       | Edge type            |
| `is_vertical`  | Boolean    | 是否垂直移动 | `is_vertical`  | Boolean    | Is vertical movement |

### 地图表 / Maps Table

| 字段           | 类型        | 说明     | Field          | Type        | Description  |
| -------------- | ----------- | -------- | -------------- | ----------- | ------------ |
| `id`         | Integer     | 主键     | `id`         | Integer     | Primary key  |
| `floor`      | Integer     | 楼层     | `floor`      | Integer     | Floor number |
| `image_path` | String(500) | 图片路径 | `image_path` | String(500) | Image path   |
| `width`      | Integer     | 图片宽度 | `width`      | Integer     | Image width  |
| `height`     | Integer     | 图片高度 | `height`     | Integer     | Image height |

---

## 前端架构 / Frontend Architecture

### 组件层次结构 / Component Hierarchy

```
App.vue (根组件 / Root Component)
├── RouterView
│   ├── Home.vue (首页 / Home Page)
│   │   └── AgentChat.vue (智能助手 / Agent Chat)
│   ├── Navigation.vue (导航页 / Navigation Page)
│   │   └── NavigationMap.vue (导航地图 / Navigation Map)
│   ├── MapEditor.vue (地图编辑器 / Map Editor)
│   │   └── ZoomableMapCanvas.vue (可缩放画布 / Zoomable Canvas)
│   ├── Map3DView.vue (3D 地图视图 / 3D Map View)
│   │   └── Map3DInterface.vue (3D 地图接口 / 3D Map Interface)
│   └── Recognition.vue (识别页 / Recognition Page)
```

### 状态管理 / State Management

**导航状态 / Navigation State** (`stores/navigation.ts`)

- 当前路径 / Current route
- 搜索历史 / Search history
- 节点缓存 / Node cache

**编辑器状态 / Editor State** (`stores/editor.ts`)

- 当前编辑的节点 / Currently editing node
- 地图缩放状态 / Map zoom state
- 未保存的更改 / Unsaved changes

---

## 后端架构 / Backend Architecture

### 分层架构 / Layered Architecture

1. **API 层 / API Layer** (`app/api/endpoints/`)

   - 处理 HTTP 请求 / Handle HTTP requests
   - 参数验证 / Parameter validation
   - 响应格式化 / Response formatting
2. **服务层 / Service Layer** (`app/services/`)

   - 业务逻辑实现 / Business logic implementation
   - 算法执行 / Algorithm execution
   - 外部服务集成 / External service integration
3. **数据访问层 / Data Access Layer** (`app/models/`, `app/db/`)

   - 数据库模型定义 / Database model definitions
   - ORM 操作 / ORM operations
   - 数据持久化 / Data persistence

### 异步处理 / Async Processing

- 所有数据库操作使用异步 / All database operations use async
- FastAPI 异步路由处理 / FastAPI async route handling
- 外部 API 调用使用异步 HTTP 客户端 / External API calls use async HTTP clients

---

## 部署架构 / Deployment Architecture

### 开发环境 / Development Environment

```
前端开发服务器 (Vite)
Frontend Dev Server (Vite)
  └── http://localhost:5173

后端开发服务器 (Uvicorn)
Backend Dev Server (Uvicorn)
  └── http://localhost:8000
```

### 生产环境建议 / Production Environment Recommendations

```
┌─────────────────┐
│   Nginx (反向代理) │
│  Nginx (Reverse  │
│      Proxy)      │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ 前端   │ │ 后端   │
│Frontend│ │Backend │
│ (静态) │ │(FastAPI)│
└────────┘ └────────┘
```

---

## 关键技术决策 / Key Technical Decisions

### 1. 为什么选择 SQLite？

**中文：** SQLite 是轻量级文件数据库，无需单独安装数据库服务器，适合中小型项目快速部署。

**English:** SQLite is a lightweight file database that doesn't require a separate database server installation, making it suitable for rapid deployment of small to medium-sized projects.

### 2. 为什么使用 A* 算法？

**中文：** A* 算法在保证最优解的同时具有较好的性能，适合室内导航场景。

**English:** The A* algorithm provides optimal solutions while maintaining good performance, making it suitable for indoor navigation scenarios.

### 3. 为什么前后端分离？

**中文：** 前后端分离便于独立开发、测试和部署，支持多端复用 API。

**English:** Frontend-backend separation facilitates independent development, testing, and deployment, and supports multi-platform API reuse.

### 4. 为什么使用异步架构？

**中文：** 异步架构提高并发处理能力，特别适合 I/O 密集型操作（数据库查询、外部 API 调用）。

**English:** Async architecture improves concurrent processing capabilities, especially suitable for I/O-intensive operations (database queries, external API calls).

---

## 扩展性考虑 / Scalability Considerations

### 当前限制 / Current Limitations

- SQLite 适合单机部署，不适合高并发场景
- 图像识别依赖本地 CLIP 模型，需要 GPU 支持
- 图结构存储在内存中，节点数量有限制

### 未来改进方向 / Future Improvement Directions

- 迁移到 PostgreSQL 或 MySQL 支持更大规模数据
- 使用 Redis 缓存热点数据
- 图像识别服务独立部署，支持分布式处理
- 引入消息队列处理异步任务

---

## 安全考虑 / Security Considerations

- API 密钥存储在 `key.py` 文件中，不应提交到版本控制
- 使用 CORS 中间件限制跨域访问
- 文件上传需要验证文件类型和大小
- 敏感操作需要身份验证（当前版本未实现）

---

## 性能优化 / Performance Optimization

- 图结构加载到内存缓存，避免频繁数据库查询
- 使用异步 I/O 提高并发处理能力
- 前端使用虚拟滚动处理大量节点列表
- 地图图片使用 Canvas 渲染，支持硬件加速

---

## 总结 / Summary

**中文：** 本项目采用现代化的前后端分离架构，使用 FastAPI 和 Vue 3 构建了一个功能完整的校园室内导航系统。系统支持视觉定位、路径规划、智能对话等多种功能，具有良好的扩展性和可维护性。

**English:** This project adopts a modern frontend-backend separation architecture, using FastAPI and Vue 3 to build a fully functional campus indoor navigation system. The system supports various features including visual positioning, path planning, and intelligent conversation, with good scalability and maintainability.

---

**最后更新 / Last Updated:** 2025-01-09
**版本 / Version:** 1.0.0
