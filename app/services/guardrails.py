"""
Guardrails Service for Econ Assistant
Provides content filtering, validation, and safety checks for inputs and outputs.
Adapted from AI_Project guardrails for Flask environment.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class GuardrailViolation(Exception):
    """Exception raised when content violates guardrails."""
    def __init__(self, message: str, violation_type: str):
        self.message = message
        self.violation_type = violation_type
        super().__init__(self.message)


class Guardrails:
    """Comprehensive guardrail system for economic assistant."""
    
    # Content filters - adapted for economic queries
    HARMFUL_PATTERNS = [
        r'\b(kill|murder|suicide|harm|attack|abuse)\s+(yourself|themselves|someone)\b',
        r'\b(how\s+to\s+)?(make|build|create)\s+(bomb|weapon|explosive|poison)\b',
        r'\b(hack|exploit|bypass|crack)\s+(system|password|security)\b',
        r'\b(steal|fraud|scam|phishing)\b.*\b(money|credit|bank|password)\b',
    ]
    
    # PII patterns to detect/redact
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
    }
    
    # Rate limiting storage (in-memory, per instance)
    _rate_limits: Dict[str, List[datetime]] = defaultdict(list)
    
    def __init__(
        self,
        max_length: int = 5000,
        min_length: int = 1,
        enable_content_filter: bool = True,
        enable_pii_detection: bool = True,
        enable_rate_limiting: bool = True,
        rate_limit_requests: int = 50,  # Lower for economics app
        rate_limit_window: int = 60
    ):
        """
        Initialize guardrails with configuration.
        
        Args:
            max_length: Maximum allowed content length
            min_length: Minimum required content length
            enable_content_filter: Enable harmful content detection
            enable_pii_detection: Enable PII detection
            enable_rate_limiting: Enable rate limiting
            rate_limit_requests: Max requests per window
            rate_limit_window: Time window in seconds
        """
        self.max_length = max_length
        self.min_length = min_length
        self.enable_content_filter = enable_content_filter
        self.enable_pii_detection = enable_pii_detection
        self.enable_rate_limiting = enable_rate_limiting
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_window = rate_limit_window
        
        # Compile patterns
        self._harmful_regex = [re.compile(p, re.IGNORECASE) for p in self.HARMFUL_PATTERNS]
        self._pii_regex = {k: re.compile(v) for k, v in self.PII_PATTERNS.items()}
    
    def validate_input(self, content: str, user_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate user input before processing.
        
        Args:
            content: Input content to validate
            user_id: Optional user identifier for rate limiting
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Empty/whitespace check
        if not content or not content.strip():
            return False, "Input cannot be empty"
        
        # Length check
        if len(content) < self.min_length:
            return False, f"Input too short (minimum {self.min_length} characters)"
        
        if len(content) > self.max_length:
            return False, f"Input too long (maximum {self.max_length} characters)"
        
        # Rate limiting
        if self.enable_rate_limiting and user_id:
            if not self._check_rate_limit(user_id):
                return False, "Rate limit exceeded. Please try again later."
        
        # Content filter
        if self.enable_content_filter:
            is_safe, violation = self._check_harmful_content(content)
            if not is_safe:
                logger.warning(f"Harmful content detected: {violation}")
                return False, "Your input contains potentially harmful content. Please rephrase."
        
        return True, None
    
    def validate_output(self, content: str, agent_name: str = "Econ Assistant") -> str:
        """
        Validate and sanitize output before returning to user.
        
        Args:
            content: Output content to validate
            agent_name: Name of the agent producing output
            
        Returns:
            Sanitized content
            
        Raises:
            GuardrailViolation: If content violates guardrails
        """
        if not content or not content.strip():
            raise GuardrailViolation("Agent produced empty output", "empty_output")
        
        # Length check
        if len(content) > self.max_length:
            logger.warning(f"{agent_name} output exceeds max length, truncating")
            content = content[:self.max_length - 3] + "..."
        
        # Content filter
        if self.enable_content_filter:
            is_safe, violation = self._check_harmful_content(content)
            if not is_safe:
                logger.error(f"{agent_name} produced harmful content: {violation}")
                raise GuardrailViolation(
                    f"Agent output contains inappropriate content: {violation}",
                    "harmful_content"
                )
        
        # PII detection (warn but don't block - economic data might contain legitimate business info)
        if self.enable_pii_detection:
            pii_found = self._detect_pii(content)
            if pii_found:
                logger.warning(f"{agent_name} output contains potential PII: {pii_found}")
        
        return content
    
    def sanitize_prompt(self, prompt: str) -> str:
        """
        Sanitize user prompt by removing/escaping potentially problematic characters.
        
        Args:
            prompt: Raw user prompt
            
        Returns:
            Sanitized prompt
        """
        # Remove excessive whitespace
        prompt = ' '.join(prompt.split())
        
        # Remove control characters
        prompt = ''.join(char for char in prompt if char.isprintable() or char.isspace())
        
        # Limit consecutive special characters
        prompt = re.sub(r'([!?.,;:]){4,}', r'\1\1\1', prompt)
        
        return prompt.strip()
    
    def _check_harmful_content(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        Check content for harmful patterns.
        
        Returns:
            Tuple of (is_safe, violation_description)
        """
        content_lower = content.lower()
        
        for pattern in self._harmful_regex:
            match = pattern.search(content_lower)
            if match:
                return False, f"Harmful pattern detected: {match.group(0)}"
        
        return True, None
    
    def _detect_pii(self, content: str) -> List[str]:
        """
        Detect potential PII in content.
        
        Returns:
            List of PII types detected
        """
        found = []
        for pii_type, pattern in self._pii_regex.items():
            if pattern.search(content):
                found.append(pii_type)
        return found
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if within limit, False if exceeded
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.rate_limit_window)
        
        # Clean old requests
        self._rate_limits[user_id] = [
            ts for ts in self._rate_limits[user_id]
            if ts > cutoff
        ]
        
        # Check limit
        if len(self._rate_limits[user_id]) >= self.rate_limit_requests:
            return False
        
        # Record this request
        self._rate_limits[user_id].append(now)
        return True
    
    def validate_followup(self, followup: str) -> Tuple[bool, Optional[str]]:
        """
        Specific validation for follow-up suggestions.
        
        Args:
            followup: Follow-up question text
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not followup or not followup.strip():
            return False, "Follow-up cannot be empty"
        
        # Length constraints (shorter than general content)
        if len(followup) > 200:
            return False, "Follow-up too long (max 200 characters)"
        
        if len(followup) < 10:
            return False, "Follow-up too short (min 10 characters)"
        
        # Must be a question (relaxed - can end with ? or be imperative)
        followup_clean = followup.strip()
        if not (followup_clean.endswith('?') or any(
            followup_clean.lower().startswith(q) 
            for q in ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'could', 'should', 'would', 'compare', 'analyze']
        )):
            logger.warning(f"Follow-up might not be a question: {followup}")
        
        return True, None


# Create singleton instance
_guardrails_instance = None


def get_guardrails() -> Guardrails:
    """Get the guardrails singleton."""
    global _guardrails_instance
    if _guardrails_instance is None:
        _guardrails_instance = Guardrails()
    return _guardrails_instance
