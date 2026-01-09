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
    """Fallback reply when LLM is not available"""
    m = msg.strip().lower()
    original = msg.strip()
    
    # Greetings
    greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
    if any(g in m for g in greetings):
        return "Hello! I'm your smart assistant. I can help you plan routes, answer questions, or just chat. How can I help you?"
    
    # Thanks
    thanks = ["thanks", "thank you", "thx", "appreciate"]
    if any(t in m for t in thanks):
        return "You're welcome! Feel free to ask if you have any other questions~"
    
    # Goodbye
    byes = ["bye", "goodbye", "see you", "later", "good night"]
    if any(b in m for b in byes):
        return "Goodbye! Have a safe trip~ 🌟"
    
    # Ability inquiry
    ability_keywords = ["what can you do", "help", "how to use", "features", "capabilities"]
    if any(k in m for k in ability_keywords):
        return "I can help you with:\n1️⃣ Route planning - Tell me where you want to go from and to\n2️⃣ Location recognition - Upload a photo and I'll identify where it is\n3️⃣ Answer questions - Ask me about places, transportation, etc.\n\nTry saying 'from NTU to Changi Airport' or 'navigate to Orchard Road'"
    
    # Weather related
    weather_keywords = ["weather", "rain", "sunny", "temperature", "hot", "cold"]
    if any(k in m for k in weather_keywords):
        return "Singapore is warm year-round, with temperatures around 25-32°C. It's recommended to bring an umbrella for sudden rain showers. Check weather.gov.sg for real-time updates~"
    
    # Location introductions
    if "ntu" in m or "nanyang" in m:
        return "Nanyang Technological University (NTU) is located in western Singapore and is one of Asia's top universities. The campus is large and beautiful with iconic buildings like The Hive. Take MRT to Pioneer station and transfer to bus, or drive/taxi directly."
    if "changi" in m or "airport" in m:
        return "Changi Airport is located in eastern Singapore and is one of the world's best airports. Don't miss Jewel Changi Airport! Take East-West MRT line or taxi, about 20-40 minutes from downtown."
    if "orchard" in m:
        return "Orchard Road is Singapore's most famous shopping street with malls like ION, Takashimaya, and Ngee Ann City. Take MRT to Orchard station."
    if "marina bay" in m or "mbs" in m:
        return "Marina Bay Sands (MBS) is Singapore's landmark featuring the infinity pool, casino, shopping mall, and ArtScience Museum. Take MRT to Bayfront station."
    if "sentosa" in m:
        return "Sentosa Island is Singapore's resort destination with Universal Studios, S.E.A. Aquarium, and beaches. Take the Sentosa Express or walk from VivoCity."
    
    # Transportation inquiry
    transport_keywords = ["how to go", "how to get", "directions", "route"]
    if any(k in m for k in transport_keywords):
        return "Singapore has many transport options:\n🚇 MRT - Covers major areas, fast and convenient\n🚌 Bus - Dense network, use EZ-Link card\n🚕 Taxi - Grab/ComfortDelGro/Gojek\n🚶 Walking - Many places are walkable in the city\n\nTell me where you want to go and I'll plan the route!"
    
    # Food related
    food_keywords = ["food", "eat", "restaurant", "dining", "hungry"]
    if any(k in m for k in food_keywords):
        return "Singapore has amazing food! Try:\n🍜 Hainanese chicken rice, Laksa, Bak Kut Teh\n🦀 Chilli crab, Black pepper crab\n🍢 Satay, Char Kway Teow\n\nVisit Chinatown, Lau Pa Sat, or Maxwell Food Centre for authentic local food~"
    
    # Generic question reply
    question_words = ["what", "where", "how", "why", "when", "which", "?"]
    if any(q in m for q in question_words):
        return f"That's a good question! For '{original}', you can:\n1. Try to be more specific about your needs\n2. If it's about routes, tell me the start and end points\n3. If it's location recognition, upload a photo\n\nI'll do my best to help!"
    
    # Default reply
    return f"Got your message! If you need route planning, try 'from A to B'. If you want to know about a place, just ask me~ 😊"


