"""
导航路径规划 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models import Node
from app.schemas import (
    RouteRequest, RouteResponse, RouteErrorResponse,
    PathNode, SearchNodeRequest, SearchNodeResponse
)
from app.services import graph_service

router = APIRouter(prefix="/navigation", tags=["导航"])


@router.post("/route", response_model=RouteResponse)
async def calculate_route(
    request: RouteRequest,
    db: AsyncSession = Depends(get_db)
) -> RouteResponse:
    """
    计算导航路径
    
    - **start_node_id**: 起点节点ID
    - **target_name**: 目标名称（模糊搜索），与 target_node_id 二选一
    - **target_node_id**: 目标节点ID（精确指定），与 target_name 二选一
    """
    # 确保图结构已加载
    if graph_service.reload_required():
        await graph_service.load_graph_from_db(db)
    
    # 验证起点存在
    start_info = graph_service.get_node_info(request.start_node_id)
    if not start_info:
        raise HTTPException(status_code=404, detail=f"起点节点不存在: {request.start_node_id}")
    
    # 确定终点
    target_node_id = request.target_node_id
    
    if not target_node_id and request.target_name:
        # 模糊搜索目标节点
        matches = graph_service.search_nodes(request.target_name)
        if not matches:
            raise HTTPException(status_code=404, detail=f"未找到匹配的目标: {request.target_name}")
        # 取第一个匹配结果
        target_node_id = matches[0]["id"]
    
    if not target_node_id:
        raise HTTPException(status_code=400, detail="请提供 target_name 或 target_node_id")
    
    # 验证终点存在
    target_info = graph_service.get_node_info(target_node_id)
    if not target_info:
        raise HTTPException(status_code=404, detail=f"终点节点不存在: {target_node_id}")
    
    # 运行 A* 算法
    total_distance, path = graph_service.astar(request.start_node_id, target_node_id)
    
    if not path:
        raise HTTPException(status_code=404, detail="无法找到路径，请检查节点是否连通")
    
    # 获取路径详细信息
    path_nodes = graph_service.get_path_nodes(path)
    steps = graph_service.generate_navigation_steps(path)
    floors = graph_service.get_floors_in_path(path)
    
    return RouteResponse(
        success=True,
        path=path,
        path_nodes=path_nodes,
        total_distance=total_distance,
        steps=steps,
        floors_involved=floors,
        message="路径规划成功",
    )


@router.get("/search", response_model=SearchNodeResponse)
async def search_nodes(
    keyword: str = Query(..., description="搜索关键词"),
    db: AsyncSession = Depends(get_db)
) -> SearchNodeResponse:
    """
    搜索节点（模糊匹配）
    
    - **keyword**: 搜索关键词，匹配节点ID、名称或详细信息
    """
    # 确保图结构已加载
    if graph_service.reload_required():
        await graph_service.load_graph_from_db(db)
    
    matches = graph_service.search_nodes(keyword)
    
    nodes = [
        PathNode(
            id=m["id"],
            name=m["name"],
            detail=m.get("detail"),
            floor=m["floor"],
            x=m.get("x"),
            y=m.get("y"),
            node_type=m.get("node_type"),
        )
        for m in matches
    ]
    
    return SearchNodeResponse(nodes=nodes, total=len(nodes))


@router.get("/nodes", response_model=SearchNodeResponse)
async def get_all_nodes(
    floor: Optional[int] = Query(None, description="按楼层筛选"),
    db: AsyncSession = Depends(get_db)
) -> SearchNodeResponse:
    """
    获取所有节点或指定楼层的节点
    
    - **floor**: 可选，楼层号
    """
    # 确保图结构已加载
    if graph_service.reload_required():
        await graph_service.load_graph_from_db(db)
    
    if floor is not None:
        nodes_data = graph_service.get_nodes_by_floor(floor)
    else:
        nodes_data = graph_service.get_all_nodes()
    
    nodes = [
        PathNode(
            id=m["id"],
            name=m["name"],
            detail=m.get("detail"),
            floor=m["floor"],
            x=m.get("x"),
            y=m.get("y"),
            node_type=m.get("node_type"),
        )
        for m in nodes_data
    ]
    
    return SearchNodeResponse(nodes=nodes, total=len(nodes))


@router.post("/reload")
async def reload_graph(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    重新加载图结构
    
    当数据库中的节点或边数据更新后，调用此接口刷新内存中的图结构
    """
    graph_service.clear_cache()
    await graph_service.load_graph_from_db(db)
    
    return {
        "message": "图结构重新加载成功",
        "nodes_count": len(graph_service.nodes_info),
        "edges_count": len(graph_service.edges_info) // 2,  # 双向边，除以2
    }

