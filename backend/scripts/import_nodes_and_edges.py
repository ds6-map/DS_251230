"""
智能导入节点和边数据的脚本
- 添加新节点（如果不存在）
- 更新现有节点的基本信息（name, detail, floor, type），但保留坐标
- 更新或添加边数据
- 不会覆盖已有节点的坐标
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from app.db import AsyncSessionLocal, init_db
from app.models import Node, Edge, NodeType, EdgeType


async def import_nodes_and_edges(
    json_file: str,
    clear_edges: bool = False,
    preserve_coordinates: bool = True
):
    """
    智能导入节点和边数据
    
    Args:
        json_file: JSON 文件路径
        clear_edges: 是否清除现有边数据
        preserve_coordinates: 是否保留已有节点的坐标（默认 True）
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
            # 清除现有边数据（如果指定）
            if clear_edges:
                print("🗑️  清除现有边数据...")
                await session.execute(delete(Edge))
                await session.commit()
                print("✅ 现有边数据已清除")
            
            # 导入节点
            print("📥 导入节点...")
            new_nodes = 0
            updated_nodes = 0
            skipped_coordinates = 0
            
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
                    
                    # 只有在 preserve_coordinates=False 或 JSON 中明确提供了坐标时才更新坐标
                    if not preserve_coordinates:
                        if 'x' in node_data:
                            existing_node.x = node_data['x']
                        if 'y' in node_data:
                            existing_node.y = node_data['y']
                    elif 'x' in node_data and 'y' in node_data:
                        # JSON 中有坐标，但 preserve_coordinates=True，跳过
                        skipped_coordinates += 1
                        print(f"   ⚠️  节点 {node_id} 已有坐标，跳过 JSON 中的坐标数据")
                    
                    updated_nodes += 1
                else:
                    # 创建新节点
                    # 新节点可以使用 JSON 中的坐标（如果有）
                    node = Node(
                        id=node_id,
                        name=node_data.get('name', node_id),
                        detail=node_data.get('detail'),
                        floor=node_data.get('floor', 1),
                        x=node_data.get('x'),  # 新节点可以使用坐标
                        y=node_data.get('y'),  # 新节点可以使用坐标
                        node_type=node_type,
                    )
                    session.add(node)
                    new_nodes += 1
            
            await session.commit()
            print(f"✅ 节点导入完成:")
            print(f"   - 新增: {new_nodes}")
            print(f"   - 更新: {updated_nodes}")
            if skipped_coordinates > 0:
                print(f"   - 保留坐标: {skipped_coordinates} 个节点")
            
            # 导入边
            print("📥 导入边...")
            imported_edges = 0
            updated_edges = 0
            error_edges = []
            
            for edge_data in edges_data:
                from_id = edge_data.get('from')
                to_id = edge_data.get('to')
                
                if not from_id or not to_id:
                    print(f"⚠️  跳过无效边: {edge_data}")
                    error_edges.append(f"无效边: {edge_data}")
                    continue
                
                # 验证节点是否存在
                from_node = await session.execute(
                    select(Node).where(Node.id == from_id)
                )
                to_node = await session.execute(
                    select(Node).where(Node.id == to_id)
                )
                
                if not from_node.scalar_one_or_none():
                    error_msg = f"节点不存在: {from_id}"
                    print(f"⚠️  {error_msg}")
                    error_edges.append(error_msg)
                    continue
                
                if not to_node.scalar_one_or_none():
                    error_msg = f"节点不存在: {to_id}"
                    print(f"⚠️  {error_msg}")
                    error_edges.append(error_msg)
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
                    updated_edges += 1
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
            print(f"✅ 边导入完成:")
            print(f"   - 新增: {imported_edges}")
            print(f"   - 更新: {updated_edges}")
            
            if error_edges:
                print(f"⚠️  错误/警告 ({len(error_edges)} 条):")
                for err in error_edges[:10]:  # 只显示前10条
                    print(f"   - {err}")
                if len(error_edges) > 10:
                    print(f"   ... 还有 {len(error_edges) - 10} 条错误")
            
            print("🎉 数据导入完成!")
            if preserve_coordinates:
                print("   ✅ 已有节点的坐标已保留")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 导入失败: {e}")
            raise


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='智能导入节点和边数据（保留已有节点坐标）'
    )
    parser.add_argument(
        'json_file',
        help='JSON 数据文件路径'
    )
    parser.add_argument(
        '--clear-edges',
        action='store_true',
        help='清除现有边数据后再导入'
    )
    parser.add_argument(
        '--allow-coordinate-overwrite',
        action='store_true',
        help='允许覆盖已有节点的坐标（默认保留坐标）'
    )
    
    args = parser.parse_args()
    
    preserve_coordinates = not args.allow_coordinate_overwrite
    
    await import_nodes_and_edges(
        args.json_file,
        clear_edges=args.clear_edges,
        preserve_coordinates=preserve_coordinates
    )


if __name__ == "__main__":
    asyncio.run(main())


