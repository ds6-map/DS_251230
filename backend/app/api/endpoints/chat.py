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
    """当 LLM 不可用时的降级回复，尽量覆盖更多常见场景"""
    m = msg.strip().lower()
    original = msg.strip()
    
    # 问候类
    greetings = ["你好", "hi", "hello", "嗨", "早上好", "下午好", "晚上好", "您好"]
    if any(g in m for g in greetings):
        return "你好！我是你的智能助手，可以帮你规划路线、回答问题或者闲聊。有什么可以帮到你的吗？"
    
    # 感谢类
    thanks = ["谢谢", "感谢", "thanks", "thank you", "多谢", "3q"]
    if any(t in m for t in thanks):
        return "不客气！如果还有其他问题，随时问我~"
    
    # 再见类
    byes = ["再见", "拜拜", "bye", "goodbye", "88", "晚安"]
    if any(b in m for b in byes):
        return "再见！祝你一路顺风~ 🌟"
    
    # 能力询问
    ability_keywords = ["你能做什么", "你会什么", "有什么功能", "怎么用", "如何使用", "help", "帮助"]
    if any(k in m for k in ability_keywords):
        return "我可以帮你：\n1️⃣ 规划路线 - 告诉我你要从哪里去哪里\n2️⃣ 识别位置 - 上传一张照片，我帮你识别在哪\n3️⃣ 解答问题 - 问我关于地点、交通等问题\n\n试试说「从 NTU 到樟宜机场」或者「导航到 Orchard Road」"
    
    # 天气相关
    weather_keywords = ["天气", "下雨", "晴天", "weather", "温度"]
    if any(k in m for k in weather_keywords):
        return "新加坡常年温暖，温度约25-32°C，建议出门带伞以防阵雨。具体天气可以查看 weather.gov.sg 获取实时信息~"
    
    # 地点介绍类
    if "ntu" in m or "南洋理工" in m:
        return "南洋理工大学(NTU)位于新加坡西部，是亚洲顶尖学府之一。校园很大很美，有很多特色建筑如 The Hive。从市区可乘地铁到 Pioneer 站再转公交，或直接驾车/打车前往。"
    if "樟宜" in m or "机场" in m or "changi" in m:
        return "樟宜机场(Changi Airport)位于新加坡东部，是全球最佳机场之一。有 Jewel 星耀樟宜值得逛逛。从市区可乘地铁东西线或直接打车，约20-40分钟到达。"
    if "乌节" in m or "orchard" in m:
        return "乌节路(Orchard Road)是新加坡最著名的购物街，ION、高岛屋、义安城等商场云集。乘地铁到 Orchard 站即可到达。"
    if "滨海湾" in m or "marina bay" in m or "金沙" in m:
        return "滨海湾金沙(Marina Bay Sands)是新加坡地标，有无边泳池、赌场、购物中心和艺术科学博物馆。乘地铁到 Bayfront 站即可到达。"
    if "圣淘沙" in m or "sentosa" in m:
        return "圣淘沙岛(Sentosa)是新加坡的度假胜地，有环球影城、S.E.A海洋馆、海滩等。可乘轻轨或步行从 VivoCity 前往。"
    
    # 交通方式询问
    transport_keywords = ["怎么去", "如何到", "怎么到", "how to go", "how to get"]
    if any(k in m for k in transport_keywords):
        return "新加坡出行方式很多：\n🚇 地铁(MRT) - 覆盖主要区域，方便快捷\n🚌 公交 - 线路密集，可用 EZ-Link 卡\n🚕 打车 - Grab/ComfortDelGro/Gojek\n🚶 步行 - 市区内很多地方步行可达\n\n告诉我你要从哪去哪，我帮你规划路线！"
    
    # 美食相关
    food_keywords = ["吃什么", "美食", "餐厅", "food", "eat", "restaurant", "推荐吃"]
    if any(k in m for k in food_keywords):
        return "新加坡美食超多！推荐尝试：\n🍜 海南鸡饭、叻沙、肉骨茶\n🦀 辣椒螃蟹、黑胡椒蟹\n🍢 沙爹、炒粿条\n\n可以去牛车水、老巴刹、麦士威熟食中心等地方找地道美食~"
    
    # 询问类问题的通用回复
    question_words = ["什么", "哪里", "怎么", "为什么", "多少", "几", "吗", "呢", "?", "？"]
    if any(q in m for q in question_words):
        return f"这是个好问题！关于「{original}」，建议你可以：\n1. 尝试更具体地描述需求\n2. 如果是路线问题，告诉我起点和终点\n3. 如果是位置识别，可以上传照片\n\n我会尽力帮助你！"
    
    # 默认回复 - 更友好
    return f"收到你的消息了！如果你需要路线规划，可以说「从XX到XX」；如果想了解某个地方，直接问我就好~ 😊"


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
    import logging
    logger = logging.getLogger(__name__)
    debug_info = []  # 调试信息列表
    
    session_id = _get_session_id(req.session_id)
    msg = (req.message or "").strip()
    if not msg and not req.image_base64:
        return {"session_id": session_id, "reply": "请输入内容", "debug": debug_info}
    
    debug_info.append(f"📥 收到消息: {msg[:50]}...")

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
    
    # 检查服务状态
    debug_info.append(f"🤖 LLM 客户端: {'✅ 已配置' if openai_client else '❌ 未配置'}")
    debug_info.append(f"🗺️  Google Maps 客户端: {'✅ 已配置' if gmaps_client else '❌ 未配置'}")

    # 使用 LLM 处理
    if openai_client:
        debug_info.append("🚀 使用 LLM 处理请求")
        tools = _tools_schema()
        history = _get_history(session_id)
        system_prompt = """你是一个友好、智能的导航和问答助手。你的职责是：

1. **路线规划**：当用户询问如何从A到B、要去某地、需要导航时，调用 navigate 工具。
   - 如果用户没说起点，可以假设从当前位置（NTU）出发
   - 支持多种交通方式：driving(驾车)、walking(步行)、transit(公共交通)、bicycling(骑行)

2. **普通对话**：对于问候、闲聊、知识问答等，直接用自然语言回复，不需要调用工具。
   - 保持友好、热情的语气
   - 可以用emoji让回复更生动
   - 如果不确定，可以引导用户提供更多信息

3. **灵活应对**：
   - 如果用户问题模糊，先尝试理解意图再决定是否调用工具
   - 如果是关于地点的介绍、推荐等，直接回答，不需要导航
   - 对于复杂问题，可以分步骤回答

请用中文回复，保持简洁但有用。"""
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
            debug_info.append(f"🔍 LLM 第一次调用完成，是否调用工具: {'是' if tool_calls else '否'}")
            if tool_calls:
                debug_info.append(f"🛠️  检测到 {len(tool_calls)} 个工具调用")
                tool_payloads: List[Dict[str, Any]] = []
                route_data = None
                for tc in tool_calls:
                    if tc.function.name != "navigate":
                        continue
                    args = json.loads(tc.function.arguments or "{}")
                    destination = (args.get("destination") or "").strip()
                    origin = args.get("origin")
                    mode = args.get("mode") or "driving"
                    
                    debug_info.append(f"📍 解析参数: origin={origin or 'None'}, destination={destination}, mode={mode}")
                    
                    if not destination:
                        debug_info.append("❌ 目的地为空，返回提示")
                        reply = "请问您想去哪里？"
                        _append_history(session_id, "user", msg)
                        _append_history(session_id, "assistant", reply)
                        return {"session_id": session_id, "reply": reply, "debug": debug_info}
                    
                    debug_info.append(f"🗺️  调用 Google Maps API: {origin or settings.DEFAULT_ORIGIN} → {destination} ({mode})")
                    route_data = navigate_route(
                        gmaps_client=gmaps_client,
                        destination=destination,
                        origin=origin,
                        mode=mode,
                        default_origin=settings.DEFAULT_ORIGIN,
                    )
                    if route_data:
                        debug_info.append(f"✅ 路线规划成功: {route_data.get('distance_text')}, {route_data.get('duration_text')}")
                    else:
                        debug_info.append("❌ 路线规划失败: Google Maps API 返回空结果")
                    tool_payloads.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(route_data, ensure_ascii=False),
                        }
                    )

                # 第二次调用：把工具结果回传给模型，让它生成自然语言回复
                if route_data:
                    second_messages = messages + [assistant_msg.model_dump()] + tool_payloads
                    second = openai_client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=second_messages,
                    )
                    reply_text = second.choices[0].message.content or "路线已生成"
                    debug_info.append("💬 LLM 生成回复完成")
                    _append_history(session_id, "user", msg)
                    _append_history(session_id, "assistant", reply_text)
                    return {
                        "session_id": session_id,
                        "reply": reply_text,
                        "tool": "navigate",
                        "data": route_data,
                        "debug": debug_info,
                    }
                
                # 导航失败时，让 LLM 生成更友好的回复
                try:
                    fallback_resp = openai_client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=messages + [{"role": "user", "content": f"用户说：{msg}\n但是导航工具没有找到路线。请用友好的方式告诉用户，并询问是否需要帮助。不要使用'抱歉，未找到可行路线'这样机械的回复。"}],
                    )
                    reply = fallback_resp.choices[0].message.content or "暂时无法规划这条路线，可以尝试提供更具体的地址吗？"
                except Exception:
                    reply = "暂时无法规划这条路线 😅\n\n可能的原因：\n• 地点名称不够具体\n• 地图服务暂时不可用\n\n试试提供更详细的地址？或者换个说法~"
                debug_info.append("💬 LLM 生成失败回复完成")
                _append_history(session_id, "user", msg)
                _append_history(session_id, "assistant", reply)
                return {"session_id": session_id, "reply": reply, "debug": debug_info}

            reply = assistant_msg.content or ""
            debug_info.append("💬 LLM 直接回复（未调用工具）")
            _append_history(session_id, "user", msg)
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply, "debug": debug_info}
        except Exception as e:
            # 记录 LLM 调用错误，但不中断流程，降级到正则解析
            logger.warning(f"LLM API 调用失败，降级到正则解析: {e}", exc_info=True)
            debug_info.append(f"⚠️  LLM 调用失败: {str(e)[:100]}，降级到正则解析")
            # 继续执行下面的降级逻辑

    # LLM 不可用或失败：用正则做一次导航意图解析作为兜底
    if not openai_client:
        logger.info("[chat] LLM 客户端未配置，使用降级回复")
        debug_info.append("⚠️  LLM 未配置，使用正则解析")
    logger.debug(f"[chat] 使用正则解析或固定回复处理: {msg[:50]}...")
    debug_info.append("🔍 开始正则解析导航查询")
    parsed = parse_navigation_query(msg)
    debug_info.append(f"📋 解析结果: {parsed}")
    if parsed.get("destination"):
        debug_info.append(f"🗺️  调用 Google Maps API: {parsed.get('origin') or settings.DEFAULT_ORIGIN} → {parsed['destination']} ({parsed.get('mode') or 'driving'})")
        data = navigate_route(
            gmaps_client=gmaps_client,
            destination=parsed["destination"],
            origin=parsed.get("origin"),
            mode=parsed.get("mode") or "driving",
            default_origin=settings.DEFAULT_ORIGIN,
        )
        if data:
            debug_info.append(f"✅ 路线规划成功: {data.get('distance_text')}, {data.get('duration_text')}")
            origin_text = parsed.get("origin") or "当前位置"
            mode_text = {"driving": "驾车", "walking": "步行", "transit": "公共交通", "bicycling": "骑行"}.get(parsed.get("mode") or "driving", "驾车")
            reply = f"🗺️ 已为你规划好路线！\n\n📍 {origin_text} → {parsed['destination']}\n🚗 方式：{mode_text}\n📏 距离：{data.get('distance_text')}\n⏱️ 预计：{data.get('duration_text')}\n🛣️ 路线：{data.get('summary') or '已生成'}"
            _append_history(session_id, "user", msg)
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply, "tool": "navigate", "data": data, "debug": debug_info}
        else:
            # 解析到了目的地但导航失败
            debug_info.append("❌ 路线规划失败: Google Maps API 返回空结果")
            reply = f"暂时无法找到去「{parsed['destination']}」的路线 😅\n\n可能的原因：\n• 地点名称不够具体\n• 该地点暂不支持导航\n\n试试提供更详细的地址？或者换个说法~"
            _append_history(session_id, "user", msg)
            _append_history(session_id, "assistant", reply)
            return {"session_id": session_id, "reply": reply, "debug": debug_info}
    
    debug_info.append("💬 使用简单回复")
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

