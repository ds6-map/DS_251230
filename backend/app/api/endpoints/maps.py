"""
地图管理 API
底图上传和节点坐标编辑
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db import get_db
from app.models import Map, Node
from app.schemas import (
    MapResponse, MapUploadResponse,
    NodeResponse, NodePositionUpdate, NodeBatchUpdate, NodeListResponse
)
from app.services import map_service, graph_service

router = APIRouter(prefix="/maps", tags=["地图管理"])


# ==================== 底图管理 ====================

@router.post("/upload", response_model=MapUploadResponse)
async def upload_map(
    floor: int = Form(..., description="楼层号"),
    file: UploadFile = File(..., description="底图文件"),
    db: AsyncSession = Depends(get_db)
) -> MapUploadResponse:
    """
    上传底图文件
    
    - **floor**: 楼层号
    - **file**: 底图文件（PNG/JPG 格式）
    
    如果该楼层已有底图，将会被替换。
    """
    # 验证文件类型
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件（PNG、JPG 格式）")
    
    # 读取文件内容
    try:
        file_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取文件失败: {str(e)}")
    
    # 保存文件
    try:
        map_obj = await map_service.save_map_file(
            file_content=file_content,
            original_filename=file.filename or "image.png",
            floor=floor,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
    
    return MapUploadResponse(
        message="上传成功",
        map=MapResponse.model_validate(map_obj),
    )


@router.get("/{floor}", response_model=MapResponse)
async def get_map_by_floor(
    floor: int,
    db: AsyncSession = Depends(get_db)
) -> MapResponse:
    """
    获取指定楼层的底图信息
    
    - **floor**: 楼层号
    """
    map_obj = await map_service.get_map_by_floor(floor, db)
    
    if not map_obj:
        raise HTTPException(status_code=404, detail=f"楼层 {floor} 的底图不存在")
    
    return MapResponse.model_validate(map_obj)


@router.get("/", response_model=List[MapResponse])
async def get_all_maps(
    db: AsyncSession = Depends(get_db)
) -> List[MapResponse]:
    """
    获取所有楼层的底图信息
    """
    maps = await map_service.get_all_maps(db)
    return [MapResponse.model_validate(m) for m in maps]


@router.delete("/{floor}")
async def delete_map(
    floor: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    删除指定楼层的底图
    
    - **floor**: 楼层号
    """
    success = await map_service.delete_map(floor, db)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"楼层 {floor} 的底图不存在")
    
    return {"message": f"楼层 {floor} 的底图已删除"}


# ==================== 节点管理（编辑器用） ====================

@router.get("/nodes/list", response_model=NodeListResponse)
async def get_nodes_for_editor(
    floor: Optional[int] = Query(None, description="按楼层筛选"),
    db: AsyncSession = Depends(get_db)
) -> NodeListResponse:
    """
    获取节点列表（编辑器用）
    
    - **floor**: 可选，按楼层筛选
    """
    if floor is not None:
        result = await db.execute(
            select(Node).where(Node.floor == floor).order_by(Node.id)
        )
    else:
        result = await db.execute(select(Node).order_by(Node.floor, Node.id))
    
    nodes = result.scalars().all()
    
    node_responses = []
    for node in nodes:
        node_responses.append(NodeResponse(
            id=node.id,
            name=node.name,
            detail=node.detail,
            floor=node.floor,
            x=node.x,
            y=node.y,
            node_type=node.node_type,
            has_coordinates=node.has_coordinates,
            created_at=node.created_at,
            updated_at=node.updated_at,
        ))
    
    return NodeListResponse(nodes=node_responses, total=len(node_responses))


@router.put("/nodes/{node_id}/position")
async def update_node_position(
    node_id: str,
    position: NodePositionUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    更新单个节点的坐标
    
    - **node_id**: 节点ID
    - **x**: X坐标（像素）
    - **y**: Y坐标（像素）
    """
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(status_code=404, detail=f"节点不存在: {node_id}")
    
    node.x = position.x
    node.y = position.y
    await db.commit()
    
    # 清除图缓存，下次请求时重新加载
    graph_service.clear_cache()
    
    return {
        "message": "坐标更新成功",
        "node_id": node_id,
        "x": position.x,
        "y": position.y,
    }


@router.put("/nodes/batch-update")
async def batch_update_node_positions(
    data: NodeBatchUpdate,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    批量更新节点坐标
    
    - **nodes**: 节点列表，每个包含 id, x, y
    """
    updated_count = 0
    errors = []
    
    for node_data in data.nodes:
        node_id = node_data.get("id")
        x = node_data.get("x")
        y = node_data.get("y")
        
        if not node_id or x is None or y is None:
            errors.append(f"无效的节点数据: {node_data}")
            continue
        
        result = await db.execute(select(Node).where(Node.id == node_id))
        node = result.scalar_one_or_none()
        
        if not node:
            errors.append(f"节点不存在: {node_id}")
            continue
        
        node.x = x
        node.y = y
        updated_count += 1
    
    await db.commit()
    
    # 清除图缓存
    graph_service.clear_cache()
    
    return {
        "message": "批量更新完成",
        "updated_count": updated_count,
        "errors": errors if errors else None,
    }


@router.get("/floors/list")
async def get_available_floors(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    获取所有可用楼层列表
    
    返回数据库中存在节点的所有楼层
    """
    from sqlalchemy import distinct
    
    result = await db.execute(select(distinct(Node.floor)).order_by(Node.floor))
    floors = [row[0] for row in result.fetchall()]
    
    return {
        "floors": floors,
        "total": len(floors),
    }

