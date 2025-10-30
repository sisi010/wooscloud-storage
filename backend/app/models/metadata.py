"""
Metadata model (for Phase 2+ - Multi-cloud tracking)
"""
from pydantic import BaseModel, Field
from datetime import datetime

class Metadata(BaseModel):
    """Metadata for tracking data location across multiple clouds"""
    id: str = Field(alias="_id")
    data_id: str  # ID of the actual data
    user_id: str
    provider: str  # "mongodb", "supabase", "firebase", etc.
    collection: str
    created_at: datetime
    
    class Config:
        populate_by_name = True