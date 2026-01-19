"""
数据加载模块
负责从data/professors目录读取JSON文件并转换为RawReview对象
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.schemas import RawReview

logger = logging.getLogger(__name__)


class ProfessorDataLoader:
    """
    导师评价数据加载器
    从data/professors/*.json文件中加载评论数据
    """
    
    def __init__(self, data_dir: str = "data/professors"):
        """
        初始化数据加载器
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        logger.info(f"ProfessorDataLoader initialized with directory: {self.data_dir}")
    
    def load_file(self, file_path: Path) -> List[RawReview]:
        """
        加载单个JSON文件并解析为RawReview列表
        
        Args:
            file_path: JSON文件路径
        
        Returns:
            List[RawReview]: 评论数据列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 提取基础元数据
            base_metadata = {
                "sha1": data.get("sha1", ""),
                "university": data.get("input", {}).get("university", ""),
                "department": data.get("input", {}).get("department", ""),
                "professor": data.get("input", {}).get("professor", ""),
                "source_file": file_path.name
            }
            
            # 解析reviews数组
            reviews = []
            review_data_list = data.get("data", {}).get("reviews", [])
            
            if not review_data_list:
                logger.debug(f"No reviews found in {file_path.name}")
                return reviews
            
            for review_item in review_data_list:
                # 提取评论内容
                description = review_item.get("description", "")
                if not description or not description.strip():
                    continue
                
                # 构建完整的元数据
                metadata = {
                    **base_metadata,
                    "review_id": review_item.get("id", ""),
                    "created_at": review_item.get("created_at", ""),
                    "anonymous": review_item.get("anonymous", True),
                    "platform": self._extract_platform(data),
                    # 评分字段（如果存在）
                    "studentProfRelation": review_item.get("studentProfRelation", 0),
                    "studentSalary": review_item.get("studentSalary", 0),
                    "jobPotential": review_item.get("jobPotential", 0),
                    "workingTime": review_item.get("workingTime", 0),
                    "researchFunding": review_item.get("researchFunding", 0),
                    "academic": review_item.get("academic", 0),
                }
                
                # 解析时间戳
                timestamp = self._parse_timestamp(review_item.get("created_at"))
                
                # 创建RawReview对象
                raw_review = RawReview(
                    content=description,
                    source_metadata=metadata,
                    timestamp=timestamp
                )
                
                reviews.append(raw_review)
            
            logger.debug(f"Loaded {len(reviews)} reviews from {file_path.name}")
            return reviews
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            return []
    
    def load_all(self, limit: Optional[int] = None) -> List[RawReview]:
        """
        加载所有JSON文件中的评论数据
        
        Args:
            limit: 限制加载的文件数量（用于测试）
        
        Returns:
            List[RawReview]: 所有评论数据列表
        """
        all_reviews = []
        json_files = sorted(self.data_dir.glob("*.json"))
        
        if limit:
            json_files = json_files[:limit]
        
        logger.info(f"Loading reviews from {len(json_files)} files...")
        
        for file_path in json_files:
            reviews = self.load_file(file_path)
            all_reviews.extend(reviews)
        
        logger.info(f"Loaded {len(all_reviews)} total reviews from {len(json_files)} files")
        return all_reviews
    
    def load_by_sha1(self, sha1: str) -> List[RawReview]:
        """
        根据SHA1加载特定导师的评论
        
        Args:
            sha1: 导师的SHA1标识
        
        Returns:
            List[RawReview]: 该导师的所有评论
        """
        file_path = self.data_dir / f"{sha1}.json"
        
        if not file_path.exists():
            logger.warning(f"File not found for SHA1: {sha1}")
            return []
        
        return self.load_file(file_path)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据集统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        json_files = list(self.data_dir.glob("*.json"))
        total_files = len(json_files)
        
        # 抽样统计（前100个文件）
        sample_files = json_files[:100]
        total_reviews = 0
        files_with_reviews = 0
        
        for file_path in sample_files:
            reviews = self.load_file(file_path)
            if reviews:
                files_with_reviews += 1
                total_reviews += len(reviews)
        
        avg_reviews_per_file = (
            total_reviews / files_with_reviews 
            if files_with_reviews > 0 
            else 0
        )
        
        return {
            "total_files": total_files,
            "sample_size": len(sample_files),
            "sample_reviews": total_reviews,
            "sample_files_with_reviews": files_with_reviews,
            "avg_reviews_per_file": avg_reviews_per_file,
            "estimated_total_reviews": int(total_files * avg_reviews_per_file)
        }
    
    @staticmethod
    def _parse_timestamp(timestamp_str: Optional[str]) -> datetime:
        """
        解析时间戳字符串
        
        Args:
            timestamp_str: 时间戳字符串
        
        Returns:
            datetime: 解析后的时间对象
        """
        if not timestamp_str:
            return datetime.now()
        
        try:
            # 尝试解析ISO格式时间戳 (e.g., "2022-05-25T08:15:36.721202")
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Failed to parse timestamp: {timestamp_str}, using current time")
            return datetime.now()
    
    @staticmethod
    def _extract_platform(data: Dict[str, Any]) -> str:
        """
        提取数据来源平台
        
        Args:
            data: JSON数据
        
        Returns:
            str: 平台名称
        """
        # 检查是否有source字段
        source = data.get("source", {})
        if isinstance(source, dict):
            base_url = source.get("baseUrl", "")
            if "realmofresearch" in base_url:
                return "realmofresearch"
        
        # 检查provenance字段
        provenance = data.get("provenance", {})
        if isinstance(provenance, dict):
            if provenance.get("excel", {}).get("sources"):
                return "excel"
        
        return "unknown"
