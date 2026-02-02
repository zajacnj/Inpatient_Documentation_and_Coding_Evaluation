"""
Audit Logger for Inpatient Documentation Evaluation

Comprehensive logging system for tracking all analysis attempts with full context:
- User actions
- Patient selections
- Document extraction
- AI analysis results
- Comparison results
- Export operations
- Performance metrics
- Timestamps

This creates a detailed audit trail for compliance and quality review.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class AuditLogger:
    """Comprehensive audit logger with full context capture."""

    def __init__(self, log_dir: str = "logs"):
        """
        Initialize audit logger.

        Args:
            log_dir: Directory for log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Main audit log file (JSON lines format for easy parsing)
        self.audit_log_file = self.log_dir / "audit_log.jsonl"

        # Human-readable summary log
        self.summary_log_file = self.log_dir / "audit_summary.log"

        # Analysis-specific log
        self.analysis_log_file = self.log_dir / "analysis_log.jsonl"

        # Current session ID
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        logger.info(f"Audit Logger initialized - Session: {self.session_id}")

    def log_event(
        self,
        event_type: str,
        username: str,
        details: Dict[str, Any],
        patient_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """
        Log a generic audit event.

        Args:
            event_type: Type of event (PATIENT_SELECTION, ANALYSIS_START, etc.)
            username: User who triggered the event
            details: Event-specific details
            patient_id: Patient identifier (if applicable)
            success: Whether the event was successful
            error_message: Error message if failed

        Returns:
            Event ID for this log entry
        """
        event_id = f"{self.session_id}_{datetime.now().strftime('%H%M%S_%f')}"
        timestamp = datetime.now().isoformat()

        log_entry = {
            'event_id': event_id,
            'timestamp': timestamp,
            'session_id': self.session_id,
            'event_type': event_type,
            'username': username,
            'patient_id': patient_id,
            'success': success,
            'error_message': error_message,
            'details': details
        }

        # Write to audit log
        try:
            with open(self.audit_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write to audit log: {e}")

        return event_id

    def log_patient_selection(
        self,
        username: str,
        patient_id: str,
        patient_name: str,
        admission_date: str,
        discharge_date: str
    ) -> str:
        """Log when a user selects a patient for review."""
        return self.log_event(
            event_type='PATIENT_SELECTION',
            username=username,
            patient_id=patient_id,
            details={
                'patient_name': patient_name,
                'admission_date': admission_date,
                'discharge_date': discharge_date
            }
        )

    def log_document_extraction(
        self,
        username: str,
        patient_id: str,
        document_types: List[str],
        document_count: int,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        """Log document extraction operations."""
        return self.log_event(
            event_type='DOCUMENT_EXTRACTION',
            username=username,
            patient_id=patient_id,
            success=success,
            error_message=error,
            details={
                'document_types': document_types,
                'document_count': document_count
            }
        )

    def log_analysis_start(
        self,
        username: str,
        patient_id: str,
        analysis_type: str,
        document_count: int
    ) -> str:
        """Log when AI analysis begins."""
        return self.log_event(
            event_type='ANALYSIS_START',
            username=username,
            patient_id=patient_id,
            details={
                'analysis_type': analysis_type,
                'document_count': document_count
            }
        )

    def log_analysis_complete(
        self,
        username: str,
        patient_id: str,
        analysis_id: str,
        diagnoses_found: int,
        processing_time_seconds: float,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        """Log when AI analysis completes."""
        return self.log_event(
            event_type='ANALYSIS_COMPLETE',
            username=username,
            patient_id=patient_id,
            success=success,
            error_message=error,
            details={
                'analysis_id': analysis_id,
                'diagnoses_found': diagnoses_found,
                'processing_time_seconds': processing_time_seconds
            }
        )

    def log_comparison_result(
        self,
        username: str,
        patient_id: str,
        documented_diagnoses: int,
        coded_diagnoses: int,
        matches: int,
        discrepancies: int
    ) -> str:
        """Log diagnosis comparison results."""
        return self.log_event(
            event_type='COMPARISON_RESULT',
            username=username,
            patient_id=patient_id,
            details={
                'documented_diagnoses': documented_diagnoses,
                'coded_diagnoses': coded_diagnoses,
                'matches': matches,
                'discrepancies': discrepancies,
                'match_rate': round(matches / max(documented_diagnoses, 1) * 100, 1)
            }
        )

    def log_export(
        self,
        username: str,
        patient_id: str,
        export_format: str,
        file_path: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> str:
        """Log export operations."""
        return self.log_event(
            event_type='EXPORT',
            username=username,
            patient_id=patient_id,
            success=success,
            error_message=error,
            details={
                'format': export_format,
                'file_path': file_path
            }
        )

    def log_analysis_details(
        self,
        analysis_id: str,
        patient_id: str,
        username: str,
        notes_analyzed: List[Dict],
        ai_diagnoses: List[Dict],
        coded_diagnoses: List[Dict],
        comparison: Dict,
        total_time_seconds: float
    ) -> None:
        """
        Log detailed analysis results for later review.

        Args:
            analysis_id: Unique identifier for this analysis
            patient_id: Patient identifier
            username: User who ran the analysis
            notes_analyzed: List of notes that were analyzed
            ai_diagnoses: Diagnoses extracted by AI
            coded_diagnoses: Actual coded diagnoses from PTF
            comparison: Comparison results
            total_time_seconds: Total processing time
        """
        log_entry = {
            'analysis_id': analysis_id,
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'patient_id': patient_id,
            'username': username,
            'notes_analyzed': [
                {
                    'type': n.get('type'),
                    'date': n.get('date'),
                    'author': n.get('author')
                } for n in notes_analyzed
            ],
            'ai_diagnoses_count': len(ai_diagnoses),
            'ai_diagnoses': ai_diagnoses,
            'coded_diagnoses_count': len(coded_diagnoses),
            'coded_diagnoses': coded_diagnoses,
            'comparison_summary': {
                'matches': comparison.get('matches', []),
                'documented_not_coded': comparison.get('documented_not_coded', []),
                'coded_not_documented': comparison.get('coded_not_documented', [])
            },
            'total_time_seconds': total_time_seconds
        }

        try:
            with open(self.analysis_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write analysis details: {e}")

    def get_recent_events(self, count: int = 50, event_type: Optional[str] = None) -> List[Dict]:
        """
        Get recent audit events.

        Args:
            count: Number of recent events to retrieve
            event_type: Optional filter by event type

        Returns:
            List of audit log entries
        """
        events = []

        try:
            if self.audit_log_file.exists():
                with open(self.audit_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if event_type is None or entry.get('event_type') == event_type:
                                events.append(entry)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Error reading audit log: {e}")

        return events[-count:] if len(events) > count else events

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit statistics.

        Returns:
            Dictionary with event counts and statistics
        """
        stats = {
            'total_events': 0,
            'successful': 0,
            'failed': 0,
            'event_types': {},
            'users': {},
            'patients_reviewed': set()
        }

        try:
            if self.audit_log_file.exists():
                with open(self.audit_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            stats['total_events'] += 1

                            if entry.get('success'):
                                stats['successful'] += 1
                            else:
                                stats['failed'] += 1

                            event_type = entry.get('event_type', 'UNKNOWN')
                            stats['event_types'][event_type] = stats['event_types'].get(event_type, 0) + 1

                            username = entry.get('username', 'UNKNOWN')
                            stats['users'][username] = stats['users'].get(username, 0) + 1

                            if entry.get('patient_id'):
                                stats['patients_reviewed'].add(entry['patient_id'])

                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")

        stats['patients_reviewed'] = len(stats['patients_reviewed'])
        return stats

    def export_session_report(self, output_file: Optional[str] = None) -> str:
        """
        Export a detailed report for the current session.

        Args:
            output_file: Optional custom output file path

        Returns:
            Path to generated report
        """
        if output_file is None:
            output_file = str(self.log_dir / f"session_report_{self.session_id}.json")

        stats = self.get_statistics()
        recent_events = self.get_recent_events(100)

        report = {
            'session_id': self.session_id,
            'generated_at': datetime.now().isoformat(),
            'statistics': stats,
            'recent_events': recent_events
        }

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Session report exported: {output_file}")
        except Exception as e:
            logger.error(f"Failed to export report: {e}")

        return output_file
