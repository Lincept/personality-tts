"""
测试用户画像管理器
Phase 3.2: 验证 UserProfileManager 功能
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from del_agent.frontend.user_profile import UserProfileManager
from del_agent.models.schemas import UserPersonalityVector


class TestUserProfileManager:
    """测试用户画像管理器"""
    
    @pytest.fixture
    def temp_storage_dir(self):
        """创建临时存储目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def profile_manager(self, temp_storage_dir):
        """创建测试用的画像管理器"""
        storage_path = Path(temp_storage_dir) / "test_profiles.json"
        return UserProfileManager(storage_path=str(storage_path))
    
    def test_create_profile_manager(self, profile_manager):
        """测试创建画像管理器"""
        assert profile_manager is not None
        assert profile_manager.storage_path.exists()
    
    def test_get_new_profile(self, profile_manager):
        """测试获取新用户的默认画像"""
        user_id = "test_user_001"
        profile = profile_manager.get_profile(user_id)
        
        assert profile is not None
        assert profile.user_id == user_id
        assert profile.humor_preference == 0.5
        assert profile.formality_level == 0.5
        assert profile.detail_preference == 0.5
        assert profile.interaction_history_count == 0
        assert isinstance(profile.created_at, datetime)
    
    def test_get_existing_profile(self, profile_manager):
        """测试获取已存在的用户画像"""
        user_id = "test_user_002"
        
        # 首次获取，创建新画像
        profile1 = profile_manager.get_profile(user_id)
        created_at1 = profile1.created_at
        
        # 再次获取，应该返回同一个画像
        profile2 = profile_manager.get_profile(user_id)
        assert profile2.created_at == created_at1
    
    def test_update_profile_direct(self, profile_manager):
        """测试直接更新用户画像字段"""
        user_id = "test_user_003"
        
        # 更新画像
        updated_profile = profile_manager.update_profile(
            user_id=user_id,
            interaction={},
            humor_preference=0.8,
            formality_level=0.3,
            language_style="casual"
        )
        
        assert updated_profile.humor_preference == 0.8
        assert updated_profile.formality_level == 0.3
        assert updated_profile.language_style == "casual"
        assert updated_profile.interaction_history_count == 1
        assert updated_profile.last_interaction is not None
    
    def test_update_profile_with_interaction(self, profile_manager):
        """测试基于交互内容更新画像"""
        user_id = "test_user_004"
        
        # 模拟一个关于导师的详细查询（51个字符以上触发细节偏好提升）
        interaction = {
            'query': '我想详细了解一下张三老师的科研情况，特别是他在经费管理和学生培养方面的表现如何？他的实验室氛围怎么样？',
            'response': '...',
        }
        
        profile = profile_manager.update_profile(
            user_id=user_id,
            interaction=interaction
        )
        
        # 由于查询较长（超过50字符），细节偏好应该有所提升
        assert profile.detail_preference > 0.5
        # 应该提取出相关话题
        assert '导师' in profile.preferred_topics or '科研' in profile.preferred_topics or '经费' in profile.preferred_topics
    
    def test_update_profile_with_feedback(self, profile_manager):
        """测试基于用户反馈更新画像"""
        user_id = "test_user_005"
        
        # 初始画像
        profile_manager.get_profile(user_id)
        
        # 模拟用户反馈：回复太正式了
        interaction = {
            'query': '导师怎么样？',
            'response': '...',
            'feedback': {
                'type': 'too_formal'
            }
        }
        
        updated_profile = profile_manager.update_profile(
            user_id=user_id,
            interaction=interaction
        )
        
        # 正式度应该降低
        assert updated_profile.formality_level < 0.5
    
    def test_get_style_params(self, profile_manager):
        """测试获取风格参数"""
        user_id = "test_user_006"
        
        # 更新画像
        profile_manager.update_profile(
            user_id=user_id,
            interaction={'query': '导师的科研经费情况'},
            humor_preference=0.7,
            formality_level=0.4,
            detail_preference=0.6
        )
        
        # 获取风格参数
        style_params = profile_manager.get_style_params(user_id)
        
        assert style_params['humor_level'] == 0.7
        assert style_params['formality_level'] == 0.4
        assert style_params['detail_level'] == 0.6
        assert style_params['interaction_count'] == 1
        assert isinstance(style_params['preferred_topics'], list)
    
    def test_persistence(self, temp_storage_dir):
        """测试持久化存储"""
        storage_path = Path(temp_storage_dir) / "persistence_test.json"
        
        # 创建第一个管理器并添加用户
        manager1 = UserProfileManager(storage_path=str(storage_path))
        manager1.update_profile(
            user_id="persistent_user",
            interaction={},
            humor_preference=0.9
        )
        
        # 创建第二个管理器，应该能加载之前保存的数据
        manager2 = UserProfileManager(storage_path=str(storage_path))
        profile = manager2.get_profile("persistent_user")
        
        assert profile.humor_preference == 0.9
        assert profile.interaction_history_count == 1
    
    def test_delete_profile(self, profile_manager):
        """测试删除用户画像"""
        user_id = "test_user_007"
        
        # 创建画像
        profile_manager.get_profile(user_id)
        assert user_id in profile_manager.list_profiles()
        
        # 删除画像
        result = profile_manager.delete_profile(user_id)
        assert result is True
        assert user_id not in profile_manager.list_profiles()
        
        # 尝试删除不存在的画像
        result = profile_manager.delete_profile("non_existent_user")
        assert result is False
    
    def test_list_profiles(self, profile_manager):
        """测试列出所有用户画像"""
        users = ["user_a", "user_b", "user_c"]
        
        for user_id in users:
            profile_manager.get_profile(user_id)
        
        profiles_list = profile_manager.list_profiles()
        assert len(profiles_list) == 3
        for user_id in users:
            assert user_id in profiles_list
    
    def test_multiple_interactions(self, profile_manager):
        """测试多次交互的累积效果"""
        user_id = "test_user_008"
        
        # 第一次交互
        profile_manager.update_profile(
            user_id=user_id,
            interaction={'query': '导师经费如何？'}
        )
        
        # 第二次交互
        profile_manager.update_profile(
            user_id=user_id,
            interaction={'query': '科研压力大吗？'}
        )
        
        # 第三次交互
        profile_manager.update_profile(
            user_id=user_id,
            interaction={'query': '实验室氛围怎么样？'}
        )
        
        profile = profile_manager.get_profile(user_id)
        
        # 交互次数应该累积
        assert profile.interaction_history_count == 3
        # 应该提取了多个话题
        assert len(profile.preferred_topics) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
