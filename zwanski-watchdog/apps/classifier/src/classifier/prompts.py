"""LLM prompt templates for OpenRouter."""

from .schemas import RawFinding

SYSTEM_PROMPT = """You are a security analyst for Zwanski Watchdog. Classify public leak hints.
Never reproduce secret values—describe categories only. Respond ONLY with minified JSON matching the schema:
finding_id, is_real_leak, confidence (0-1), leak_type (enum), severity_score (0-10), severity_reasoning,
affected_entity, affected_entity_confidence, recommended_action (enum), pii_detected, pii_types (list),
ai_content_detected, classified_at (ISO8601), model_used, tokens_used (estimate 0 if unknown).

Severity rubric:
- 9-10: production creds, live private keys in sensitive sectors, >10k PII records
- 7-8.9: powerful API keys, infra configs, <10k PII
- 5-6.9: read-only creds, stale tokens, low-sensitivity configs
- 3-4.9: hashed/obfuscated, staging/test
- 1-2.9: likely test data
- 0-0.9: false positive
"""

USER_PROMPT_TEMPLATE = """Classify this finding. Do NOT repeat credential contents; describe type only.

source={source}
module={module}
url={url}
metadata={metadata}
content_excerpt (truncated):
{excerpt}
"""


def build_user_prompt(finding: RawFinding) -> str:
    """Format the user message for the classifier model."""
    excerpt = finding.raw_content[:2000]
    return USER_PROMPT_TEMPLATE.format(
        source=finding.source,
        module=finding.module_name,
        url=finding.url,
        metadata=finding.metadata,
        excerpt=excerpt,
    )
