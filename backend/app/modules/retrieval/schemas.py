from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.retrieval.models import VectorSearchResult


class VectorSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class MatchedChildResponse(BaseModel):
    child_id: UUID
    ordinal: int
    preview: str
    start_offset: int
    end_offset: int
    score: float


class ParentSearchMatchResponse(BaseModel):
    parent_id: UUID
    document_id: UUID
    heading_path: str
    content: str
    score: float
    matched_children: list[MatchedChildResponse]


class VectorSearchResponse(BaseModel):
    query: str
    embedding_model: str
    matches: list[ParentSearchMatchResponse]

    @classmethod
    def from_result(cls, result: VectorSearchResult) -> "VectorSearchResponse":
        return cls(
            query=result.query,
            embedding_model=result.embedding_model,
            matches=[
                ParentSearchMatchResponse(
                    parent_id=match.parent_id,
                    document_id=match.document_id,
                    heading_path=match.heading_path,
                    content=match.content,
                    score=match.score,
                    matched_children=[
                        MatchedChildResponse(
                            child_id=child.child_id,
                            ordinal=child.ordinal,
                            preview=child.preview,
                            start_offset=child.start_offset,
                            end_offset=child.end_offset,
                            score=child.score,
                        )
                        for child in match.matched_children
                    ],
                )
                for match in result.matches
            ],
        )
