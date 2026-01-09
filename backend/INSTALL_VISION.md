# 图片识别功能安装指南

## 问题

如果遇到错误：`VISION_ERR_BACKEND_MISSING`，说明缺少图片识别所需的依赖包。

## 安装步骤

### 方法 1：安装所有依赖（推荐）

```bash
cd backend
pip install -r requirements.txt
```

### 方法 2：仅安装图片识别依赖

如果只需要图片识别功能，可以单独安装：

```bash
cd backend
pip install chromadb==0.3.23
pip install langchain-experimental==0.4.1
pip install open-clip-torch==3.2.0
pip install torch torchvision
```

### 方法 3：使用 CPU 版本的 PyTorch（如果 GPU 版本安装失败）

```bash
cd backend
pip install chromadb==0.3.23
pip install langchain-experimental==0.4.1
pip install open-clip-torch==3.2.0
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

## 注意事项

1. **PyTorch 安装**：
   - 如果有 NVIDIA GPU，可以安装 GPU 版本以获得更好的性能
   - 如果没有 GPU 或安装失败，使用 CPU 版本即可
   - CPU 版本安装命令：`pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`

2. **依赖大小**：
   - 这些包比较大（特别是 torch），首次安装可能需要较长时间
   - 建议使用国内镜像加速：
     ```bash
     pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
     ```

3. **验证安装**：
   安装完成后，重启后端服务器，再次尝试上传图片识别。

## 如果不需要图片识别功能

如果暂时不需要图片识别功能，可以：
1. 不安装这些依赖
2. 图片识别功能会返回友好的错误提示
3. 其他功能（导航、对话等）不受影响

