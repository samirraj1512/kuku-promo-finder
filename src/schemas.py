"""Pydantic schemas for judge output (plan 7.3) + pairwise + cold-viewer. Same schema whether the judge is an API model or a human-in-loop file."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

HookType = Literal["status_reversal", "impossible_situation", "hidden_identity", "ticking_clock", "shocking_revelation",
                   "public_humiliation", "confrontation", "betrayal", "other"]
CliffType = Literal["danger", "revelation", "decision", "mystery", "betrayal", "ticking_clock", "unresolved_confrontation", "none"]


class Hook(BaseModel):
    score: int = Field(ge=1, le=5); type: HookType; evidence_ids: list[str] = []


class Cliff(BaseModel):
    score: int = Field(ge=1, le=5); type: CliffType; evidence_ids: list[str] = []; unanswered_question: str = ""


class Clarity(BaseModel):
    score: int = Field(ge=1, le=5); confusions: list[str] = []


class Flags(BaseModel):
    resolved_in_clip: bool = False; needs_prior_context: bool = False
    spoiler_risk: Literal["none", "low", "high"] = "none"; policy_risk: Literal["none", "low", "medium", "high"] = "none"


class Pointwise(BaseModel):
    reasoning: str = ""; hook: Hook; cliffhanger: Cliff; clarity: Clarity; intensity: int = Field(ge=1, le=5)
    flags: Flags = Flags(); why_it_works: str = ""


class Cold(BaseModel):
    """Cold-viewer pass: judge sees ONLY clip text, no show context."""
    who_is_in_conflict: str = ""; why: str = ""; open_question: str = ""
    passes: bool = False; confusions: list[str] = []


class Judgment(Pointwise):
    cold: Cold = Cold(); hook_text: str = ""; cliff_text: str = ""


class PairResult(BaseModel):
    a: str; b: str; winner_a_first: str; winner_b_first: str   # winner when a shown first / when b shown first
