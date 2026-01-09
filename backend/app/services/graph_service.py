"""
图服务模块
实现 A* 算法和图结构管理
"""
import heapq
import math
from typing import Dict, List, Tuple, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Node, Edge
from app.schemas import PathNode, NavigationStep


class GraphService:
    """
    图服务类
    管理图结构并提供路径规划功能
    """
    
    def __init__(self):
        # 图结构：邻接表 { node_id: [(neighbor_id, weight, edge_type), ...] }
        self.graph: Dict[str, List[Tuple[str, float, str]]] = {}
        # 节点信息缓存
        self.nodes_info: Dict[str, dict] = {}
        # 边信息缓存
        self.edges_info: Dict[Tuple[str, str], dict] = {}
        # 是否已加载
        self._loaded = False
    
    async def load_graph_from_db(self, db: AsyncSession) -> None:
        """
        从数据库加载图结构到内存
        应在应用启动时调用
        
        Args:
            db: 数据库会话
        """
        # 加载所有节点
        result = await db.execute(select(Node))
        nodes = result.scalars().all()
        
        for node in nodes:
            self.nodes_info[node.id] = {
                "id": node.id,
                "name": node.name,
                "detail": node.detail,
                "floor": node.floor,
                "x": node.x,
                "y": node.y,
                "node_type": node.node_type,
            }
            # 初始化邻接表
            if node.id not in self.graph:
                self.graph[node.id] = []
        
        # 加载所有边
        result = await db.execute(select(Edge))
        edges = result.scalars().all()
        
        for edge in edges:
            # 存储边信息
            edge_info = {
                "weight": edge.weight,
                "edge_type": edge.edge_type,
                "is_vertical": edge.is_vertical,
            }
            self.edges_info[(edge.from_node_id, edge.to_node_id)] = edge_info
            self.edges_info[(edge.to_node_id, edge.from_node_id)] = edge_info
            
            # 构建双向邻接表
            if edge.from_node_id not in self.graph:
                self.graph[edge.from_node_id] = []
            if edge.to_node_id not in self.graph:
                self.graph[edge.to_node_id] = []
            
            self.graph[edge.from_node_id].append(
                (edge.to_node_id, edge.weight, edge.edge_type)
            )
            self.graph[edge.to_node_id].append(
                (edge.from_node_id, edge.weight, edge.edge_type)
            )
        
        self._loaded = True
    
    def reload_required(self) -> bool:
        """检查是否需要重新加载"""
        return not self._loaded
    
    def clear_cache(self) -> None:
        """清除缓存，强制下次重新加载"""
        self.graph.clear()
        self.nodes_info.clear()
        self.edges_info.clear()
        self._loaded = False
    
    def _heuristic(self, node1_id: str, node2_id: str) -> float:
        """
        A* 算法的启发函数
        计算两个节点之间的估计距离
        
        如果节点有坐标，使用欧几里得距离
        否则使用楼层差异作为估计
        
        Args:
            node1_id: 节点1的ID
            node2_id: 节点2的ID
            
        Returns:
            估计距离
        """
        node1 = self.nodes_info.get(node1_id, {})
        node2 = self.nodes_info.get(node2_id, {})
        
        # 如果两个节点都有坐标，使用欧几里得距离
        if all([node1.get("x"), node1.get("y"), node2.get("x"), node2.get("y")]):
            dx = node1["x"] - node2["x"]
            dy = node1["y"] - node2["y"]
            distance = math.sqrt(dx * dx + dy * dy)
            
            # 考虑楼层差异
            floor_diff = abs(node1.get("floor", 0) - node2.get("floor", 0))
            # 楼层权重：每层约 30 个单位
            return distance + floor_diff * 30
        
        # 没有坐标时，只使用楼层差异
        floor1 = node1.get("floor", 0)
        floor2 = node2.get("floor", 0)
        return abs(floor1 - floor2) * 50
    
    def astar(self, start_id: str, end_id: str) -> Tuple[float, List[str]]:
        """
        A* 算法实现
        计算从起点到终点的最短路径
        
        Args:
            start_id: 起点节点ID
            end_id: 终点节点ID
            
        Returns:
            (总距离, 路径节点ID列表)
            如果无法到达，返回 (inf, [])
        """
        if start_id not in self.graph or end_id not in self.graph:
            return float('inf'), []
        
        if start_id == end_id:
            return 0, [start_id]
        
        # 优先队列: (f_score, g_score, node_id)
        # f_score = g_score + h_score
        open_set: List[Tuple[float, float, str]] = [(0, 0, start_id)]
        
        # 已访问节点集合
        closed_set: Set[str] = set()
        
        # g_score: 从起点到各节点的实际距离
        g_scores: Dict[str, float] = {start_id: 0}
        
        # 前驱节点，用于重建路径
        came_from: Dict[str, Optional[str]] = {start_id: None}
        
        while open_set:
            # 取出 f_score 最小的节点
            f_score, g_score, current = heapq.heappop(open_set)
            
            # 找到终点
            if current == end_id:
                # 重建路径
                path = []
                node = current
                while node is not None:
                    path.append(node)
                    node = came_from.get(node)
                path.reverse()
                return g_scores[end_id], path
            
            # 跳过已访问的节点
            if current in closed_set:
                continue
            
            closed_set.add(current)
            
            # 遍历邻居
            for neighbor, weight, edge_type in self.graph.get(current, []):
                if neighbor in closed_set:
                    continue
                
                # 计算新的 g_score
                tentative_g = g_scores[current] + weight
                
                # 如果找到更短的路径
                if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                    g_scores[neighbor] = tentative_g
                    came_from[neighbor] = current
                    
                    # 计算 f_score
                    h_score = self._heuristic(neighbor, end_id)
                    f_score = tentative_g + h_score
                    
                    heapq.heappush(open_set, (f_score, tentative_g, neighbor))
        
        # 无法到达
        return float('inf'), []
    
    def get_node_info(self, node_id: str) -> Optional[dict]:
        """获取节点信息"""
        return self.nodes_info.get(node_id)
    
    def get_edge_info(self, from_id: str, to_id: str) -> Optional[dict]:
        """获取边信息"""
        return self.edges_info.get((from_id, to_id))
    
    def get_path_nodes(self, path: List[str]) -> List[PathNode]:
        """
        获取路径上所有节点的详细信息
        
        Args:
            path: 路径节点ID列表
            
        Returns:
            PathNode 列表
        """
        result = []
        for node_id in path:
            info = self.nodes_info.get(node_id, {})
            result.append(PathNode(
                id=node_id,
                name=info.get("name", node_id),
                detail=info.get("detail"),
                floor=info.get("floor", 0),
                x=info.get("x"),
                y=info.get("y"),
                node_type=info.get("node_type"),
            ))
        return result
    
    def generate_navigation_steps(self, path: List[str]) -> List[NavigationStep]:
        """
        生成分步导航指令
        
        Args:
            path: 路径节点ID列表
            
        Returns:
            NavigationStep 列表
        """
        if len(path) < 2:
            return []
        
        steps = []
        
        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]
            
            from_node = self.nodes_info.get(from_id, {})
            to_node = self.nodes_info.get(to_id, {})
            edge = self.edges_info.get((from_id, to_id), {})
            
            edge_type = edge.get("edge_type", "normal")
            weight = edge.get("weight", 0)
            
            from_floor = from_node.get("floor", 0)
            to_floor = to_node.get("floor", 0)
            floor_change = to_floor - from_floor if from_floor != to_floor else None
            
            # 生成指令文字
            to_name = to_node.get("name", to_id)
            to_detail = to_node.get("detail", "")
            
            if edge_type == "stairs":
                if floor_change and floor_change > 0:
                    floors_text = "floor" if floor_change == 1 else "floors"
                    instruction = f"Go up {floor_change} {floors_text} via stairs to Level {to_floor}"
                elif floor_change and floor_change < 0:
                    floors_text = "floor" if abs(floor_change) == 1 else "floors"
                    instruction = f"Go down {abs(floor_change)} {floors_text} via stairs to Level {to_floor}"
                else:
                    instruction = f"Pass through stairs to {to_name}"
            elif edge_type == "lifts":
                if floor_change:
                    instruction = f"Take lift to Level {to_floor}"
                else:
                    instruction = f"Pass through lift to {to_name}"
            else:
                if to_detail:
                    instruction = f"Walk about {weight:.0f}M to {to_name} ({to_detail})"
                else:
                    instruction = f"Walk about {weight:.0f}M to {to_name}"
            
            steps.append(NavigationStep(
                step_number=i + 1,
                instruction=instruction,
                from_node_id=from_id,
                to_node_id=to_id,
                distance=weight,
                edge_type=edge_type,
                floor_change=floor_change,
            ))
        
        return steps
    
    def get_floors_in_path(self, path: List[str]) -> List[int]:
        """
        获取路径涉及的所有楼层
        
        Args:
            path: 路径节点ID列表
            
        Returns:
            楼层列表（已排序去重）
        """
        floors = set()
        for node_id in path:
            info = self.nodes_info.get(node_id, {})
            floor = info.get("floor")
            if floor is not None:
                floors.add(floor)
        return sorted(floors)
    
    def search_nodes(self, keyword: str) -> List[dict]:
        """
        搜索节点（模糊匹配）
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的节点信息列表
        """
        keyword_lower = keyword.lower()
        results = []
        
        for node_id, info in self.nodes_info.items():
            # 匹配 ID、名称或详细信息
            if (keyword_lower in node_id.lower() or
                keyword_lower in info.get("name", "").lower() or
                keyword_lower in (info.get("detail") or "").lower()):
                results.append(info)
        
        return results
    
    def get_all_nodes(self) -> List[dict]:
        """获取所有节点"""
        return list(self.nodes_info.values())
    
    def get_nodes_by_floor(self, floor: int) -> List[dict]:
        """获取指定楼层的所有节点"""
        return [
            info for info in self.nodes_info.values()
            if info.get("floor") == floor
        ]


# 全局单例
graph_service = GraphService()

