"""
Navigation instruction generator
Convert path to natural language navigation instructions
"""
from typing import List, Dict, Any


def generate_direction_text(
    from_node: Dict[str, Any],
    to_node: Dict[str, Any],
    edge_info: Dict[str, Any]
) -> str:
    """
    Generate single step navigation instruction
    
    Args:
        from_node: Start node info
        to_node: End node info
        edge_info: Edge info
        
    Returns:
        Navigation instruction text
    """
    edge_type = edge_info.get("edge_type", "normal")
    weight = edge_info.get("weight", 0)
    
    from_floor = from_node.get("floor", 0)
    to_floor = to_node.get("floor", 0)
    floor_diff = to_floor - from_floor
    
    to_name = to_node.get("name", to_node.get("id", "Unknown"))
    to_detail = to_node.get("detail", "")
    
    if edge_type == "stairs":
        if floor_diff > 0:
            floors_text = "floor" if floor_diff == 1 else "floors"
            return f"Go up {floor_diff} {floors_text} via stairs to Level {to_floor}"
        elif floor_diff < 0:
            floors_text = "floor" if abs(floor_diff) == 1 else "floors"
            return f"Go down {abs(floor_diff)} {floors_text} via stairs to Level {to_floor}"
        else:
            return f"Pass through stairs to {to_name}"
    
    elif edge_type == "lifts":
        if floor_diff != 0:
            return f"Take lift to Level {to_floor}"
        else:
            return f"Pass through lift area to {to_name}"
    
    else:
        # Normal corridor
        if to_detail:
            return f"Walk about {weight:.0f}M along corridor to {to_name} ({to_detail})"
        else:
            return f"Walk about {weight:.0f}M along corridor to {to_name}"


def format_total_distance(distance: float) -> str:
    """
    Format total distance display
    
    Args:
        distance: Distance value
        
    Returns:
        Formatted distance string
    """
    if distance < 1000:
        return f"{distance:.0f} M"
    else:
        return f"{distance / 1000:.1f} KM"


def format_estimated_time(distance: float, speed: float = 1.2) -> str:
    """
    Estimate walking time
    
    Args:
        distance: Distance (meters)
        speed: Walking speed (m/s), default 1.2 m/s
        
    Returns:
        Formatted time string
    """
    seconds = distance / speed
    
    if seconds < 60:
        return f"About {seconds:.0f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"About {minutes:.0f} minutes"
    else:
        hours = seconds / 3600
        return f"About {hours:.1f} hours"

