"""
Rate Limiting Guardrail - Prevents abuse and excessive usage.
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

from .schemas import (
    GuardrailResult, 
    GuardrailViolation, 
    GuardrailSeverity,
    GuardrailType,
    EducationalContext,
    GuardrailConfig
)

logger = logging.getLogger(__name__)


class RateLimitingGuardrail:
    """Rate limiting to prevent abuse and ensure fair usage."""
    
    def __init__(self, config: GuardrailConfig):
        """Initialize rate limiting guardrail."""
        self.config = config
        
        # In-memory storage for rate limiting (in production, use Redis or database)
        self.request_history: Dict[str, Dict[str, deque]] = defaultdict(lambda: {
            'minute': deque(),
            'hour': deque(), 
            'day': deque()
        })
        
        # Track consecutive violations
        self.violation_history: Dict[str, deque] = defaultdict(deque)
        
        logger.info("Rate limiting guardrail initialized")
    
    async def validate(self, user_input: str, context: EducationalContext) -> GuardrailResult:
        """
        Validate rate limiting for user request.
        
        Args:
            user_input: The user's input text
            context: Educational context including student_id
            
        Returns:
            GuardrailResult with rate limiting violations if any
        """
        if not self.config.enable_rate_limiting:
            return GuardrailResult(passed=True)
        
        violations = []
        metadata = {}
        
        # Use student_id or session_id as identifier
        user_id = context.student_id or context.session_id or "anonymous"
        current_time = datetime.now()
        
        # Clean old entries and get current counts
        usage_stats = self._get_usage_stats(user_id, current_time)
        metadata['usage_stats'] = usage_stats
        
        # Check rate limits
        rate_violations = self._check_rate_limits(user_id, usage_stats, current_time)
        violations.extend(rate_violations)
        
        # Record this request if not blocked
        if not any(v.severity in [GuardrailSeverity.BLOCK, GuardrailSeverity.CRITICAL] for v in violations):
            self._record_request(user_id, current_time)
        else:
            # Record violation for escalating penalties
            self._record_violation(user_id, current_time)
        
        return GuardrailResult(
            passed=len(violations) == 0,
            violations=violations,
            metadata=metadata
        )
    
    def _get_usage_stats(self, user_id: str, current_time: datetime) -> Dict[str, Any]:
        """Get current usage statistics for user."""
        # Clean old entries
        self._cleanup_old_entries(user_id, current_time)
        
        history = self.request_history[user_id]
        violations = len([v for v in self.violation_history[user_id] 
                         if current_time - v < timedelta(hours=1)])
        
        return {
            'requests_last_minute': len(history['minute']),
            'requests_last_hour': len(history['hour']),
            'requests_last_day': len(history['day']),
            'violations_last_hour': violations,
            'user_id': user_id
        }
    
    def _check_rate_limits(self, user_id: str, stats: Dict[str, Any], current_time: datetime) -> list:
        """Check if user has exceeded rate limits."""
        violations = []
        
        # Check minute limit
        if stats['requests_last_minute'] >= self.config.max_requests_per_minute:
            violations.append(GuardrailViolation(
                type=GuardrailType.RATE_LIMITING,
                severity=GuardrailSeverity.BLOCK,
                message=f"Límite de {self.config.max_requests_per_minute} consultas por minuto excedido",
                details={
                    'limit_type': 'per_minute',
                    'limit': self.config.max_requests_per_minute,
                    'current_count': stats['requests_last_minute'],
                    'reset_time': (current_time + timedelta(minutes=1)).isoformat()
                },
                user_id=user_id,
                session_id=user_id  # Using user_id as session fallback
            ))
        
        # Check hour limit
        elif stats['requests_last_hour'] >= self.config.max_requests_per_hour:
            violations.append(GuardrailViolation(
                type=GuardrailType.RATE_LIMITING,
                severity=GuardrailSeverity.BLOCK,
                message=f"Límite de {self.config.max_requests_per_hour} consultas por hora excedido",
                details={
                    'limit_type': 'per_hour',
                    'limit': self.config.max_requests_per_hour,
                    'current_count': stats['requests_last_hour'],
                    'reset_time': (current_time + timedelta(hours=1)).isoformat()
                },
                user_id=user_id,
                session_id=user_id
            ))
        
        # Check day limit
        elif stats['requests_last_day'] >= self.config.max_requests_per_day:
            violations.append(GuardrailViolation(
                type=GuardrailType.RATE_LIMITING,
                severity=GuardrailSeverity.BLOCK,
                message=f"Límite de {self.config.max_requests_per_day} consultas por día excedido",
                details={
                    'limit_type': 'per_day',
                    'limit': self.config.max_requests_per_day,
                    'current_count': stats['requests_last_day'],
                    'reset_time': (current_time + timedelta(days=1)).isoformat()
                },
                user_id=user_id,
                session_id=user_id
            ))
        
        # Check for repeated violations (escalating penalty)
        elif stats['violations_last_hour'] >= 3:
            violations.append(GuardrailViolation(
                type=GuardrailType.RATE_LIMITING,
                severity=GuardrailSeverity.CRITICAL,
                message="Múltiples violaciones de límites detectadas - penalización temporal",
                details={
                    'limit_type': 'violation_escalation',
                    'violations_count': stats['violations_last_hour'],
                    'penalty_duration_minutes': 30,
                    'reset_time': (current_time + timedelta(minutes=30)).isoformat()
                },
                user_id=user_id,
                session_id=user_id
            ))
        
        # Warning when approaching limits
        elif stats['requests_last_minute'] >= self.config.max_requests_per_minute * 0.8:
            violations.append(GuardrailViolation(
                type=GuardrailType.RATE_LIMITING,
                severity=GuardrailSeverity.WARNING,
                message=f"Te estás acercando al límite de consultas por minuto ({stats['requests_last_minute']}/{self.config.max_requests_per_minute})",
                details={
                    'limit_type': 'approaching_limit',
                    'current_count': stats['requests_last_minute'],
                    'limit': self.config.max_requests_per_minute,
                    'percentage': stats['requests_last_minute'] / self.config.max_requests_per_minute
                },
                user_id=user_id,
                session_id=user_id
            ))
        
        return violations
    
    def _record_request(self, user_id: str, timestamp: datetime):
        """Record a successful request."""
        history = self.request_history[user_id]
        
        # Add to all time windows
        history['minute'].append(timestamp)
        history['hour'].append(timestamp)
        history['day'].append(timestamp)
    
    def _record_violation(self, user_id: str, timestamp: datetime):
        """Record a rate limit violation."""
        self.violation_history[user_id].append(timestamp)
        
        # Keep only recent violations (last 24 hours)
        cutoff = timestamp - timedelta(hours=24)
        while (self.violation_history[user_id] and 
               self.violation_history[user_id][0] < cutoff):
            self.violation_history[user_id].popleft()
    
    def _cleanup_old_entries(self, user_id: str, current_time: datetime):
        """Remove old entries outside time windows."""
        history = self.request_history[user_id]
        
        # Clean minute window (keep last 60 seconds)
        minute_cutoff = current_time - timedelta(minutes=1)
        while history['minute'] and history['minute'][0] < minute_cutoff:
            history['minute'].popleft()
        
        # Clean hour window (keep last 60 minutes)
        hour_cutoff = current_time - timedelta(hours=1)
        while history['hour'] and history['hour'][0] < hour_cutoff:
            history['hour'].popleft()
        
        # Clean day window (keep last 24 hours)
        day_cutoff = current_time - timedelta(days=1)
        while history['day'] and history['day'][0] < day_cutoff:
            history['day'].popleft()
        
        # Clean violation history
        violation_cutoff = current_time - timedelta(hours=24)
        while (self.violation_history[user_id] and 
               self.violation_history[user_id][0] < violation_cutoff):
            self.violation_history[user_id].popleft()
    
    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """Get current rate limiting status for a user."""
        current_time = datetime.now()
        stats = self._get_usage_stats(user_id, current_time)
        
        # Calculate time until limits reset
        next_minute = current_time.replace(second=0, microsecond=0) + timedelta(minutes=1)
        next_hour = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        next_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        return {
            **stats,
            'limits': {
                'per_minute': self.config.max_requests_per_minute,
                'per_hour': self.config.max_requests_per_hour,
                'per_day': self.config.max_requests_per_day
            },
            'reset_times': {
                'minute': next_minute.isoformat(),
                'hour': next_hour.isoformat(),
                'day': next_day.isoformat()
            },
            'remaining': {
                'minute': max(0, self.config.max_requests_per_minute - stats['requests_last_minute']),
                'hour': max(0, self.config.max_requests_per_hour - stats['requests_last_hour']),
                'day': max(0, self.config.max_requests_per_day - stats['requests_last_day'])
            }
        }
    
    def reset_user_limits(self, user_id: str):
        """Reset rate limits for a user (admin function)."""
        if user_id in self.request_history:
            del self.request_history[user_id]
        if user_id in self.violation_history:
            del self.violation_history[user_id]
        logger.info(f"Rate limits reset for user: {user_id}")