"""
数据导入脚本
从 JSON 文件导入节点和边数据到数据库
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from app.db import AsyncSessionLocal, init_db
from app.models import Node, Edge, NodeType, EdgeType


async def import_map_data(json_file: str, clear_existing: bool = False):
    """
    从 JSON 文件导入地图数据
    
    Args:
        json_file: JSON 文件路径
        clear_existing: 是否清除现有数据
    """
    # 读取 JSON 文件
    print(f"📖 读取文件: {json_file}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 文件不存在: {json_file}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {e}")
        return
    
    nodes_data = data.get('nodes', [])
    edges_data = data.get('edges', [])
    
    print(f"📊 发现 {len(nodes_data)} 个节点, {len(edges_data)} 条边")
    
    # 初始化数据库
    await init_db()
    
    async with AsyncSessionLocal() as session:
        try:
            # 清除现有数据（如果指定）
            if clear_existing:
                print("🗑️  清除现有数据...")
                await session.execute(delete(Edge))
                await session.execute(delete(Node))
                await session.commit()
                print("✅ 现有数据已清除")
            
            # 导入节点
            print("📥 导入节点...")
            imported_nodes = 0
            skipped_nodes = 0
            
            for node_data in nodes_data:
                node_id = node_data.get('id')
                
                if not node_id:
                    print(f"⚠️  跳过无效节点: {node_data}")
                    continue
                
                # 检查节点是否已存在
                result = await session.execute(
                    select(Node).where(Node.id == node_id)
                )
                existing_node = result.scalar_one_or_none()
                
                # 推断节点类型
                node_type = NodeType.OTHER.value
                name_upper = node_data.get('name', '').upper()
                id_upper = node_id.upper()
                
                if 'STAIR' in id_upper or 'STAIR' in name_upper:
                    node_type = NodeType.STAIRS.value
                elif 'LIFT' in id_upper or 'ELEVATOR' in name_upper:
                    node_type = NodeType.LIFT.value
                elif 'RESTROOM' in name_upper or 'TOILET' in name_upper:
                    node_type = NodeType.RESTROOM.value
                elif 'ENTRANCE' in name_upper or 'GATE' in name_upper:
                    node_type = NodeType.ENTRANCE.value
                elif 'CORRIDOR' in name_upper or 'HALL' in name_upper:
                    node_type = NodeType.CORRIDOR.value
                else:
                    node_type = NodeType.CLASSROOM.value
                
                if existing_node:
                    # 更新现有节点（保留坐标）
                    existing_node.name = node_data.get('name', node_id)
                    existing_node.detail = node_data.get('detail')
                    existing_node.floor = node_data.get('floor', 1)
                    existing_node.node_type = node_type
                    # 如果 JSON 中有坐标，更新坐标
                    if 'x' in node_data:
                        existing_node.x = node_data['x']
                    if 'y' in node_data:
                        existing_node.y = node_data['y']
                    skipped_nodes += 1
                else:
                    # 创建新节点
                    node = Node(
                        id=node_id,
                        name=node_data.get('name', node_id),
                        detail=node_data.get('detail'),
                        floor=node_data.get('floor', 1),
                        x=node_data.get('x'),
                        y=node_data.get('y'),
                        node_type=node_type,
                    )
                    session.add(node)
                    imported_nodes += 1
            
            await session.commit()
            print(f"✅ 节点导入完成: 新增 {imported_nodes}, 更新 {skipped_nodes}")
            
            # 导入边
            print("📥 导入边...")
            imported_edges = 0
            skipped_edges = 0
            
            for edge_data in edges_data:
                from_id = edge_data.get('from')
                to_id = edge_data.get('to')
                
                if not from_id or not to_id:
                    print(f"⚠️  跳过无效边: {edge_data}")
                    continue
                
                # 检查边是否已存在
                result = await session.execute(
                    select(Edge).where(
                        Edge.from_node_id == from_id,
                        Edge.to_node_id == to_id
                    )
                )
                existing_edge = result.scalar_one_or_none()
                
                # 确定边类型
                edge_type = edge_data.get('type', 'normal')
                if edge_type not in [e.value for e in EdgeType]:
                    edge_type = EdgeType.NORMAL.value
                
                # 判断是否为垂直移动
                is_vertical = edge_type in [EdgeType.STAIRS.value, EdgeType.LIFTS.value]
                
                if existing_edge:
                    # 更新现有边
                    existing_edge.weight = edge_data.get('weight', 1.0)
                    existing_edge.edge_type = edge_type
                    existing_edge.is_vertical = is_vertical
                    skipped_edges += 1
                else:
                    # 创建新边
                    edge = Edge(
                        from_node_id=from_id,
                        to_node_id=to_id,
                        weight=edge_data.get('weight', 1.0),
                        edge_type=edge_type,
                        is_vertical=is_vertical,
                    )
                    session.add(edge)
                    imported_edges += 1
            
            await session.commit()
            print(f"✅ 边导入完成: 新增 {imported_edges}, 更新 {skipped_edges}")
            
            print("🎉 数据导入完成!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 导入失败: {e}")
            raise


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='导入地图数据到数据库')
    parser.add_argument(
        'json_file',
        help='JSON 数据文件路径'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='清除现有数据后再导入'
    )
    
    args = parser.parse_args()
    
    await import_map_data(args.json_file, args.clear)


if __name__ == "__main__":
    asyncio.run(main())

