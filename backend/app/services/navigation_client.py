import re
from typing import Any, Optional, Dict

try:
    from googlemaps.exceptions import ApiError
except ImportError:
    # 如果没有安装googlemaps，创建一个虚拟的ApiError
    class ApiError(Exception):
        pass


# 说明：
# - 本文件提供"导航能力"相关的纯函数：解析文本 -> 得到起点/终点/出行方式 -> 调用 Google Maps 得到路线
# - 设计上不处理 HTTP，只返回结构化 dict，便于被主 Agent 或 API 路由复用
MODE_WORDS = {
    "driving": ["驾车", "开车", "车", "drive", "driving"],
    "walking": ["步行", "走路", "walk", "walking"],
    "bicycling": ["骑行", "自行车", "单车", "bike", "bicycle", "bicycling"],
    "transit": ["公交", "地铁", "巴士", "公交车", "公共交通", "transit", "metro", "bus"],
}

def _canonicalize_origin(origin: Optional[str], default_origin: str) -> Optional[str]:
    # 对 origin 做一些常见别名归一化，比如 NTU -> DEFAULT_ORIGIN
    if not origin:
        return None
    o = origin.strip()
    if not o:
        return None
    lo = o.lower()
    if lo == "ntu" or "南洋理工" in o or "nanyang technological university" in lo:
        return default_origin
    return o


def normalize_text(s: str) -> str:
    # 统一输入格式：去首尾空格、压缩连续空白
    x = s.strip()
    x = re.sub(r"\s+", " ", x)
    return x


def detect_mode(s: str) -> str:
    # 从输入文本里猜测出行方式；未命中则默认 driving
    t = s.lower()
    for mode, words in MODE_WORDS.items():
        for w in words:
            if w in s or w in t:
                return mode
    return "driving"


def parse_navigation_query(s: str) -> Dict[str, Any]:
    # 解析自然语言为：origin / destination / mode
    # 支持：
    # - "从 A 到 B"
    # - "导航到 B"
    # - 英文 from/to 或 navigate to
    m = normalize_text(s)
    mode = detect_mode(m)
    pat_pairs = [
        r"(?:从|由)\s*(.+?)\s*(?:到|至|->|→)\s*(.+)",
        r"(?:from)\s*(.+?)\s*(?:to)\s*(.+)",
    ]
    for pat in pat_pairs:
        r = re.search(pat, m, re.IGNORECASE)
        if r:
            o = r.group(1).strip()
            d = r.group(2).strip()
            return {"origin": o, "destination": d, "mode": mode}

    pat_single = [
        r"(?:导航到|导航至|前往|去往|去|到)\s*(.+)",
        r"(?:navigate to)\s*(.+)",
    ]
    for pat in pat_single:
        r = re.search(pat, m, re.IGNORECASE)
        if r:
            d = r.group(1).strip()
            return {"origin": None, "destination": d, "mode": mode}

    kw = ["导航", "路线", "去", "到"]
    if any(k in m for k in kw):
        parts = re.split(r"(?:导航到|导航至|前往|去往|去|到)", m)
        if len(parts) > 1:
            d = parts[-1].strip()
            if d:
                return {"origin": None, "destination": d, "mode": mode}
    return {"origin": None, "destination": None, "mode": mode}


def navigate_route(
    *,
    gmaps_client,
    destination: str,
    origin: Optional[str],
    mode: str,
    default_origin: str,
) -> Optional[Dict[str, Any]]:
    # 调用 Google Maps Directions API 并提取前端渲染所需的关键字段
    # 返回 None 表示：没有 key / 没有路线 / 外部 API 报错
    if not gmaps_client:
        return None
    try:
        o = _canonicalize_origin(origin, default_origin) or default_origin
        r = gmaps_client.directions(
            o,
            destination,
            mode=mode,
            alternatives=False,
            language="zh-CN",
        )
        if not r:
            return None
        route = r[0]
        leg = route["legs"][0]
        return {
            "summary": route.get("summary"),
            "distance_text": leg["distance"]["text"],
            "distance_value": leg["distance"]["value"],
            "duration_text": leg["duration"]["text"],
            "duration_value": leg["duration"]["value"],
            "start_address": leg["start_address"],
            "end_address": leg["end_address"],
            "start_location": leg["start_location"],
            "end_location": leg["end_location"],
            "overview_polyline": route["overview_polyline"]["points"],
        }
    except ApiError:
        return None
    except Exception:
        return None

