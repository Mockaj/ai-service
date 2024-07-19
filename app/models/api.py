from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
from typing import List, Literal, Optional, Union, Any
from fastapi import HTTPException


class StatusEnum(str, Enum):
    ACTIVE = '1'
    INACTIVE = '0'


class Record(BaseModel):
    id: str = Field(..., min_length=1, description="ID must not be empty")

    @field_validator('id')
    def check_id(cls, value: str):
        if " " in value:
            raise ValueError("ID must not include whitespaces.")
        return value


class RecordCreateReplace(Record):
    method: Literal['POST', 'PUT']
    name: str
    description: Optional[str] = None
    status: Optional[StatusEnum] = None


class RecordPatch(Record):
    method: Literal['PATCH']
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class RecordDelete(Record):
    method: Literal['DELETE']


class RecordInDb(Record):
    name: str
    description: Optional[str] = None
    status: Optional[StatusEnum] = None


class SimilarRecord(RecordInDb):
    score: float


class SyncRecord(BaseModel):
    data: Union[RecordCreateReplace, RecordPatch, RecordDelete] = Field(discriminator='method')

    @model_validator(mode='before')
    def check_record_completeness(cls, values: Any):
        data = values.get('data')
        method = data.get('method')

        if method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            raise ValidationError("Method must be one of 'POST', 'PUT', 'PATCH', 'DELETE")

        if method == 'DELETE':
            if len(data.keys()) > 2:
                raise ValidationError(
                    "For DELETE, only 'id' and 'method' should be provided, no other fields are allowed.")

        elif method == 'PATCH':
            if len(data.keys()) < 2:
                raise ValidationError("For PATCH, at least one field other than 'id' and 'method' must be provided.")

        if method in ['POST', 'PUT']:
            if not isinstance(values, dict):
                raise ValidationError(f"For method {method}, data must be of type RecordCreateReplace")
        return values


class SyncRecordsPayload(BaseModel):
    payload: List[SyncRecord]


class GetCollectionsResponse(BaseModel):
    collections: List[str]


class ErrorResponse(BaseModel):
    error: str
    code: int


class ValidationError(HTTPException):
    def __init__(self, detail: str, status_code: int = 422):
        super().__init__(status_code=status_code, detail="Validation error: " + detail)


class SimilarRecordsQuery(BaseModel):
    query: List[str]


class SimilarRecordsResponse(BaseModel):
    data: List[SimilarRecord]
