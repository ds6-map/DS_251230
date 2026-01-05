"""
Agent Chat API
整合自 add 项目的对话功能
"""
import json
from typing import Any, List, Dict, Optional
from uuid import uuid4
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings, get_openai_client, get_gmaps_client, _get_api_keys

# 动态导入，避免在没有安装依赖时报错
try:
    from app.services.navigation_client import navigate_route, parse_navigation_query
except ImportError:
    # 如果没有安装googlemaps，提供占位函数
    def parse_navigation_query(s: str) -> dict:
        return {"origin": None, "destination": None, "mode": "driving"}
    
    def navigate_route(*, gmaps_client, destination: str, origin: Optional[str], mode: str, default_origin: str) -> Optional[Dict]:
        return None

router = APIRouter()

# 会话消息存储（内存，进程重启会清空）
_SESSION_MESSAGES: Dict[str, List[Dict[str, str]]] = {}
_MAX_SESSION_MESSAGES = 20


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    image_base64: Optional[str] = None
    dataset_folder: str = "image_data"
    top_k: int = 3


def _get_session_id(raw: Optional[str]) -> str:
    s = (raw or "").strip()
    return s or uuid4().hex


def _get_history(session_id: str) -> List[Dict[str, str]]:
    return _SESSION_MESSAGES.get(session_id, [])


def _append_history(session_id: str, role: str, content: str) -> None:
    c = (content or "").strip()
    if not c:
        return
    history = _SESSION_MESSAGES.setdefault(session_id, [])
    history.append({"role": role, "content": c})
    if len(history) > _MAX_SESSION_MESSAGES:
        _SESSION_MESSAGES[session_id] = history[-_MAX_SESSION_MESSAGES:]


def _simple_chat_reply(msg: str) -> str:
    """当 LLM 不可用时的简单降级回复"""
    m = msg.strip()
    if "你好" in m:
        return "你好！我可以帮你导航或聊天。"
    if "NTU" in m or "南洋理工" in m:
        return "NTU位于新加坡西部，附近有Jurong Lake Gardens、IMM、Jurong Point等。"
    if "樟宜" in m or "机场" in m:
        return "樟宜机场在新加坡东部，适合驾车或地铁前往。"
    return "已收到：" + m