def _tools_schema() -> List[Dict[str, Any]]:
    """Define tool list for LLM (OpenAI tool-calling)"""
    return [
        {
            "type": "function",
            "function": {
                "name": "navigate",
                "description": "Plan a route from origin to destination, returning distance, duration and polyline.",
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
    import logging
    logger = logging.getLogger(__name__)
    debug_info = []  # 调试信息列表
    
    session_id = _get_session_id(req.session_id)
    msg = (req.message or "").strip()
    if not msg and not req.image_base64:
        return {"session_id": session_id, "reply": "Please enter a message", "debug": debug_info}
    
    debug_info.append(f"📥 Received message: {msg[:50]}...")

    # Handle image recognition
    if req.image_base64:
        _append_history(session_id, "user", "User uploaded an image")
        try:
            from app.services.vision_client import recognize_image_base64

            data = recognize_image_base64(
                image_base64=req.image_base64,
                dataset_folder=req.dataset_folder,
                top_k=req.top_k,
            )
            _append_history(session_id, "assistant", "Recognition completed")
            return {"session_id": session_id, "reply": "Recognition completed", "tool": "location", "data": data}
        except RuntimeError as e:
            error_msg = str(e)
            if "VISION_ERR_BACKEND_MISSING" in error_msg:
                reply = "Image recognition temporarily unavailable: missing dependencies. Please install: pip install chromadb langchain-experimental open-clip-torch torch torchvision"
            else:
                reply = f"Image recognition temporarily unavailable: {error_msg}"
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply}
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Image recognition error: {e}", exc_info=True)
            reply = f"Image recognition temporarily unavailable: {str(e)}"
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply}

    openai_client = get_openai_client()
    gmaps_client = get_gmaps_client()
    
    # Check service status
    debug_info.append(f"🤖 LLM Client: {'✅ Configured' if openai_client else '❌ Not configured'}")
    debug_info.append(f"🗺️  Google Maps Client: {'✅ Configured' if gmaps_client else '❌ Not configured'}")

    # Use LLM to process
    if openai_client:
        debug_info.append("🚀 Processing request with LLM")
        tools = _tools_schema()
        history = _get_history(session_id)
        system_prompt = """You are a friendly, intelligent navigation and Q&A assistant. Your responsibilities are:

1. **Route Planning**: When users ask how to get from A to B, want to go somewhere, or need navigation, call the navigate tool.
   - If the user doesn't specify a starting point, assume starting from current location (NTU)
   - Support multiple transport modes: driving, walking, transit, bicycling

2. **General Conversation**: For greetings, chat, knowledge Q&A, etc., reply directly in natural language without calling tools.
   - Keep a friendly, enthusiastic tone
   - Use emojis to make responses more lively
   - If unsure, guide users to provide more information

3. **Be Flexible**:
   - If the user's question is vague, try to understand the intent before deciding whether to call tools
   - For introductions or recommendations about places, answer directly without navigation
   - For complex questions, answer step by step

Please reply in English, keep it concise but useful."""
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": system_prompt,
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
            debug_info.append(f"🔍 LLM first call completed, tool call: {'Yes' if tool_calls else 'No'}")
            if tool_calls:
                debug_info.append(f"🛠️  Detected {len(tool_calls)} tool call(s)")
                tool_payloads: List[Dict[str, Any]] = []
                route_data = None
                for tc in tool_calls:
                    if tc.function.name != "navigate":
                        continue
                    args = json.loads(tc.function.arguments or "{}")
                    destination = (args.get("destination") or "").strip()
                    origin = args.get("origin")
                    mode = args.get("mode") or "driving"
                    
                    debug_info.append(f"📍 Parsed params: origin={origin or 'None'}, destination={destination}, mode={mode}")
                    
                    if not destination:
                        debug_info.append("❌ Destination is empty, returning prompt")
                        reply = "Where would you like to go?"
                        _append_history(session_id, "user", msg)
                        _append_history(session_id, "assistant", reply)
                        return {"session_id": session_id, "reply": reply, "debug": debug_info}
                    
                    debug_info.append(f"🗺️  Calling Google Maps API: {origin or settings.DEFAULT_ORIGIN} → {destination} ({mode})")
                    route_data = navigate_route(
                        gmaps_client=gmaps_client,
                        destination=destination,
                        origin=origin,
                        mode=mode,
                        default_origin=settings.DEFAULT_ORIGIN,
                    )
                    if route_data:
                        debug_info.append(f"✅ Route planning successful: {route_data.get('distance_text')}, {route_data.get('duration_text')}")
                    else:
                        debug_info.append("❌ Route planning failed: Google Maps API returned empty result")
                    tool_payloads.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(route_data, ensure_ascii=False),
                        }
                    )

                # Second call: pass tool results back to model to generate natural language reply
                if route_data:
                    second_messages = messages + [assistant_msg.model_dump()] + tool_payloads
                    second = openai_client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=second_messages,
                    )
                    reply_text = second.choices[0].message.content or "Route generated"
                    debug_info.append("💬 LLM reply generation completed")
                    _append_history(session_id, "user", msg)
                    _append_history(session_id, "assistant", reply_text)
                    return {
                        "session_id": session_id,
                        "reply": reply_text,
                        "tool": "navigate",
                        "data": route_data,
                        "debug": debug_info,
                    }
                
                # When navigation fails, let LLM generate a friendlier reply
                try:
                    fallback_resp = openai_client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=messages + [{"role": "user", "content": f"User said: {msg}\nBut the navigation tool couldn't find a route. Please tell the user in a friendly way and ask if they need help. Don't use robotic replies like 'Sorry, no viable route found'."}],
                    )
                    reply = fallback_resp.choices[0].message.content or "Unable to plan this route at the moment. Could you provide a more specific address?"
                except Exception:
                    reply = "Unable to plan this route at the moment 😅\n\nPossible reasons:\n• Location name not specific enough\n• Map service temporarily unavailable\n\nTry providing a more detailed address or rephrase~"
                debug_info.append("💬 LLM fallback reply generation completed")
                _append_history(session_id, "user", msg)
                _append_history(session_id, "assistant", reply)
                return {"session_id": session_id, "reply": reply, "debug": debug_info}

            reply = assistant_msg.content or ""
            debug_info.append("💬 LLM direct reply (no tool call)")
            _append_history(session_id, "user", msg)
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply, "debug": debug_info}
        except Exception as e:
            # Log LLM call error but don't interrupt flow, fallback to regex parsing
            logger.warning(f"LLM API call failed, falling back to regex: {e}", exc_info=True)
            debug_info.append(f"⚠️  LLM call failed: {str(e)[:100]}, falling back to regex")
            # Continue to fallback logic below

    # LLM unavailable or failed: use regex for navigation intent parsing as fallback
    if not openai_client:
        logger.info("[chat] LLM client not configured, using fallback reply")
        debug_info.append("⚠️  LLM not configured, using regex parsing")
    logger.debug(f"[chat] Using regex or fixed reply: {msg[:50]}...")
    debug_info.append("🔍 Starting regex navigation query parsing")
    parsed = parse_navigation_query(msg)
    debug_info.append(f"📋 Parse result: {parsed}")
    if parsed.get("destination"):
        debug_info.append(f"🗺️  Calling Google Maps API: {parsed.get('origin') or settings.DEFAULT_ORIGIN} → {parsed['destination']} ({parsed.get('mode') or 'driving'})")
        data = navigate_route(
            gmaps_client=gmaps_client,
            destination=parsed["destination"],
            origin=parsed.get("origin"),
            mode=parsed.get("mode") or "driving",
            default_origin=settings.DEFAULT_ORIGIN,
        )
        if data:
            debug_info.append(f"✅ Route planning successful: {data.get('distance_text')}, {data.get('duration_text')}")
            origin_text = parsed.get("origin") or "Current location"
            mode_text = {"driving": "Driving", "walking": "Walking", "transit": "Transit", "bicycling": "Cycling"}.get(parsed.get("mode") or "driving", "Driving")
            reply = f"🗺️ Route planned for you!\n\n📍 {origin_text} → {parsed['destination']}\n🚗 Mode: {mode_text}\n📏 Distance: {data.get('distance_text')}\n⏱️ Est. time: {data.get('duration_text')}\n🛣️ Route: {data.get('summary') or 'Generated'}"
            _append_history(session_id, "user", msg)
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply, "tool": "navigate", "data": data, "debug": debug_info}
        else:
            # Parsed destination but navigation failed
            debug_info.append("❌ Route planning failed: Google Maps API returned empty result")
            reply = f"Unable to find a route to '{parsed['destination']}' at the moment 😅\n\nPossible reasons:\n• Location name not specific enough\n• Navigation not supported for this location\n\nTry providing a more detailed address or rephrase~"
            _append_history(session_id, "user", msg)
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply, "debug": debug_info}
    
    debug_info.append("💬 Using simple reply")
    reply = _simple_chat_reply(msg)
    _append_history(session_id, "user", msg)
    _append_history(session_id, "assistant", reply)
    return {"session_id": session_id, "reply": reply, "debug": debug_info}


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

