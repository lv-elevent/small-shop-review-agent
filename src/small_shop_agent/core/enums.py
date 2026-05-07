from enum import Enum


class SourceType(str, Enum):
    CSV_UPLOAD = "csv_upload"
    DEMO_MODE = "demo_mode"


class BatchStatus(str, Enum):
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Topic(str, Enum):
    WAITING_TIME = "waiting_time"
    SERVICE = "service"
    PRODUCT = "product"
    PRICE = "price"
    ENVIRONMENT = "environment"
    HYGIENE = "hygiene"
    LOCATION = "location"
    OTHER = "other"


class SafetyStatus(str, Enum):
    PASS = "pass"
    REWRITE_REQUIRED = "rewrite_required"
    BLOCKED = "blocked"


class RiskType(str, Enum):
    OFFENSIVE = "offensive"
    FAKE_PROMISE = "fake_promise"
    PRIVACY_RISK = "privacy_risk"
    FABRICATED_FACT = "fabricated_fact"
    OVER_MARKETING = "over_marketing"
    UNCLEAR_RESPONSIBILITY = "unclear_responsibility"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class ApprovalAction(str, Enum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class TraceStatus(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    PENDING = "pending"


class TraceStep(str, Enum):
    INPUT_VALIDATION = "input_validation"
    DATA_CLEANING = "data_cleaning"
    CLASSIFICATION = "classification"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    ISSUE_AGGREGATION = "issue_aggregation"
    EVIDENCE_CHECK = "evidence_check"
    REPLY_DRAFTING = "reply_drafting"
    SAFETY_CHECK = "safety_check"
    HUMAN_APPROVAL = "human_approval"
    EVAL_RUN = "eval_run"