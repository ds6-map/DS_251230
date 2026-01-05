# API 密钥配置文件
# ⚠️ 此文件包含敏感信息，已在 .gitignore 中，不会被提交到 Git

# OpenAI API 配置
openai_api_key = "sk-cXEECaKlO2W5786tqS4jL8olIiqSh5tJma73IJpkmQjyOiBU"
base_url = "https://api.openai.com/v1"  # OpenAI API 基础 URL，支持自定义端点

# Google Maps API 配置
google_api_key = "AIzaSyCfg5WQ8DO8dL6Xk1BtvatHzJOtNJVmPXY"

# 配置说明：
# 1. 数据库：使用 SQLite，无需配置，数据库文件自动创建在 data/campus_nav.db
# 2. 向量化：使用 ChromaDB，数据自动存储在项目根目录的 chroma/ 文件夹
# 3. 图片数据：放在 image_data/ 目录下，按楼层和区域组织（已有数据）
# 4. 大模型：通过 base_url 配置，支持 OpenAI 官方 API 或兼容的代理 API

