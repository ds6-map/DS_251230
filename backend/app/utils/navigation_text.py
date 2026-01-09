"""
导航指令生成工具
将路径转换为自然语言导航指令
"""
from typing import List, Dict, Any


def generate_direction_text(
    from_node: Dict[str, Any],
    to_node: Dict[str, Any],
    edge_info: Dict[str, Any]
) -> str:
    """
    生成单步导航指令
    
    Args:
        from_node: 起点节点信息
        to_node: 终点节点信息
        edge_info: 边信息
        
    Returns:
        导航指令文本
    """
    edge_type = edge_info.get("edge_type", "normal")
    weight = edge_info.get("weight", 0)
    
    from_floor = from_node.get("floor", 0)
    to_floor = to_node.get("floor", 0)
    floor_diff = to_floor - from_floor
    
    to_name = to_node.get("name", to_node.get("id", "未知"))
    to_detail = to_node.get("detail", "")
    
    if edge_type == "stairs":
        if floor_diff > 0:
            return f"沿楼梯上行 {floor_diff} 层，到达 {to_floor} 楼"
        elif floor_diff < 0:
            return f"沿楼梯下行 {abs(floor_diff)} 层，到达 {to_floor} 楼"
        else:
            return f"经过楼梯，到达 {to_name}"
    
    elif edge_type == "lifts":
        if floor_diff != 0:
            return f"乘坐电梯到 {to_floor} 楼"
        else:
            return f"经过电梯区域，到达 {to_name}"
    
    else:
        # 普通走廊
        if to_detail:
            return f"沿走廊前行约 {weight:.0f} 米，到达 {to_name} ({to_detail})"
        else:
            return f"沿走廊前行约 {weight:.0f} 米，到达 {to_name}"


def format_total_distance(distance: float) -> str:
    """
    格式化总距离显示
    
    Args:
        distance: 距离值
        
    Returns:
        格式化后的距离字符串
    """
    if distance < 1000:
        return f"{distance:.0f} 米"
    else:
        return f"{distance / 1000:.1f} 公里"


def format_estimated_time(distance: float, speed: float = 1.2) -> str:
    """
    估算步行时间
    
    Args:
        distance: 距离（米）
        speed: 步行速度（米/秒），默认 1.2 m/s
        
    Returns:
        格式化后的时间字符串
    """
    seconds = distance / speed
    
    if seconds < 60:
        return f"约 {seconds:.0f} 秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"约 {minutes:.0f} 分钟"
    else:
        hours = seconds / 3600
        return f"约 {hours:.1f} 小时"

