"""
角色加载器
从 roles 目录加载所有角色配置
"""
import os
import importlib.util
from typing import Dict, List


class RoleLoader:
    """角色加载器"""

    def __init__(self, roles_dir: str = "roles"):
        """
        初始化角色加载器

        Args:
            roles_dir: 角色配置文件目录
        """
        self.roles_dir = roles_dir
        self.roles = {}
        self._load_roles()

    def _load_roles(self):
        """从目录加载所有角色"""
        if not os.path.exists(self.roles_dir):
            print(f"警告: 角色目录 {self.roles_dir} 不存在")
            return

        for filename in os.listdir(self.roles_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                role_id = filename[:-3]  # 去掉 .py
                role_path = os.path.join(self.roles_dir, filename)

                try:
                    # 动态加载模块
                    spec = importlib.util.spec_from_file_location(role_id, role_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # 获取角色配置
                    if hasattr(module, 'ROLE_CONFIG'):
                        config = module.ROLE_CONFIG
                        if not isinstance(config, dict):
                            print(f"警告: {filename} 的 ROLE_CONFIG 不是 dict，已跳过")
                            continue

                        # 兼容缺失字段：用文件名派生默认值，避免 KeyError 影响整体加载
                        defaults = {
                            'id': role_id,
                            'name': role_id,
                            'personality': '',
                            'style': '',
                            'description': '',
                            'custom_prompt': None
                        }
                        missing_keys = [k for k in defaults.keys() if k not in config]
                        for k, v in defaults.items():
                            config.setdefault(k, v)

                        if missing_keys:
                            print(
                                f"警告: {filename} 缺少字段 {missing_keys}，已使用默认值补齐"
                            )

                        if config['id'] in self.roles:
                            print(
                                f"警告: 角色 id 重复: {config['id']}（来自 {filename}），已跳过"
                            )
                            continue

                        self.roles[config['id']] = config
                        # print(f"✓ 加载角色: {config['name']} ({config['id']})")  # 静默加载
                    else:
                        print(f"警告: {filename} 缺少 ROLE_CONFIG")

                except Exception as e:
                    print(f"错误: 加载 {filename} 失败: {str(e)}")

    def get_role(self, role_id: str) -> Dict:
        """
        获取角色配置

        Args:
            role_id: 角色 ID

        Returns:
            角色配置字典
        """
        return self.roles.get(role_id)

    def list_roles(self) -> List[Dict]:
        """
        列出所有角色

        Returns:
            角色列表
        """
        return list(self.roles.values())

    def get_role_ids(self) -> List[str]:
        """
        获取所有角色 ID

        Returns:
            角色 ID 列表
        """
        return list(self.roles.keys())

    def display_roles(self):
        """显示所有可用角色"""
        if not self.roles:
            print("没有可用的角色")
            return

        print("\n可用角色:")
        print("=" * 60)
        for i, (role_id, config) in enumerate(self.roles.items(), 1):
            print(f"{i}. {config.get('name', role_id)} ({role_id})")
            print(f"   特点: {config.get('personality', '')}")
            print(f"   风格: {config.get('style', '')}")
            print(f"   说明: {config.get('description', '')}")
            print()

    def select_role_interactive(self) -> str:
        """
        交互式选择角色

        Returns:
            选择的角色 ID
        """
        if not self.roles:
            print("没有可用的角色，使用默认配置")
            return None

        self.display_roles()

        role_list = list(self.roles.keys())

        while True:
            try:
                choice = input(f"请选择角色 (1-{len(role_list)}) 或直接回车使用第一个: ").strip()

                if not choice:
                    # 默认选择第一个
                    selected_id = role_list[0]
                    print(f"✓ 已选择: {self.roles[selected_id]['name']}")
                    return selected_id

                choice_num = int(choice)
                if 1 <= choice_num <= len(role_list):
                    selected_id = role_list[choice_num - 1]
                    print(f"✓ 已选择: {self.roles[selected_id]['name']}")
                    return selected_id
                else:
                    print(f"请输入 1-{len(role_list)} 之间的数字")

            except ValueError:
                print("请输入有效的数字")
            except KeyboardInterrupt:
                print("\n已取消")
                return None


# 测试代码
if __name__ == "__main__":
    loader = RoleLoader()
    loader.display_roles()

    print("\n测试交互选择:")
    selected = loader.select_role_interactive()
    if selected:
        print(f"\n最终选择: {loader.get_role(selected)}")
