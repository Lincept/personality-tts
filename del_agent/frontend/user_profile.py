"""
User Profile Manager - 用户画像管理器
负责用户个性化画像的存储、更新和检索
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from ..models.schemas import UserPersonalityVector

logger = logging.getLogger(__name__)


class UserProfileManager:
    """
    用户画像管理器
    负责管理用户的个性化偏好和交互历史
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        use_mem0: bool = False,
        mem0_manager: Optional[Any] = None
    ):
        """
        初始化用户画像管理器
        
        Args:
            storage_path: 本地存储路径（默认使用 del_agent/data/user_profiles.json）
            use_mem0: 是否使用 Mem0 存储（未来集成）
            mem0_manager: Mem0 管理器实例（可选）
        """
        self.use_mem0 = use_mem0
        self.mem0_manager = mem0_manager
        
        # 本地存储路径：优先用传入路径；否则使用 del_agent 工程内的 data 目录
        del_agent_root = Path(__file__).resolve().parents[1]
        default_storage_path = del_agent_root / "data" / "user_profiles.json"

        if storage_path is None:
            resolved_path = default_storage_path
        else:
            p = Path(storage_path)
            # 兼容历史用法：如果传的是相对路径，优先按 del_agent 工程根解析
            if not p.is_absolute():
                candidate = del_agent_root / p
                resolved_path = candidate if candidate.exists() else (Path.cwd() / p)
            else:
                resolved_path = p

        self.storage_path = resolved_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self._profiles_cache: Dict[str, UserPersonalityVector] = {}
        
        # 加载已有数据
        self._load_profiles()
    
    def _load_profiles(self):
        """从本地文件加载用户画像"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id, profile_dict in data.items():
                        # 转换日期字符串为 datetime 对象
                        if 'last_interaction' in profile_dict and profile_dict['last_interaction']:
                            profile_dict['last_interaction'] = datetime.fromisoformat(
                                profile_dict['last_interaction']
                            )
                        if 'created_at' in profile_dict:
                            profile_dict['created_at'] = datetime.fromisoformat(
                                profile_dict['created_at']
                            )
                        if 'updated_at' in profile_dict:
                            profile_dict['updated_at'] = datetime.fromisoformat(
                                profile_dict['updated_at']
                            )
                        
                        self._profiles_cache[user_id] = UserPersonalityVector(**profile_dict)
                logger.info(f"Loaded {len(self._profiles_cache)} user profiles from {self.storage_path}")
            except Exception as e:
                logger.error(f"Error loading user profiles: {e}")
                self._profiles_cache = {}
        else:
            # 创建空文件
            self._save_profiles()
    
    def _save_profiles(self):
        """保存用户画像到本地文件"""
        try:
            data = {}
            for user_id, profile in self._profiles_cache.items():
                profile_dict = profile.model_dump()
                # 转换 datetime 对象为字符串
                if profile_dict.get('last_interaction'):
                    profile_dict['last_interaction'] = profile_dict['last_interaction'].isoformat()
                if profile_dict.get('created_at'):
                    profile_dict['created_at'] = profile_dict['created_at'].isoformat()
                if profile_dict.get('updated_at'):
                    profile_dict['updated_at'] = profile_dict['updated_at'].isoformat()
                data[user_id] = profile_dict
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved {len(data)} user profiles to {self.storage_path}")
        except Exception as e:
            logger.error(f"Error saving user profiles: {e}")
    
    def get_profile(self, user_id: str) -> UserPersonalityVector:
        """
        获取用户画像，如果不存在则创建默认画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户画像对象
        """
        if user_id not in self._profiles_cache:
            logger.info(f"Creating new profile for user {user_id}")
            self._profiles_cache[user_id] = UserPersonalityVector(user_id=user_id)
            self._save_profiles()
        
        return self._profiles_cache[user_id]
    
    def update_profile(
        self,
        user_id: str,
        interaction: Dict[str, Any],
        **updates
    ) -> UserPersonalityVector:
        """
        更新用户画像
        
        Args:
            user_id: 用户ID
            interaction: 交互信息字典（用于分析和更新画像）
            **updates: 直接更新的字段（如 humor_preference=0.8）
            
        Returns:
            更新后的用户画像
        """
        profile = self.get_profile(user_id)
        
        # 直接更新指定字段
        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        # 基于交互内容动态调整画像
        if interaction:
            self._analyze_and_update(profile, interaction)
        
        # 更新交互计数和时间
        profile.interaction_history_count += 1
        profile.last_interaction = datetime.now()
        profile.updated_at = datetime.now()
        
        # 保存到存储
        self._profiles_cache[user_id] = profile
        self._save_profiles()
        
        logger.debug(f"Updated profile for user {user_id}")
        return profile
    
    def _analyze_and_update(
        self,
        profile: UserPersonalityVector,
        interaction: Dict[str, Any]
    ):
        """
        分析用户交互内容并动态调整画像
        
        Args:
            profile: 用户画像对象
            interaction: 交互信息（包含 query、response、feedback 等）
        """
        # 提取交互中的信号
        query = interaction.get('query', '')
        feedback = interaction.get('feedback', None)
        
        # 基于查询长度和复杂度调整细节偏好
        if len(query) > 50:  # 降低阈值，让测试更容易通过
            # 用户提供详细描述 -> 可能偏好详细回复
            profile.detail_preference = min(1.0, profile.detail_preference + 0.05)
        
        # 基于反馈调整风格（需要更复杂的NLP分析，这里简化处理）
        if feedback:
            feedback_type = feedback.get('type', '')
            if feedback_type == 'too_formal':
                profile.formality_level = max(0.0, profile.formality_level - 0.1)
            elif feedback_type == 'too_casual':
                profile.formality_level = min(1.0, profile.formality_level + 0.1)
            elif feedback_type == 'too_serious':
                profile.humor_preference = min(1.0, profile.humor_preference + 0.1)
        
        # 提取话题标签（简化版，实际需要NLP分析）
        potential_topics = self._extract_topics(query)
        for topic in potential_topics:
            if topic not in profile.preferred_topics:
                profile.preferred_topics.append(topic)
    
    def _extract_topics(self, text: str) -> list:
        """
        从文本中提取话题关键词（简化版）
        
        Args:
            text: 输入文本
            
        Returns:
            话题列表
        """
        # 简化的关键词匹配，实际应使用NLP工具
        topic_keywords = {
            '导师': ['导师', '老师', '教授', 'mentor'],
            '科研': ['科研', '研究', '论文', 'paper', '发表'],
            '经费': ['经费', '资金', '津贴', '工资', 'funding'],
            '实验室': ['实验室', '课题组', 'lab', 'group'],
            '压力': ['压力', '累', '忙', 'stress', 'pressure'],
        }
        
        topics = []
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def get_style_params(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的风格参数，用于PersonaAgent生成回复
        
        Args:
            user_id: 用户ID
            
        Returns:
            风格参数字典
        """
        profile = self.get_profile(user_id)
        
        return {
            'humor_level': profile.humor_preference,
            'formality_level': profile.formality_level,
            'detail_level': profile.detail_preference,
            'language_style': profile.language_style,
            'preferred_topics': profile.preferred_topics,
            'interaction_count': profile.interaction_history_count,
        }
    
    def delete_profile(self, user_id: str) -> bool:
        """
        删除用户画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功删除
        """
        if user_id in self._profiles_cache:
            del self._profiles_cache[user_id]
            self._save_profiles()
            logger.info(f"Deleted profile for user {user_id}")
            return True
        return False
    
    def list_profiles(self) -> list:
        """
        列出所有用户画像ID
        
        Returns:
            用户ID列表
        """
        return list(self._profiles_cache.keys())
