from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Transaction Schemas ---
class TransactionBase(BaseModel):
    ref_number: str
    user_id: str
    amount: float
    type: str # DEPOSIT, WITHDRAWAL
    status: str # SUCCESS, FAILED, PENDING

class TransactionCreate(TransactionBase):
    platform_name: str
    method_name: str

class TransactionResponse(TransactionBase):
    id: int
    platform_id: int
    method_id: int
    is_anomalous: bool
    datetime: datetime
    platform_name: Optional[str] = None
    method_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Platform Schemas ---
class PlatformBase(BaseModel):
    name: str
    url: str
    description: Optional[str] = None

class PlatformCreate(PlatformBase):
    pass

class PlatformResponse(PlatformBase):
    id: int
    trust_score: float
    risk_score: float
    created_at: datetime

    class Config:
        from_attributes = True

# --- RAG Request / Response Schemas ---
class RAGQueryRequest(BaseModel):
    query: str

class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    retrieved_context: List[dict]

# --- Anomaly Prediction Sandbox Schemas ---
class AnomalyPredictRequest(BaseModel):
    amount: float
    type: str
    status: str

class AnomalyPredictResponse(BaseModel):
    amount: float
    type: str
    status: str
    is_anomalous: bool
    message: str