def _tools_schema() -> List[Dict[str, Any]]:
    """定义给 LLM 的工具列表（OpenAI tool-calling）"""
    return [
        {
            "type": "function",
            "function": {
                "name": "navigate",
                "description": "规划从起点到终点的路线，返回距离、时间和折线。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {"type": ["string", "null"]},
                        "destination": {"type": "string"},
                        "mode": {
                            "type": "string",
                            "enum": ["driving", "walking", "bicycling", "transit"],
                        },
                    },
                    "required": ["destination"],
                },
            },
        }
    ]


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    主 Agent：单入口 /api/chat
    1) 有图片则走图片识别
    2) 有 LLM 则让 LLM 决策是否调用 navigate
    3) 否则走正则解析/简单回复降级
    """
    session_id = _get_session_id(req.session_id)
    msg = (req.message or "").strip()
    if not msg and not req.image_base64:
        return {"session_id": session_id, "reply": "请输入内容"}

    # 处理图片识别
    if req.image_base64:
        _append_history(session_id, "user", "用户上传了一张图片")
        try:
            from app.services.vision_client import recognize_image_base64

            data = recognize_image_base64(
                image_base64=req.image_base64,
                dataset_folder=req.dataset_folder,
                top_k=req.top_k,
            )
            _append_history(session_id, "assistant", "已识别完成")
            return {"session_id": session_id, "reply": "已识别完成", "tool": "location", "data": data}
        except RuntimeError as e:
            error_msg = str(e)
            if "VISION_ERR_BACKEND_MISSING" in error_msg:
                reply = "图片识别功能暂时不可用：缺少依赖包。请安装: pip install chromadb langchain-experimental open-clip-torch torch torchvision"
            else:
                reply = f"图片识别暂时不可用：{error_msg}"
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply}
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"图片识别错误: {e}", exc_info=True)
            reply = f"图片识别暂时不可用：{str(e)}"
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply}

    openai_client = get_openai_client()
    gmaps_client = get_gmaps_client()

    # 使用 LLM 处理
    if openai_client:
        tools = _tools_schema()
        history = _get_history(session_id)
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": "你是主Agent。普通对话直接回复；需要路线规划时调用navigate工具。",
            },
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": msg})
        try:
            # 第一次调用：让模型决定是否要 tool-call
            first = openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            assistant_msg = first.choices[0].message
            tool_calls = getattr(assistant_msg, "tool_calls", None)
            if tool_calls:
                tool_payloads: List[Dict[str, Any]] = []
                route_data = None
                for tc in tool_calls:
                    if tc.function.name != "navigate":
                        continue
                    args = json.loads(tc.function.arguments or "{}")
                    destination = (args.get("destination") or "").strip()
                    if not destination:
                        reply = "请问您想去哪里？"
                        _append_history(session_id, "user", msg)
                        _append_history(session_id, "assistant", reply)
                        return {"session_id": session_id, "reply": reply}
                    origin = args.get("origin")
                    mode = args.get("mode") or "driving"
                    route_data = navigate_route(
                        gmaps_client=gmaps_client,
                        destination=destination,
                        origin=origin,
                        mode=mode,
                        default_origin=settings.DEFAULT_ORIGIN,
                    )
                    tool_payloads.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(route_data, ensure_ascii=False),
                        }
                    )

                # 第二次调用：把工具结果回传给模型，让它生成自然语言回复
                second_messages = messages + [assistant_msg.model_dump()] + tool_payloads
                second = openai_client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=second_messages,
                )
                reply_text = second.choices[0].message.content or ""
                if route_data:
                    _append_history(session_id, "user", msg)
                    _append_history(session_id, "assistant", reply_text or "路线已生成")
                    return {
                        "session_id": session_id,
                        "reply": reply_text,
                        "tool": "navigate",
                        "data": route_data,
                    }
                reply = "抱歉，未找到可行路线。"
                _append_history(session_id, "user", msg)
                _append_history(session_id, "assistant", reply)
                return {"session_id": session_id, "reply": reply}

            reply = assistant_msg.content or ""
            _append_history(session_id, "user", msg)
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply}
        except Exception as e:
            # 记录 LLM 调用错误，但不中断流程，降级到正则解析
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"LLM API 调用失败，降级到正则解析: {e}", exc_info=True)
            # 继续执行下面的降级逻辑

    # LLM 不可用或失败：用正则做一次导航意图解析作为兜底
    import logging
    logger = logging.getLogger(__name__)
    if not openai_client:
        logger.info("[chat] LLM 客户端未配置，使用降级回复")
    logger.debug(f"[chat] 使用正则解析或固定回复处理: {msg[:50]}...")
    parsed = parse_navigation_query(msg)
    if parsed.get("destination"):
        data = navigate_route(
            gmaps_client=gmaps_client,
            destination=parsed["destination"],
            origin=parsed.get("origin"),
            mode=parsed.get("mode") or "driving",
            default_origin=settings.DEFAULT_ORIGIN,
        )
        if data:
            reply = f"路线概要: {data.get('summary')}；距离: {data.get('distance_text')}；时间: {data.get('duration_text')}"
            _append_history(session_id, "user", msg)
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply, "tool": "navigate", "data": data}

    reply = _simple_chat_reply(msg)
    _append_history(session_id, "user", msg)
    _append_history(session_id, "assistant", reply)
    return {"session_id": session_id, "reply": reply}


@router.get("/status")
async def api_status():
    """前端轮询：展示 LLM / GMaps 是否就绪"""
    try:
        llm_ready = False
        gmaps_ready = False
        try:
            llm_ready = get_openai_client() is not None
        except Exception:
            pass
        try:
            gmaps_ready = get_gmaps_client() is not None
        except Exception:
            pass
        
        return {
            "llmReady": llm_ready,
            "gmapsReady": gmaps_ready,
            "openaiBase": settings.OPENAI_API_BASE or "",
            "openaiModel": settings.OPENAI_MODEL,
        }
    except Exception as e:
        # 即使出错也返回有效响应
        return {
            "llmReady": False,
            "gmapsReady": False,
            "openaiBase": "",
            "openaiModel": settings.OPENAI_MODEL,
            "error": str(e) if settings.DEBUG else None,
        }


@router.get("/config")
async def api_config():
    """前端动态加载 Google Maps JS 时需要的 key"""
    try:
        api_key = settings.GMAPS_API_KEY or ""
        if not api_key:
            # 尝试从 key.py 读取
            _, api_key, _ = _get_api_keys()
        return {"gmapsKey": api_key or ""}
    except Exception as e:
        # 即使出错也返回有效响应
        if settings.DEBUG:
            print(f"Failed to get config: {e}")
        return {"gmapsKey": ""}

