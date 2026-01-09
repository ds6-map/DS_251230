"""
导出节点坐标的脚本
将数据库中所有节点的坐标导出为 JSON 文件，用于备份和恢复
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db import AsyncSessionLocal, init_db
from app.models import Node


async def export_node_coordinates(output_file: str = None):
    """
    导出所有节点的坐标信息
    
    Args:
        output_file: 输出文件路径，如果为 None 则自动生成
    """
    await init_db()
    
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"node_coordinates_backup_{timestamp}.json"
    
    async with AsyncSessionLocal() as session:
        # 查询所有有坐标的节点
        result = await session.execute(
            select(Node).where(Node.x.isnot(None), Node.y.isnot(None))
        )
        nodes = result.scalars().all()
        
        # 构建坐标数据
        coordinates = {
            "export_time": datetime.now().isoformat(),
            "total_nodes": len(nodes),
            "nodes": [
                {
                    "id": node.id,
                    "x": float(node.x),
                    "y": float(node.y),
                    "floor": node.floor
                }
                for node in nodes
            ]
        }
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(coordinates, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已导出 {len(nodes)} 个节点的坐标到: {output_file}")
        return output_file


async def restore_node_coordinates(backup_file: str):
    """
    从备份文件恢复节点坐标
    
    Args:
        backup_file: 备份文件路径
    """
    print(f"📖 读取备份文件: {backup_file}")
    
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 文件不存在: {backup_file}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析错误: {e}")
        return
    
    await init_db()
    
    nodes_data = data.get('nodes', [])
    print(f"📊 发现 {len(nodes_data)} 个节点的坐标数据")
    
    async with AsyncSessionLocal() as session:
        restored = 0
        not_found = 0
        
        for node_data in nodes_data:
            node_id = node_data.get('id')
            x = node_data.get('x')
            y = node_data.get('y')
            
            if not node_id or x is None or y is None:
                continue
            
            result = await session.execute(
                select(Node).where(Node.id == node_id)
            )
            node = result.scalar_one_or_none()
            
            if node:
                node.x = x
                node.y = y
                restored += 1
            else:
                not_found += 1
                print(f"⚠️  节点不存在: {node_id}")
        
        await session.commit()
        print(f"✅ 已恢复 {restored} 个节点的坐标")
        if not_found > 0:
            print(f"⚠️  {not_found} 个节点在数据库中不存在")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='导出/恢复节点坐标')
    parser.add_argument(
        'action',
        choices=['export', 'restore'],
        help='操作类型: export (导出) 或 restore (恢复)'
    )
    parser.add_argument(
        'file',
        nargs='?',
        help='文件路径（导出时可选，恢复时必需）'
    )
    
    args = parser.parse_args()
    
    if args.action == 'export':
        await export_node_coordinates(args.file)
    elif args.action == 'restore':
        if not args.file:
            print("❌ 恢复操作需要指定备份文件路径")
            return
        await restore_node_coordinates(args.file)


if __name__ == "__main__":
    asyncio.run(main())


