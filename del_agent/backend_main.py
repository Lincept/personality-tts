#!/usr/bin/env python3
"""
backend_main.py - 后端批量处理入口

功能：
1. 加载 data/professors 中的评论数据
2. 通过 DataFactoryPipeline 处理并压缩成知识
3. 存储到向量数据库
4. 验证和展示存储结果

使用方式：
    python backend_main.py --help              # 查看帮助
    python backend_main.py process --limit 5   # 处理5个文件
    python backend_main.py show --limit 10     # 展示10条存储记录
    python backend_main.py stats               # 查看统计信息

环境变量（.env）：
    BACKEND_TRACE_ENABLED=true/false   # 控制跟踪输出
    BACKEND_VERBOSE=true/false         # 控制详细日志
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# 添加项目根路径
PROJECT_ROOT = Path(__file__).parent.absolute()
if str(PROJECT_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT.parent))

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# 从环境变量读取标志位
def _env_bool(key: str, default: bool = False) -> bool:
    """从环境变量读取布尔值"""
    val = os.getenv(key, "").lower()
    if val in ("true", "1", "yes", "on"):
        return True
    elif val in ("false", "0", "no", "off"):
        return False
    return default

ENV_TRACE_ENABLED = _env_bool("BACKEND_TRACE_ENABLED", False)
ENV_VERBOSE = _env_bool("BACKEND_VERBOSE", False)

# 禁用 logging（使用 print + 标志位控制输出）
logging.disable(logging.CRITICAL)

from del_agent.models.schemas import RawReview, StructuredKnowledgeNode
from del_agent.backend.factory import DataFactoryPipeline
from del_agent.core.llm_adapter import OpenAICompatibleProvider
from del_agent.storage.unified_store import (
    KnowledgeStore, KnowledgeRecord,
    create_knowledge_store
)
from del_agent.utils.config import ConfigManager


class BackendProcessor:
    """后端批量处理器"""
    
    def __init__(
        self,
        data_dir: str,
        config_path: Optional[str] = None,
        trace_enabled: Optional[bool] = None,
        enable_verification: bool = False,
        storage_backend: str = "json"
    ):
        """
        初始化处理器
        
        Args:
            data_dir: 数据目录路径
            config_path: 配置文件路径
            trace_enabled: 是否启用跟踪输出（None则从.env读取）
            enable_verification: 是否启用核验
            storage_backend: 存储后端 ("json", "mem0", "hybrid")
        """
        self.storage_backend = storage_backend
        self.data_dir = Path(data_dir)
        # 优先使用参数，否则从环境变量读取
        self.trace_enabled = trace_enabled if trace_enabled is not None else ENV_TRACE_ENABLED
        self.enable_verification = enable_verification
        self.verbose = ENV_VERBOSE
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化组件
        self._init_components()
        
        # 处理统计
        self.stats = {
            "total_files": 0,
            "total_reviews": 0,
            "processed_reviews": 0,
            "stored_records": 0,
            "failed_reviews": 0,
            "start_time": None,
            "end_time": None
        }
    
    def _load_config(self, config_path: Optional[str]) -> ConfigManager:
        """加载配置文件"""
        if config_path:
            config_file = config_path
        else:
            config_file = str(PROJECT_ROOT / "config" / "settings.yaml")
        
        return ConfigManager(config_file)
    
    def _init_components(self):
        """初始化处理组件"""
        # 创建 LLM Provider
        llm_config = self.config.get_llm_config('doubao')
        if not llm_config.api_key:
            raise RuntimeError("未找到豆包 API Key（请设置 ARK_API_KEY 或 DOBAO_API_KEY）")
        
        self.llm_provider = OpenAICompatibleProvider(
            model_name=llm_config.model_name,
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            timeout=llm_config.timeout,
            api_secret=getattr(llm_config, "api_secret", None)
        )
        self._verbose(f"LLM Provider initialized: {llm_config.model_name}")
        
        # 创建知识存储（支持 json, mem0, hybrid）
        store_config = {
            "base_dir": str(PROJECT_ROOT / "data" / "knowledge_store"),
            "json_base_dir": str(PROJECT_ROOT / "data" / "knowledge_store"),
            "llm_provider": "qwen",  # Mem0 使用通义千问
            # API Key 从环境变量自动获取
        }
        self.knowledge_store = create_knowledge_store(
            backend=self.storage_backend,
            config=store_config,
            verbose=self.verbose
        )
        self._verbose(f"Knowledge Store backend: {self.knowledge_store.backend_name}")
        self._verbose(f"Knowledge Store enabled: {self.knowledge_store.enabled}")
        
        # 创建数据工厂（不传递 vector_store，使用本地 JSON 存储）
        self.pipeline = DataFactoryPipeline(
            llm_provider=self.llm_provider,
            enable_verification=self.enable_verification,
            vector_store=None,  # 不使用 Mem0 VectorStore
            trace_backend=self.trace_enabled,
            trace_print=self._trace_print
        )
        self._verbose("DataFactoryPipeline initialized")
        
        self._trace("BackendProcessor initialized")
    
    def _trace_print(self, msg: str):
        """跟踪输出"""
        if self.trace_enabled:
            print(msg)
    
    def _trace(self, msg: str):
        """简化的跟踪输出"""
        if self.trace_enabled:
            print(f"[BACKEND_MAIN] {msg}")
    
    def _verbose(self, msg: str):
        """详细日志输出"""
        if self.verbose:
            print(f"[VERBOSE] {msg}")
    
    def load_data_files(self, limit: Optional[int] = None) -> List[Path]:
        """
        加载数据文件列表
        
        Args:
            limit: 最大文件数量限制
        
        Returns:
            数据文件路径列表
        """
        if not self.data_dir.exists():
            raise FileNotFoundError(f"数据目录不存在: {self.data_dir}")
        
        # 获取所有 JSON 文件
        files = sorted(self.data_dir.glob("*.json"))
        
        if limit and limit > 0:
            files = files[:limit]
        
        self.stats["total_files"] = len(files)
        self._trace(f"Found {len(files)} data files")
        
        return files
    
    def parse_data_file(self, file_path: Path) -> List[RawReview]:
        """
        解析单个数据文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            RawReview 列表
        """
        reviews = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 提取教授信息
            professor_info = data.get("input", {})
            sha1 = data.get("sha1", file_path.stem)
            
            # 处理评论列表
            review_list = data.get("data", {}).get("reviews", [])
            
            for review in review_list:
                content = review.get("description", "")
                if not content or not content.strip():
                    continue
                
                # 构建元数据
                source_metadata = {
                    "sha1": sha1,
                    "professor": professor_info.get("professor", ""),
                    "university": professor_info.get("university", ""),
                    "department": professor_info.get("department", ""),
                    "review_id": review.get("id", ""),
                    "academic_score": review.get("academic", 0),
                    "funding_score": review.get("researchFunding", 0),
                    "relationship_score": review.get("studentProfRelation", 0),
                    "salary_score": review.get("studentSalary", 0),
                    "worktime_score": review.get("workingTime", 0),
                    "job_score": review.get("jobPotential", 0),
                    "anonymous": review.get("anonymous", True)
                }
                
                # 获取时间戳
                created_at = review.get("created_at", "")
                try:
                    timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    timestamp = datetime.now()
                
                raw_review = RawReview(
                    content=content,
                    source_metadata=source_metadata,
                    timestamp=timestamp
                )
                reviews.append(raw_review)
            
            self._trace(f"Parsed {len(reviews)} reviews from {file_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            self._trace(f"[ERROR] Parse failed: {file_path.name} - {e}")
        
        return reviews
    
    async def process_reviews(
        self,
        reviews: List[RawReview],
        store_results: bool = True
    ) -> List[StructuredKnowledgeNode]:
        """
        处理评论列表
        
        Args:
            reviews: 评论列表
            store_results: 是否存储结果
        
        Returns:
            处理结果列表
        """
        results = []
        
        for i, review in enumerate(reviews, 1):
            try:
                self._trace(f"Processing review {i}/{len(reviews)}...")
                
                # 处理单条评论
                node = await self.pipeline.process_raw_review(review)
                results.append(node)
                self.stats["processed_reviews"] += 1
                
                # 存储到本地 JSON 存储
                if store_results and self.knowledge_store.enabled:
                    success = self._store_knowledge_node(node, review.source_metadata)
                    if success:
                        self.stats["stored_records"] += 1
                
                # 输出处理结果摘要
                self._trace(
                    f"  ✓ {node.mentor_id} | {node.dimension} | "
                    f"weight={node.weight_score:.2f} | "
                    f"fact={node.fact_content[:50]}..."
                )
                
            except Exception as e:
                logger.error(f"Failed to process review {i}: {e}")
                self._trace(f"  ✗ Error: {e}")
                self.stats["failed_reviews"] += 1
        
        return results
    
    def _store_knowledge_node(
        self,
        node: StructuredKnowledgeNode,
        source_metadata: Dict[str, Any]
    ) -> bool:
        """
        存储知识节点到本地 JSON 存储
        
        Args:
            node: 知识节点
            source_metadata: 来源元数据
        
        Returns:
            是否成功
        """
        # 构建存储内容
        content = (
            f"教授: {source_metadata.get('professor', 'Unknown')}\n"
            f"学校: {source_metadata.get('university', 'Unknown')}\n"
            f"院系: {source_metadata.get('department', 'Unknown')}\n"
            f"维度: {node.dimension}\n"
            f"内容: {node.fact_content}\n"
            f"权重: {node.weight_score:.2f}\n"
            f"标签: {', '.join(node.tags)}"
        )
        
        # 构建元数据
        metadata = {
            "mentor_id": node.mentor_id,
            "dimension": node.dimension,
            "weight_score": node.weight_score,
            "tags": node.tags,
            "original_nuance": node.original_nuance,
            "sha1": source_metadata.get("sha1", ""),
            "professor": source_metadata.get("professor", ""),
            "university": source_metadata.get("university", ""),
            "department": source_metadata.get("department", ""),
            "stored_at": datetime.now().isoformat()
        }
        
        # 使用 sha1 作为 user_id 分组存储
        user_id = source_metadata.get("sha1", "default")
        
        return self.knowledge_store.insert(
            content=content,
            user_id=user_id,
            metadata=metadata,
            kind="fact"
        )
    
    async def run_batch_process(
        self,
        limit: Optional[int] = None,
        store_results: bool = True
    ) -> Dict[str, Any]:
        """
        运行批量处理
        
        Args:
            limit: 最大文件数量限制
            store_results: 是否存储结果
        
        Returns:
            处理统计信息
        """
        self.stats["start_time"] = datetime.now()
        
        print("=" * 60)
        print("后端批量处理开始")
        print("=" * 60)
        
        # 1. 加载数据文件
        files = self.load_data_files(limit)
        print(f"\n📁 已加载 {len(files)} 个数据文件")
        
        # 2. 解析并处理每个文件
        all_nodes = []
        
        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] 处理文件: {file_path.name}")
            print("-" * 40)
            
            # 解析文件
            reviews = self.parse_data_file(file_path)
            self.stats["total_reviews"] += len(reviews)
            
            if not reviews:
                print("  ⚠️  没有评论数据")
                continue
            
            # 处理评论
            nodes = await self.process_reviews(reviews, store_results)
            all_nodes.extend(nodes)
        
        self.stats["end_time"] = datetime.now()
        
        # 3. 输出统计信息
        self._print_summary()
        
        return self.stats
    
    def _print_summary(self):
        """打印处理摘要"""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        print("\n" + "=" * 60)
        print("处理完成 - 统计信息")
        print("=" * 60)
        print(f"  📁 文件总数:     {self.stats['total_files']}")
        print(f"  📝 评论总数:     {self.stats['total_reviews']}")
        print(f"  ✅ 成功处理:     {self.stats['processed_reviews']}")
        print(f"  ❌ 处理失败:     {self.stats['failed_reviews']}")
        print(f"  💾 存储记录:     {self.stats['stored_records']}")
        print(f"  ⏱️  总耗时:       {duration:.2f}s")
        
        if self.stats["processed_reviews"] > 0:
            avg_time = duration / self.stats["processed_reviews"]
            print(f"  📊 平均耗时:     {avg_time:.2f}s/条")
        
        print("=" * 60)
    
    def show_stored_records(
        self,
        user_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        展示存储的记录
        
        Args:
            user_id: 用户ID过滤
            query: 搜索查询
            limit: 返回数量限制
        
        Returns:
            记录列表
        """
        if not self.knowledge_store.enabled:
            print("⚠️  知识存储未启用")
            return []
        
        print("\n" + "=" * 60)
        print("存储记录展示")
        print("=" * 60)
        
        # 先显示存储统计
        stats = self.knowledge_store.get_stats()
        print(f"📊 存储后端: {self.knowledge_store.backend_name}")
        print(f"📊 存储位置: {stats.get('storage_path', 'N/A')}")
        print(f"📊 总记录数: {stats.get('total_records', 0)}")
        
        if query:
            # 搜索模式
            print(f"\n🔍 搜索: '{query}'")
            records = self.knowledge_store.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
        else:
            # 获取所有记录
            print(f"\n📋 获取记录 (user_id={user_id or 'all'}, limit={limit})")
            records = self.knowledge_store.get_all(user_id=user_id, limit=limit)
        
        if not records:
            print("  没有找到记录")
            return []
        
        print(f"\n找到 {len(records)} 条记录:\n")
        
        for i, record in enumerate(records, 1):
            print(f"--- 记录 {i} ---")
            print(f"ID: {record.id or 'N/A'}")
            if record.created_at:
                print(f"创建时间: {record.created_at}")
            if record.score > 0:
                print(f"相关度: {record.score:.2f}")
            content_preview = record.content[:300] if len(record.content) > 300 else record.content
            print(f"内容:\n{content_preview}")
            if record.metadata:
                # 显示关键元数据
                meta = record.metadata
                print(f"  维度: {meta.get('dimension', 'N/A')}")
                print(f"  权重: {meta.get('weight_score', 'N/A')}")
                print(f"  教授: {meta.get('professor', 'N/A')}")
            print()
        
        print("=" * 60)
        
        return [record.to_dict() for record in records]


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="后端批量处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python backend_main.py process --limit 5          # 处理前5个文件（JSON存储）
  python backend_main.py process --limit 5 --store mem0   # 使用Mem0存储
  python backend_main.py process --limit 5 --store hybrid # 混合存储
  python backend_main.py process --trace            # 处理并输出跟踪信息
  python backend_main.py show --limit 10            # 展示10条存储记录
  python backend_main.py show --query "张老师"      # 搜索包含"张老师"的记录
  python backend_main.py stats                       # 查看存储统计
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # process 子命令
    process_parser = subparsers.add_parser("process", help="批量处理评论数据")
    process_parser.add_argument(
        "--limit", "-l", type=int, default=None,
        help="最大处理文件数量"
    )
    process_parser.add_argument(
        "--data-dir", "-d", type=str, 
        default=str(PROJECT_ROOT / "data" / "professors"),
        help="数据目录路径"
    )
    process_parser.add_argument(
        "--trace", "-t", action="store_true",
        help="启用跟踪输出"
    )
    process_parser.add_argument(
        "--no-store", action="store_true",
        help="不存储结果到数据库"
    )
    process_parser.add_argument(
        "--verify", action="store_true",
        help="启用核验循环"
    )
    process_parser.add_argument(
        "--store", "-s", type=str, default="json",
        choices=["json", "mem0", "hybrid"],
        help="存储后端: json(默认), mem0(向量), hybrid(混合)"
    )
    
    # show 子命令
    show_parser = subparsers.add_parser("show", help="展示存储的记录")
    show_parser.add_argument(
        "--limit", "-l", type=int, default=10,
        help="返回记录数量限制"
    )
    show_parser.add_argument(
        "--user-id", "-u", type=str, default=None,
        help="按用户ID过滤"
    )
    show_parser.add_argument(
        "--query", "-q", type=str, default=None,
        help="搜索查询"
    )
    show_parser.add_argument(
        "--data-dir", "-d", type=str,
        default=str(PROJECT_ROOT / "data" / "professors"),
        help="数据目录路径"
    )
    show_parser.add_argument(
        "--store", "-s", type=str, default="json",
        choices=["json", "mem0", "hybrid"],
        help="存储后端: json(默认), mem0(向量), hybrid(混合)"
    )
    
    # stats 子命令
    stats_parser = subparsers.add_parser("stats", help="查看存储统计")
    stats_parser.add_argument(
        "--data-dir", "-d", type=str,
        default=str(PROJECT_ROOT / "data" / "professors"),
        help="数据目录路径"
    )
    stats_parser.add_argument(
        "--store", "-s", type=str, default="json",
        choices=["json", "mem0", "hybrid"],
        help="存储后端: json(默认), mem0(向量), hybrid(混合)"
    )
    
    # 通用参数
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--config", "-c", type=str, default=None, help="配置文件路径")
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging(args.verbose)
    
    if not args.command:
        parser.print_help()
        return
    
    # 获取数据目录
    data_dir = getattr(args, "data_dir", str(PROJECT_ROOT / "data" / "professors"))
    
    # 获取存储后端
    storage_backend = getattr(args, "store", "json")
    
    # 确定 trace 状态：命令行 --trace 优先，否则使用环境变量
    trace_enabled = getattr(args, "trace", False) or ENV_TRACE_ENABLED
    
    # 创建处理器
    processor = BackendProcessor(
        data_dir=data_dir,
        config_path=args.config,
        trace_enabled=trace_enabled,
        enable_verification=getattr(args, "verify", False),
        storage_backend=storage_backend
    )
    
    # 执行命令
    if args.command == "process":
        asyncio.run(processor.run_batch_process(
            limit=args.limit,
            store_results=not args.no_store
        ))
    
    elif args.command == "show":
        processor.show_stored_records(
            user_id=args.user_id,
            query=args.query,
            limit=args.limit
        )
    
    elif args.command == "stats":
        # 流水线统计
        stats = processor.pipeline.get_statistics()
        print("\n" + "=" * 40)
        print("流水线统计信息")
        print("=" * 40)
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 存储统计
        store_stats = processor.knowledge_store.get_stats()
        print("\n" + "=" * 40)
        print("知识存储统计信息")
        print("=" * 40)
        print(f"  存储后端: {store_stats.get('backend', 'N/A')}")
        
        # 根据后端类型显示不同的统计
        if store_stats.get('backend') == 'hybrid(mem0+json)':
            # 混合存储
            json_stats = store_stats.get('json', {})
            mem0_stats = store_stats.get('mem0', {})
            
            print("\n  JSON 存储:")
            print(f"    存储路径: {json_stats.get('storage_path', 'N/A')}")
            print(f"    总记录数: {json_stats.get('total_records', 0)}")
            if json_stats.get('by_dimension'):
                print("    按维度统计:")
                for dim, count in json_stats['by_dimension'].items():
                    print(f"      {dim}: {count}")
            
            print("\n  Mem0 存储:")
            print(f"    存储路径: {mem0_stats.get('storage_path', 'N/A')}")
            print(f"    已启用: {mem0_stats.get('enabled', False)}")
        else:
            # 单一存储
            print(f"  存储路径: {store_stats.get('storage_path', 'N/A')}")
            print(f"  总记录数: {store_stats.get('total_records', 0)}")
            
            if store_stats.get('by_dimension'):
                print("\n  按维度统计:")
                for dim, count in store_stats['by_dimension'].items():
                    print(f"    {dim}: {count}")
            
            if store_stats.get('by_user'):
                print(f"\n  按用户/教授统计: {len(store_stats['by_user'])} 个分组")
        
        print("=" * 40)


if __name__ == "__main__":
    main()
