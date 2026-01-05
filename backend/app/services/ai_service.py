"""
AI 服务模块
视觉定位和图像识别（当前为 Mock 实现）
"""
import random
from typing import List, Optional
from app.schemas import LocationCandidate
from app.services.graph_service import graph_service
from app.core.config import settings


class AIService:
    """
    AI 服务类
    提供图像识别和视觉定位功能
    
    当前实现：Mock 数据
    未来实现：CLIP 模型 + FAISS 向量检索
    """
    
    def __init__(self):
        self._model_loaded = False
        self._mock_mode = settings.AI_MOCK_MODE
    
    async def load_model(self) -> None:
        """
        加载 AI 模型
        
        TODO: 实现 CLIP 模型加载
        - 使用 sentence-transformers 或 transformers 库
        - 加载预训练的 CLIP 模型
        - 初始化 FAISS 索引
        """
        if self._mock_mode:
            # Mock 模式下不需要加载模型
            self._model_loaded = True
            return
        
        # TODO: 实际模型加载代码
        # from sentence_transformers import SentenceTransformer
        # self.model = SentenceTransformer(settings.CLIP_MODEL_NAME)
        # self._model_loaded = True
        pass
    
    async def recognize_location(
        self,
        image_data: bytes,
        top_k: int = 3
    ) -> List[LocationCandidate]:
        """
        识别图片中的位置
        
        Args:
            image_data: 图片二进制数据
            top_k: 返回前 K 个候选结果
            
        Returns:
            LocationCandidate 列表，按置信度降序排列
            
        TODO: 实现步骤
        1. OCR 识别（可选）：尝试识别图中文字
        2. CLIP 编码：将图片转为向量
        3. 向量检索：与预存的节点向量库比对
        4. 返回 Top K 结果
        """
        if self._mock_mode:
            return await self._mock_recognize(top_k)
        
        # TODO: 实际识别代码
        # 1. OCR 识别
        # ocr_result = await self._ocr_recognize(image_data)
        # if ocr_result:
        #     return ocr_result
        
        # 2. CLIP 向量检索
        # image_vector = await self._extract_image_features(image_data)
        # candidates = await self._search_similar_nodes(image_vector, top_k)
        # return candidates
        
        return await self._mock_recognize(top_k)
    
    async def _mock_recognize(self, top_k: int = 3) -> List[LocationCandidate]:
        """
        Mock 识别实现
        随机返回一些节点作为候选结果
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🎲 [Mock识别] 开始 Mock 识别，请求 top_k={top_k}")
        
        all_nodes = graph_service.get_all_nodes()
        logger.info(f"📊 [Mock识别] 图中共有 {len(all_nodes)} 个节点")
        
        if not all_nodes:
            logger.warning("⚠️ [Mock识别] 图结构中没有节点数据")
            return []
        
        # 随机选择节点
        sample_size = min(top_k, len(all_nodes))
        selected_nodes = random.sample(all_nodes, sample_size)
        logger.info(f"🎯 [Mock识别] 随机选择了 {sample_size} 个节点")
        
        # 生成随机置信度（按降序排列）
        confidences = sorted([random.uniform(0.5, 0.95) for _ in range(sample_size)], reverse=True)
        
        candidates = []
        for i, node in enumerate(selected_nodes):
            candidate = LocationCandidate(
                node_id=node["id"],
                node_name=node["name"],
                detail=node.get("detail"),
                floor=node["floor"],
                confidence=round(confidences[i], 2),
            )
            candidates.append(candidate)
            logger.info(f"  [{i+1}] 节点: {node['name']} (ID: {node['id']}, 楼层: {node['floor']}, 置信度: {candidate.confidence})")
        
        logger.info(f"✅ [Mock识别] 完成，返回 {len(candidates)} 个候选结果")
        return candidates
    
    async def _extract_image_features(self, image_data: bytes):
        """
        提取图像特征向量
        
        TODO: 使用 CLIP 模型提取特征
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            特征向量 (numpy array)
        """
        # TODO: 实现图像特征提取
        # from PIL import Image
        # import io
        # image = Image.open(io.BytesIO(image_data))
        # features = self.model.encode(image)
        # return features
        pass
    
    async def _search_similar_nodes(
        self,
        query_vector,
        top_k: int = 3
    ) -> List[LocationCandidate]:
        """
        在向量库中搜索相似节点
        
        TODO: 使用 FAISS 或简单余弦相似度
        
        Args:
            query_vector: 查询向量
            top_k: 返回前 K 个结果
            
        Returns:
            LocationCandidate 列表
        """
        # TODO: 实现向量检索
        # distances, indices = self.faiss_index.search(query_vector, top_k)
        # 或使用简单的余弦相似度
        # similarities = cosine_similarity(query_vector, node_vectors)
        pass
    
    async def _ocr_recognize(self, image_data: bytes) -> Optional[List[LocationCandidate]]:
        """
        OCR 识别图片中的文字
        
        TODO: 使用 PaddleOCR 识别文字
        
        Args:
            image_data: 图片二进制数据
            
        Returns:
            如果识别到匹配的节点，返回 LocationCandidate 列表
            否则返回 None
        """
        # TODO: 实现 OCR 识别
        # from paddleocr import PaddleOCR
        # ocr = PaddleOCR()
        # result = ocr.ocr(image_data)
        # 解析结果，匹配节点名称
        pass


# 全局单例
ai_service = AIService()

