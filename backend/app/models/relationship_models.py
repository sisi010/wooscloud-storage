"""
Relationship Models
Data relationships with automatic population and cascade operations
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# ============================================================================
# Enums
# ============================================================================

class RelationType(str, Enum):
    """Relationship types"""
    ONE_TO_ONE = "one_to_one"      # 1:1
    ONE_TO_MANY = "one_to_many"    # 1:N
    MANY_TO_MANY = "many_to_many"  # N:N

class CascadeAction(str, Enum):
    """Cascade operation types"""
    NONE = "none"              # Do nothing
    SET_NULL = "set_null"      # Set reference to null
    DELETE = "delete"          # Delete related documents
    RESTRICT = "restrict"      # Prevent deletion if references exist

# ============================================================================
# Relationship Definition
# ============================================================================

class RelationshipDefinition(BaseModel):
    """Define a relationship between collections"""
    name: str = Field(min_length=1, max_length=100)
    from_collection: str = Field(min_length=1, max_length=100)
    to_collection: str = Field(min_length=1, max_length=100)
    relation_type: RelationType
    
    # Field names
    from_field: str = Field(min_length=1, max_length=100)  # Field in source
    to_field: str = Field(default="id", max_length=100)    # Field in target (usually "id")
    
    # Cascade options
    on_delete: CascadeAction = CascadeAction.SET_NULL
    on_update: CascadeAction = CascadeAction.NONE
    
    # Validation
    required: bool = False
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = []

class RelationshipCreate(BaseModel):
    """Create relationship request"""
    name: str = Field(min_length=1, max_length=100)
    from_collection: str = Field(min_length=1, max_length=100)
    to_collection: str = Field(min_length=1, max_length=100)
    relation_type: RelationType
    from_field: str = Field(min_length=1, max_length=100)
    to_field: str = Field(default="id", max_length=100)
    on_delete: CascadeAction = CascadeAction.SET_NULL
    on_update: CascadeAction = CascadeAction.NONE
    required: bool = False
    description: Optional[str] = None
    tags: List[str] = []

class RelationshipUpdate(BaseModel):
    """Update relationship request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    on_delete: Optional[CascadeAction] = None
    on_update: Optional[CascadeAction] = None
    required: Optional[bool] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class Relationship(BaseModel):
    """Relationship model"""
    id: str
    user_id: str
    name: str
    from_collection: str
    to_collection: str
    relation_type: RelationType
    from_field: str
    to_field: str
    on_delete: CascadeAction
    on_update: CascadeAction
    required: bool
    description: Optional[str] = None
    tags: List[str] = []
    created_at: str
    updated_at: str

class RelationshipListResponse(BaseModel):
    """List of relationships"""
    relationships: List[Relationship]
    total: int

# ============================================================================
# Populate Options
# ============================================================================

class PopulateOptions(BaseModel):
    """Options for populating references"""
    fields: List[str] = []  # Fields to populate
    depth: int = Field(default=1, ge=1, le=3)  # Max nesting depth
    select: Optional[List[str]] = None  # Fields to include from populated doc
    
    @validator("depth")
    def validate_depth(cls, v):
        """Limit populate depth to prevent infinite loops"""
        if v > 3:
            raise ValueError("Maximum populate depth is 3")
        return v

# ============================================================================
# Data with Relationships
# ============================================================================

class DataWithRelationships(BaseModel):
    """Data model with relationship support"""
    collection: str
    data: Dict[str, Any]
    populate: Optional[List[str]] = None  # Fields to auto-populate

class DataWithRelationshipsResponse(BaseModel):
    """Response with populated relationships"""
    id: str
    collection: str
    data: Dict[str, Any]
    populated_fields: List[str] = []
    created_at: str
    updated_at: str

# ============================================================================
# Cascade Operations
# ============================================================================

class CascadeResult(BaseModel):
    """Result of cascade operation"""
    action: CascadeAction
    affected_collections: List[str]
    affected_count: int
    details: Dict[str, Any] = {}

# ============================================================================
# Reference Validation
# ============================================================================

class ReferenceValidationResult(BaseModel):
    """Result of reference validation"""
    valid: bool
    field: str
    collection: str
    reference_id: Union[str, List[str]]
    exists: bool
    error_message: Optional[str] = None

class BulkReferenceValidation(BaseModel):
    """Bulk reference validation results"""
    total_checked: int
    valid_count: int
    invalid_count: int
    results: List[ReferenceValidationResult]

# ============================================================================
# Relationship Statistics
# ============================================================================

class RelationshipStats(BaseModel):
    """Relationship usage statistics"""
    relationship_id: str
    relationship_name: str
    from_collection: str
    to_collection: str
    total_references: int
    broken_references: int  # References to non-existent docs
    last_validated: Optional[str] = None

class RelationshipHealthStatus(BaseModel):
    """Overall relationship health"""
    total_relationships: int
    healthy_relationships: int
    relationships_with_broken_refs: int
    total_broken_references: int
    collections_with_relationships: List[str]

# ============================================================================
# Examples and Presets
# ============================================================================

class RelationshipExample(BaseModel):
    """Example relationship configurations"""
    name: str
    description: str
    example: RelationshipCreate

# Common relationship patterns
RELATIONSHIP_EXAMPLES = [
    RelationshipExample(
        name="User has Posts",
        description="One user can have many posts",
        example=RelationshipCreate(
            name="user_posts",
            from_collection="users",
            to_collection="posts",
            relation_type=RelationType.ONE_TO_MANY,
            from_field="posts",
            to_field="id",
            on_delete=CascadeAction.DELETE,
            description="User's blog posts"
        )
    ),
    RelationshipExample(
        name="Post belongs to User",
        description="Each post belongs to one user",
        example=RelationshipCreate(
            name="post_author",
            from_collection="posts",
            to_collection="users",
            relation_type=RelationType.ONE_TO_ONE,
            from_field="author_id",
            to_field="id",
            on_delete=CascadeAction.SET_NULL,
            required=True,
            description="Post author"
        )
    ),
    RelationshipExample(
        name="Post has Comments",
        description="One post can have many comments",
        example=RelationshipCreate(
            name="post_comments",
            from_collection="posts",
            to_collection="comments",
            relation_type=RelationType.ONE_TO_MANY,
            from_field="comments",
            to_field="id",
            on_delete=CascadeAction.DELETE,
            description="Post comments"
        )
    ),
    RelationshipExample(
        name="Users follow Users",
        description="Many-to-many relationship for followers",
        example=RelationshipCreate(
            name="user_followers",
            from_collection="users",
            to_collection="users",
            relation_type=RelationType.MANY_TO_MANY,
            from_field="followers",
            to_field="id",
            on_delete=CascadeAction.SET_NULL,
            description="User followers"
        )
    )
]

class RelationshipExamplesResponse(BaseModel):
    """List of relationship examples"""
    examples: List[RelationshipExample]