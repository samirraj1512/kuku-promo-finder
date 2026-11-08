from typing import Literal
from pydantic import BaseModel, Field
from src.llm_client import LLMClient


class Sub(BaseModel):
    score: int = Field(ge=1, le=5)
    type: Literal["a", "b"]
    evidence_ids: list[str]


class Out(BaseModel):
    reasoning: str
    hook: Sub
    flag: bool


def test_stub_returns_valid_and_caches(tmp_path):
    c = LLMClient({"provider": "stub"}, cache_dir=str(tmp_path), usage_path=str(tmp_path / "u.csv"))
    r1 = c.complete("sys", "user", Out, stage="t")
    r2 = c.complete("sys", "user", Out, stage="t")
    assert isinstance(r1, Out) and 1 <= r1.hook.score <= 5
    assert c.cache_hits == 1 and r1 == r2
    assert c.pin("s", "u")["prompt_hash"]
