# 配置说明文档

## key.py 文件位置

`key.py` 文件应该放在**项目根目录**（`D:\大模型\12.5_导航\key.py`）

代码会自动从以下位置查找 `key.py`：
1. 项目根目录：`D:\大模型\12.5_导航\key.py`
2. 项目根目录的父目录（作为备选）

## key.py 文件格式

```python
# OpenAI API 配置
openai_api_key = "sk-your-api-key-here"
base_url = "https://api.openai.com/v1"  # 可选，支持自定义 API 端点

# Google Maps API 配置
google_api_key = "AIza-your-api-key-here"
```

## 配置项说明

### 1. **数据库配置** ✅
- **类型**：SQLite（文件数据库）
- **位置**：`backend/data/campus_nav.db`
- **配置**：无需额外配置，自动创建
- **说明**：存储节点、边、地图等数据

### 2. **Google Maps API** ✅
- **用途**：室外导航（Agent Chat 功能）
- **配置**：在 `key.py` 中设置 `google_api_key`
- **说明**：用于 Google Maps 路线规划

### 3. **向量化配置** ✅
- **类型**：ChromaDB
- **位置**：项目根目录的 `chroma/` 文件夹（自动创建）
- **配置**：无需额外配置
- **用途**：图片相似度检索（视觉定位）
- **数据源**：`image_data/` 目录下的图片

### 4. **大模型链接** ✅
- **类型**：OpenAI API（或兼容的 API）
- **配置**：在 `key.py` 中设置：
  - `openai_api_key`：API 密钥
  - `base_url`：API 端点（可选，默认使用官方 API）
- **支持**：
  - OpenAI 官方 API：`https://api.openai.com/v1`
  - 自定义代理 API：如 `https://api.openai-proxy.org/v1`
  - 其他兼容的 API 端点

### 5. **图片数据** ✅
- **位置**：`image_data/` 目录
- **结构**：按楼层和区域组织
  ```
  image_data/
    L1/
      L1_AIA/
      L1_Food/
      ...
    L2/
      ...
  ```
- **用途**：用于视觉定位（拍照识别位置）

## 环境变量配置（可选）

除了 `key.py`，也可以通过环境变量配置：

```bash
# Windows
set OPENAI_API_KEY=sk-your-key
set OPENAI_API_BASE=https://api.openai.com/v1
set GMAPS_API_KEY=AIza-your-key

# Linux/Mac
export OPENAI_API_KEY=sk-your-key
export OPENAI_API_BASE=https://api.openai.com/v1
export GMAPS_API_KEY=AIza-your-key
```

**优先级**：环境变量 > key.py > 默认值

## 安全检查

- ✅ `key.py` 已在 `.gitignore` 中，不会被提交到 Git
- ✅ 建议定期轮换 API 密钥
- ✅ 不要将 `key.py` 分享给他人

## 当前配置状态

根据你提供的 `key.py` 文件：
- ✅ OpenAI API Key：已配置
- ✅ OpenAI Base URL：已配置（`https://api.openai.com/v1`）
- ✅ Google Maps API Key：已配置
- ✅ 数据库：SQLite，自动管理
- ✅ 向量化：ChromaDB，自动管理
- ✅ 图片数据：`image_data/` 目录已有数据

**所有配置项都已就绪！** 🎉

