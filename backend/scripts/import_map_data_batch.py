"""
批量数据导入脚本
支持从多个 JSON 文件或目录批量导入节点和边数据到数据库
"""
import asyncio
import json
import sys
import os
import glob
from pathlib import Path
from typing import List

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from app.db import AsyncSessionLocal, init_db
from app.models import Node, Edge, NodeType, EdgeType


async def import_map_data(json_file: str, clear_existing: bool = False, verbose: bool = True):
    """
    从 JSON 文件导入地图数据
    
    Args:
        json_file: JSON 文件路径
        clear_existing: 是否清除现有数据（只在第一个文件时生效）
        verbose: 是否显示详细信息
    """
    # 读取 JSON 文件
    if verbose:
        print(f"\n📖 读取文件: {json_file}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 文件不存在: {json_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误 ({json_file}): {e}")
        return False
    
    nodes_data = data.get('nodes', [])
    edges_data = data.get('edges', [])
    
    if verbose:
        print(f"📊 发现 {len(nodes_data)} 个节点, {len(edges_data)} 条边")
    
    async with AsyncSessionLocal() as session:
        try:
            # 清除现有数据（只在第一次导入时）
            if clear_existing:
                if verbose:
                    print("🗑️  清除现有数据...")
                await session.execute(delete(Edge))
                await session.execute(delete(Node))
                await session.commit()
                if verbose:
                    print("✅ 现有数据已清除")
            
            # 导入节点
            if verbose:
                print("📥 导入节点...")
            imported_nodes = 0
            updated_nodes = 0
            skipped_nodes = 0
            
            for node_data in nodes_data:
                node_id = node_data.get('id')
                
                if not node_id:
                    if verbose:
                        print(f"⚠️  跳过无效节点: {node_data}")
                    skipped_nodes += 1
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
                    updated_nodes += 1
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
            if verbose:
                print(f"✅ 节点导入完成: 新增 {imported_nodes}, 更新 {updated_nodes}, 跳过 {skipped_nodes}")
            
            # 导入边
            if verbose:
                print("📥 导入边...")
            imported_edges = 0
            updated_edges = 0
            skipped_edges = 0
            
            for edge_data in edges_data:
                from_id = edge_data.get('from')
                to_id = edge_data.get('to')
                
                if not from_id or not to_id:
                    if verbose:
                        print(f"⚠️  跳过无效边: {edge_data}")
                    skipped_edges += 1
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
            if verbose:
                print(f"✅ 边导入完成: 新增 {imported_edges}, 更新 {updated_edges}, 跳过 {skipped_edges}")
            
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 导入失败 ({json_file}): {e}")
            return False


def find_json_files(paths: List[str]) -> List[str]:
    """
    查找所有 JSON 文件
    
    Args:
        paths: 文件路径或目录路径列表，支持通配符
        
    Returns:
        JSON 文件路径列表
    """
    json_files = []
    
    for path_str in paths:
        path = Path(path_str)
        
        # 如果是文件，直接添加
        if path.is_file():
            if path.suffix.lower() == '.json':
                json_files.append(str(path.resolve()))
            else:
                print(f"⚠️  跳过非 JSON 文件: {path_str}")
        
        # 如果是目录，查找所有 JSON 文件
        elif path.is_dir():
            json_files.extend([
                str(p.resolve()) 
                for p in path.rglob('*.json')
            ])
        
        # 如果是通配符模式
        elif '*' in path_str or '?' in path_str:
            matched = glob.glob(path_str, recursive=True)
            json_files.extend([
                str(Path(f).resolve())
                for f in matched
                if Path(f).suffix.lower() == '.json'
            ])
        
        else:
            print(f"⚠️  路径不存在: {path_str}")
    
    # 去重并排序
    json_files = sorted(list(set(json_files)))
    return json_files


async def batch_import(
    paths: List[str],
    clear_existing: bool = False,
    verbose: bool = True
):
    """
    批量导入多个 JSON 文件
    
    Args:
        paths: 文件路径、目录路径或通配符模式列表
        clear_existing: 是否在导入前清除现有数据
        verbose: 是否显示详细信息
    """
    # 查找所有 JSON 文件
    json_files = find_json_files(paths)
    
    if not json_files:
        print("❌ 未找到任何 JSON 文件")
        return
    
    print(f"\n🔍 找到 {len(json_files)} 个 JSON 文件:")
    for i, f in enumerate(json_files, 1):
        print(f"  {i}. {f}")
    
    # 确认
    if verbose:
        response = input(f"\n是否导入这 {len(json_files)} 个文件? (y/n): ").strip().lower()
        if response != 'y' and response != 'yes':
            print("❌ 已取消导入")
            return
    
    # 初始化数据库
    await init_db()
    
    # 批量导入
    print(f"\n🚀 开始批量导入...")
    success_count = 0
    fail_count = 0
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n{'='*60}")
        print(f"📦 处理文件 {i}/{len(json_files)}: {Path(json_file).name}")
        print(f"{'='*60}")
        
        # 只在第一个文件时清除现有数据
        should_clear = clear_existing and i == 1
        
        success = await import_map_data(json_file, clear_existing=should_clear, verbose=verbose)
        
        if success:
            success_count += 1
            print(f"✅ 文件 {i} 导入成功")
        else:
            fail_count += 1
            print(f"❌ 文件 {i} 导入失败")
    
    # 统计信息
    print(f"\n{'='*60}")
    print(f"🎉 批量导入完成!")
    print(f"✅ 成功: {success_count} 个文件")
    print(f"❌ 失败: {fail_count} 个文件")
    print(f"{'='*60}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='批量导入地图数据到数据库',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 导入单个文件
  python import_map_data_batch.py project1230/campus_map.json
  
  # 导入多个文件
  python import_map_data_batch.py project1230/campus_map.json project1230/campus_map_add.json
  
  # 导入目录下所有 JSON 文件
  python import_map_data_batch.py project1230/
  
  # 使用通配符
  python import_map_data_batch.py project1230/*.json
  
  # 清除现有数据后导入
  python import_map_data_batch.py project1230/ --clear
        """
    )
    parser.add_argument(
        'paths',
        nargs='+',
        help='JSON 文件路径、目录路径或通配符模式（可指定多个）'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='清除现有数据后再导入（只在第一个文件时清除）'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='静默模式，不显示详细信息'
    )
    
    args = parser.parse_args()
    
    await batch_import(args.paths, clear_existing=args.clear, verbose=not args.quiet)


if __name__ == "__main__":
    asyncio.run(main())


