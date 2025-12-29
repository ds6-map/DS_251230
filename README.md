# 校园室内导航系统

一个移动端优先的校园室内导航 Web 应用，支持视觉定位、路径规划和可视化导航。

## 功能特性

- **自我定位**：上传周围环境照片，AI 识别当前位置
- **搜索目的地**：输入关键词搜索目标位置
- **路径规划**：使用 A* 算法计算最短路径
- **可视化导航**：在底图上显示节点位置和导航路径
- **地图编辑器**：可视化界面标注节点位置，上传底图

## 技术栈

### 后端

- FastAPI (异步框架)
- PostgreSQL + SQLAlchemy Async
- Alembic (数据库迁移)
- Pydantic V2 (数据校验)
- A* 算法 (路径规划)

### 前端

- Vue 3 + TypeScript + Vite
- Vant UI (移动端组件库)
- Pinia (状态管理)
- Canvas API (地图渲染)

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── core/             # 配置
│   │   ├── api/              # API 路由
│   │   ├── models/           # 数据库模型
│   │   ├── schemas/          # Pydantic 模型
│   │   ├── services/         # 业务逻辑
│   │   ├── utils/            # 工具函数
│   │   └── db/               # 数据库连接
│   ├── data/maps/            # 底图存储
│   ├── scripts/              # 数据导入脚本
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/              # API 封装
│   │   ├── components/       # Vue 组件
│   │   ├── views/            # 页面
│   │   ├── stores/           # Pinia 状态
│   │   └── assets/           # 静态资源
│   └── package.json
│
└── README.md
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（创建 .env 文件）
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/campus_nav

# 初始化数据库（首次运行）
# 需要先创建数据库：CREATE DATABASE campus_nav;

# 导入地图数据
python scripts/import_map_data.py ../campus_map.json --clear

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
```

### 访问地址

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## API 接口

### 导航相关

- `POST /api/v1/navigation/route` - 计算导航路径
- `GET /api/v1/navigation/search` - 搜索节点
- `GET /api/v1/navigation/nodes` - 获取所有节点
- `POST /api/v1/navigation/reload` - 重新加载图结构

### 图像识别

- `POST /api/v1/recognition/recognize` - 识别图片位置

### 地图管理

- `POST /api/v1/maps/upload` - 上传底图
- `GET /api/v1/maps/{floor}` - 获取楼层底图
- `GET /api/v1/maps/` - 获取所有底图
- `PUT /api/v1/maps/nodes/{id}/position` - 更新节点坐标
- `PUT /api/v1/maps/nodes/batch-update` - 批量更新坐标

## 数据格式

地图数据 JSON 格式 (campus_map.json):

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
      "weight": 20,
      "type": "normal"
    }
  ]
}
```

## 使用流程

1. **导入节点和边数据**：运行 `import_map_data.py` 脚本
2. **上传底图**：在编辑器页面上传各楼层的底图截图
3. **标注节点位置**：在编辑器中拖拽节点到正确位置
4. **使用导航**：在首页搜索目的地，开始导航

## 开发说明

### 添加新节点

1. 编辑 `campus_map.json` 添加节点和边
2. 运行导入脚本：`python scripts/import_map_data.py campus_map.json`
3. 在编辑器中设置节点坐标

### AI 识别模块

当前为 Mock 实现，返回随机候选位置。

未来计划：

- 集成 CLIP 模型进行视觉特征提取
- 使用 FAISS 进行向量检索
- 添加 OCR 识别辅助

## License

MIT
