"""
Query Logger for Inpatient Documentation and Coding Evaluation

Tracks all database queries, parameters, results, and AI evaluation steps.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class QueryLogger:
    """Comprehensive query and evaluation logger."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup file handler for query logs
        self.query_log_file = self.log_dir / f"queries_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self.eval_log_file = self.log_dir / f"evaluations_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        # Setup Python logger
        self.logger = logging.getLogger("QueryLogger")
        self.logger.setLevel(logging.INFO)

    def log_query(
        self,
        query_type: str,
        username: str,
        sql_query: str,
        parameters: Dict[str, Any],
        success: bool,
        results: Optional[Any] = None,
        error: Optional[str] = None,
        row_count: int = 0,
        execution_time_ms: float = 0
    ):
        """Log a database query with full details."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query_type": query_type,
            "username": username,
            "sql_query": sql_query,
            "parameters": parameters,
            "success": success,
            "row_count": row_count,
            "execution_time_ms": round(execution_time_ms, 2),
            "error": error,
            "results_sample": results[:3] if results and isinstance(results, list) else None
        }

        # Write to JSONL file
        with open(self.query_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, default=str) + '\n')

        # Also log to Python logger
        if success:
            self.logger.info(f"{query_type}: {row_count} rows in {execution_time_ms:.2f}ms")
        else:
            self.logger.error(f"{query_type} FAILED: {error}")

        return log_entry

    def log_evaluation_step(
        self,
        evaluation_id: str,
        patient_id: str,
        username: str,
        step_name: str,
        step_type: str,
        success: bool,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time_ms: float = 0
    ):
        """Log an AI evaluation step."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "evaluation_id": evaluation_id,
            "patient_id": patient_id,
            "username": username,
            "step_name": step_name,
            "step_type": step_type,
            "success": success,
            "execution_time_ms": round(execution_time_ms, 2),
            "input_summary": self._summarize_data(input_data),
            "output_summary": self._summarize_data(output_data),
            "error": error
        }

        # Write to JSONL file
        with open(self.eval_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, default=str) + '\n')

        # Also log to Python logger
        if success:
            self.logger.info(f"Eval {evaluation_id} - {step_name}: SUCCESS in {execution_time_ms:.2f}ms")
        else:
            self.logger.error(f"Eval {evaluation_id} - {step_name}: FAILED - {error}")

        return log_entry

    def _summarize_data(self, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Create a summary of data for logging."""
        if not data:
            return None

        summary = {}
        for key, value in data.items():
            if isinstance(value, list):
                summary[key] = f"List[{len(value)} items]"
            elif isinstance(value, dict):
                summary[key] = f"Dict[{len(value)} keys]"
            elif isinstance(value, str) and len(value) > 100:
                summary[key] = value[:100] + "..."
            else:
                summary[key] = value

        return summary

    def get_recent_queries(self, count: int = 20, query_type: Optional[str] = None) -> List[Dict]:
        """Get recent query logs."""
        if not self.query_log_file.exists():
            return []

        logs = []
        with open(self.query_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log = json.loads(line)
                    if query_type is None or log.get("query_type") == query_type:
                        logs.append(log)
                except json.JSONDecodeError:
                    continue

        return logs[-count:]

    def get_evaluation_log(self, evaluation_id: str) -> List[Dict]:
        """Get all steps for a specific evaluation."""
        if not self.eval_log_file.exists():
            return []

        logs = []
        with open(self.eval_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log = json.loads(line)
                    if log.get("evaluation_id") == evaluation_id:
                        logs.append(log)
                except json.JSONDecodeError:
                    continue

        return logs

    def get_failed_queries(self, hours: int = 24) -> List[Dict]:
        """Get failed queries from the last N hours."""
        if not self.query_log_file.exists():
            return []

        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=hours)

        failed = []
        with open(self.query_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log = json.loads(line)
                    log_time = datetime.fromisoformat(log["timestamp"])
                    if not log.get("success") and log_time > cutoff:
                        failed.append(log)
                except (json.JSONDecodeError, KeyError):
                    continue

        return failed

    def get_query_statistics(self) -> Dict[str, Any]:
        """Get statistics about queries."""
        if not self.query_log_file.exists():
            return {"total_queries": 0}

        total = 0
        successful = 0
        failed = 0
        total_time = 0
        total_rows = 0
        by_type = {}

        with open(self.query_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    log = json.loads(line)
                    total += 1
                    if log.get("success"):
                        successful += 1
                        total_rows += log.get("row_count", 0)
                    else:
                        failed += 1
                    total_time += log.get("execution_time_ms", 0)

                    qtype = log.get("query_type", "unknown")
                    by_type[qtype] = by_type.get(qtype, 0) + 1
                except json.JSONDecodeError:
                    continue

        return {
            "total_queries": total,
            "successful": successful,
            "failed": failed,
            "total_rows_returned": total_rows,
            "avg_execution_time_ms": round(total_time / total, 2) if total > 0 else 0,
            "queries_by_type": by_type
        }
