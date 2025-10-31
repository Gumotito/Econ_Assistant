"""
Analytics service for tracking query patterns and usage.
Helps identify popular queries, data gaps, and improvement opportunities.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


class Analytics:
    """Analytics service for Econ Assistant."""
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize analytics service.
        
        Args:
            log_dir: Directory for analytics logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.query_log = self.log_dir / "query_analytics.jsonl"
        self.tool_log = self.log_dir / "tool_usage.jsonl"
    
    def log_query(
        self,
        prompt: str,
        answer: str,
        tools_used: List[str],
        query_time: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Log a query for analysis.
        
        Args:
            prompt: User's question
            answer: Assistant's answer
            tools_used: List of tool names used
            query_time: Time taken in seconds
            success: Whether query succeeded
            error: Error message if failed
        """
        try:
            record = {
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt,
                "prompt_length": len(prompt),
                "answer_length": len(answer),
                "tools_used": tools_used,
                "num_tools": len(tools_used),
                "query_time_seconds": round(query_time, 3),
                "success": success,
                "error": error
            }
            
            with open(self.query_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging query: {e}")
    
    def log_tool_usage(
        self,
        tool_name: str,
        arguments: Dict,
        execution_time: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Log tool usage for analysis.
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            execution_time: Time taken in seconds
            success: Whether tool execution succeeded
            error: Error message if failed
        """
        try:
            record = {
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "arguments": arguments,
                "execution_time_seconds": round(execution_time, 3),
                "success": success,
                "error": error
            }
            
            with open(self.tool_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging tool usage: {e}")
    
    def get_popular_queries(self, limit: int = 10) -> List[Dict]:
        """
        Get most common query patterns.
        
        Args:
            limit: Number of top queries to return
            
        Returns:
            List of {query, count} dicts
        """
        if not self.query_log.exists():
            return []
        
        try:
            queries = []
            with open(self.query_log, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    # Normalize query (lowercase, strip)
                    normalized = record['prompt'].lower().strip()
                    queries.append(normalized)
            
            # Count occurrences
            counter = Counter(queries)
            
            return [
                {"query": query, "count": count}
                for query, count in counter.most_common(limit)
            ]
            
        except Exception as e:
            logger.error(f"Error analyzing popular queries: {e}")
            return []
    
    def get_tool_usage_stats(self) -> Dict:
        """
        Get tool usage statistics.
        
        Returns:
            Dict with tool usage counts and performance metrics
        """
        if not self.tool_log.exists():
            return {"total_calls": 0, "by_tool": {}}
        
        try:
            tool_counts = Counter()
            tool_times = defaultdict(list)
            tool_errors = Counter()
            
            with open(self.tool_log, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    tool = record['tool']
                    
                    tool_counts[tool] += 1
                    tool_times[tool].append(record['execution_time_seconds'])
                    
                    if not record['success']:
                        tool_errors[tool] += 1
            
            # Calculate averages
            stats = {
                "total_calls": sum(tool_counts.values()),
                "by_tool": {}
            }
            
            for tool, count in tool_counts.items():
                times = tool_times[tool]
                stats["by_tool"][tool] = {
                    "count": count,
                    "avg_time": round(sum(times) / len(times), 3),
                    "min_time": round(min(times), 3),
                    "max_time": round(max(times), 3),
                    "errors": tool_errors[tool]
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error analyzing tool usage: {e}")
            return {"total_calls": 0, "by_tool": {}}
    
    def identify_data_gaps(self, limit: int = 10) -> List[str]:
        """
        Identify queries that resulted in "no results" or errors.
        These indicate data gaps or missing capabilities.
        
        Args:
            limit: Number of gaps to return
            
        Returns:
            List of queries that failed or had no results
        """
        if not self.query_log.exists():
            return []
        
        try:
            gaps = []
            
            with open(self.query_log, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    answer = record.get('answer', '').lower()
                    
                    # Check for failure indicators
                    if (
                        not record['success'] or
                        'no results found' in answer or
                        'no matching information' in answer or
                        'could not find' in answer or
                        'error' in answer or
                        record.get('error')
                    ):
                        gaps.append(record['prompt'])
            
            # Return unique gaps
            return list(set(gaps))[:limit]
            
        except Exception as e:
            logger.error(f"Error identifying data gaps: {e}")
            return []
    
    def get_performance_summary(self) -> Dict:
        """
        Get overall performance summary.
        
        Returns:
            Dict with performance metrics
        """
        if not self.query_log.exists():
            return {
                "total_queries": 0,
                "avg_query_time": 0,
                "success_rate": 0,
                "avg_tools_per_query": 0
            }
        
        try:
            total = 0
            successes = 0
            total_time = 0
            total_tools = 0
            
            with open(self.query_log, "r", encoding="utf-8") as f:
                for line in f:
                    record = json.loads(line)
                    total += 1
                    
                    if record['success']:
                        successes += 1
                    
                    total_time += record['query_time_seconds']
                    total_tools += record['num_tools']
            
            return {
                "total_queries": total,
                "avg_query_time": round(total_time / total, 3) if total > 0 else 0,
                "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
                "avg_tools_per_query": round(total_tools / total, 1) if total > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance summary: {e}")
            return {
                "total_queries": 0,
                "avg_query_time": 0,
                "success_rate": 0,
                "avg_tools_per_query": 0
            }
    
    def get_recent_queries(self, limit: int = 10) -> List[Dict]:
        """
        Get most recent queries.
        
        Args:
            limit: Number of recent queries to return
            
        Returns:
            List of recent query records
        """
        if not self.query_log.exists():
            return []
        
        try:
            queries = []
            with open(self.query_log, "r", encoding="utf-8") as f:
                for line in f:
                    queries.append(json.loads(line))
            
            # Return last N queries (most recent)
            return queries[-limit:][::-1]  # Reverse to show newest first
            
        except Exception as e:
            logger.error(f"Error getting recent queries: {e}")
            return []


# Create singleton instance
_analytics_instance = None


def get_analytics() -> Analytics:
    """Get the analytics singleton."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = Analytics()
    return _analytics_instance
