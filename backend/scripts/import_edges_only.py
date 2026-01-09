"""
只导入边数据的脚本
从 JSON 文件导入边数据，不修改节点信息（保留节点坐标）
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
from app.models import Node, Edge, EdgeType


async def import_edges_only(json_file: str, clear_edges: bool = False):
    """
    从 JSON 文件只导入边数据，不修改节点信息
    
    Args:
        json_file: JSON 文件路径
        clear_edges: 是否清除现有边数据
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
    
    edges_data = data.get('edges', [])
    
    print(f"📊 发现 {len(edges_data)} 条边")
    
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
            
            # 导入边
            print("📥 导入边...")
            imported_edges = 0
            updated_edges = 0
            skipped_edges = 0
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
            print(f"   - 跳过: {skipped_edges}")
            
            if error_edges:
                print(f"⚠️  错误/警告 ({len(error_edges)} 条):")
                for err in error_edges[:10]:  # 只显示前10条
                    print(f"   - {err}")
                if len(error_edges) > 10:
                    print(f"   ... 还有 {len(error_edges) - 10} 条错误")
            
            print("🎉 边数据导入完成! (节点坐标已保留)")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 导入失败: {e}")
            raise


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='只导入边数据到数据库（保留节点坐标）')
    parser.add_argument(
        'json_file',
        help='JSON 数据文件路径'
    )
    parser.add_argument(
        '--clear-edges',
        action='store_true',
        help='清除现有边数据后再导入'
    )
    
    args = parser.parse_args()
    
    await import_edges_only(args.json_file, args.clear_edges)


if __name__ == "__main__":
    asyncio.run(main())

