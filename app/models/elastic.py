from pydantic import BaseModel
from typing import List, Optional
from app.models.api import RecordInDb


class Shards(BaseModel):
    total: int
    successful: int
    skipped: int
    failed: int


class TotalHits(BaseModel):
    value: int
    relation: str


class Hit(BaseModel):
    index: str
    id: str
    score: Optional[float] = None
    source: RecordInDb


class Hits(BaseModel):
    total: TotalHits
    max_score: float
    hits: List[Hit]


class ElasticSearchResponse(BaseModel):
    took: int
    timed_out: bool
    shards: Shards
    hits: Hits
