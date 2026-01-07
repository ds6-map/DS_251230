# 修改边信息同时保留节点坐标的解决方案

## 问题描述

当你需要修改 `campus_map.json` 中的边（edges）信息时，希望保留已经在地图编辑器中手动放置好的节点坐标（x, y），避免重新放置所有节点。

## 解决方案

### 方案 1：智能导入节点和边（最推荐）⭐⭐⭐

**优点**：最灵活，可以同时添加新节点和更新边，自动保留已有节点坐标

**步骤**：

1. **修改 `campus_map.json`**：
   - 添加新节点到 `nodes` 数组（新节点可以包含 `x`, `y` 坐标）
   - 修改或添加边到 `edges` 数组

2. **使用智能导入脚本**：
```bash
cd backend
python scripts/import_nodes_and_edges.py ../project1230/campus_map.json
```

3. **如果需要清除所有旧边后重新导入**：
```bash
python scripts/import_nodes_and_edges.py ../project1230/campus_map.json --clear-edges
```

**工作原理**：
- ✅ **新节点**：会创建，可以使用 JSON 中的坐标（如果有）
- ✅ **已有节点**：更新基本信息（name, detail, floor, type），**自动保留坐标**
- ✅ **边**：更新或新增

**注意事项**：
- 默认会保留已有节点的坐标，即使 JSON 中有 `x`, `y` 也会被忽略
- 如果需要覆盖坐标，使用 `--allow-coordinate-overwrite` 参数
- 确保所有边引用的节点都已存在（新节点会在导入时创建）

---

### 方案 1b：只导入边数据（仅修改边时使用）⭐

**优点**：最简单、最安全，不会影响节点坐标

**步骤**：

1. **备份当前节点坐标**（可选但推荐）：
```bash
cd backend
python scripts/export_node_coordinates.py export
```
这会生成一个备份文件，如 `node_coordinates_backup_20250101_120000.json`

2. **修改 `campus_map.json`**，只修改 `edges` 部分，不要修改 `nodes` 部分

3. **只导入边数据**：
```bash
cd backend
python scripts/import_edges_only.py ../project1230/campus_map.json
```

4. **如果需要清除所有旧边后重新导入**：
```bash
python scripts/import_edges_only.py ../project1230/campus_map.json --clear-edges
```

**注意事项**：
- 确保 JSON 中所有边引用的节点都已存在于数据库中
- 如果边引用了不存在的节点，会显示警告并跳过该边

---

### 方案 2：使用标准导入脚本（已保护坐标）

**优点**：使用现有脚本，自动保护坐标

**步骤**：

1. **修改 `campus_map.json`**，可以同时修改 `nodes` 和 `edges`

2. **导入数据**（不添加 `--clear` 参数）：
```bash
cd backend
python scripts/import_map_data.py ../project1230/campus_map.json
```

**工作原理**：
- 导入脚本在更新已存在的节点时，**会自动保留已有的坐标**
- 只有新节点或 JSON 中明确提供了 `x`, `y` 的节点才会设置坐标
- 边会被更新或新增

**注意事项**：
- 如果 JSON 中的节点有 `x`, `y` 字段，会覆盖数据库中的坐标
- 建议在 JSON 中**不要包含** `x`, `y` 字段，只保留节点定义信息

---

### 方案 3：备份和恢复机制

**优点**：最安全，可以随时恢复

**完整流程**：

1. **导出当前坐标**：
```bash
cd backend
python scripts/export_node_coordinates.py export coordinates_backup.json
```

2. **修改 `campus_map.json`**，可以任意修改

3. **导入数据**（如果需要清除旧数据）：
```bash
python scripts/import_map_data.py ../project1230/campus_map.json --clear
```

4. **恢复坐标**：
```bash
python scripts/export_node_coordinates.py restore coordinates_backup.json
```

---

### 方案 4：分离节点和边文件（长期方案）

**优点**：最灵活，适合频繁修改边信息

**建议的文件结构**：

```
project1230/
  ├── nodes.json          # 只包含节点定义（不含坐标）
  ├── edges.json          # 只包含边定义
  └── coordinates.json    # 节点坐标（从数据库导出）
```

**工作流程**：
1. 节点定义很少变化，放在 `nodes.json`
2. 边信息经常修改，放在 `edges.json`
3. 坐标信息从数据库导出，单独管理

**实现**：需要修改导入脚本支持分别导入节点和边

---

### 方案 5：通过 API 直接更新边（开发中）

**优点**：不需要重启服务，实时更新

**实现方式**：
- 创建专门的 API 端点 `/api/v1/maps/edges/update`
- 接受边数据并批量更新
- 不影响节点数据

---

## 推荐工作流程

### 日常修改边信息：

```bash
# 1. 修改 campus_map.json 中的 edges 部分

# 2. 只导入边数据
cd backend
python scripts/import_edges_only.py ../project1230/campus_map.json

# 3. 重新加载图数据（如果后端正在运行）
# 通过 API: POST /api/v1/navigation/reload
# 或重启后端服务
```

### 添加新节点和边（推荐）⭐：

```bash
# 1. 在 campus_map.json 中添加新节点（可以包含 x, y，但已有节点会保留坐标）
# 2. 添加或修改边

# 3. 使用智能导入脚本（自动保留已有节点坐标）
cd backend
python scripts/import_nodes_and_edges.py ../project1230/campus_map.json

# 4. 在地图编辑器中为新节点设置坐标（如果 JSON 中没有提供）
```

### 添加新节点和边（旧方法）：

```bash
# 1. 在 campus_map.json 中添加新节点（不要包含 x, y）
# 2. 添加新边

# 3. 导入数据（不添加 --clear）
cd backend
python scripts/import_map_data.py ../project1230/campus_map.json

# 4. 在地图编辑器中为新节点设置坐标
```

### 完全重置（清除所有数据）：

```bash
# 1. 先备份坐标
python scripts/export_node_coordinates.py export

# 2. 清除并导入
python scripts/import_map_data.py ../project1230/campus_map.json --clear

# 3. 恢复坐标
python scripts/export_node_coordinates.py restore node_coordinates_backup_*.json
```

---

## 注意事项

1. **JSON 格式**：确保 `campus_map.json` 是有效的 JSON 格式
2. **节点 ID**：边中引用的节点 ID 必须在 `nodes` 中存在
3. **坐标字段**：在 JSON 中**不要包含** `x`, `y` 字段，除非你想覆盖已有坐标
4. **备份**：重要操作前建议先备份坐标
5. **图缓存**：导入后需要重新加载图数据（通过 `/reload` API 或重启服务）

---

## 快速参考

| 操作 | 命令 |
|------|------|
| **智能导入（推荐）** | `python scripts/import_nodes_and_edges.py <json_file>` |
| 只导入边 | `python scripts/import_edges_only.py <json_file>` |
| 导入节点和边（旧方法） | `python scripts/import_map_data.py <json_file>` |
| 清除边后导入 | `python scripts/import_nodes_and_edges.py <json_file> --clear-edges` |
| 清除所有后导入 | `python scripts/import_map_data.py <json_file> --clear` |
| 导出坐标 | `python scripts/export_node_coordinates.py export` |
| 恢复坐标 | `python scripts/export_node_coordinates.py restore <backup_file>` |

