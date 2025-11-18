"""
Team Collaboration Models
Advanced team collaboration with RBAC and activity logging
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================================================
# Enums
# ============================================================================

class MemberRole(str, Enum):
    """Member roles with hierarchical permissions"""
    OWNER = "owner"        # Full control, can delete organization
    ADMIN = "admin"        # Team management, member management
    MEMBER = "member"      # Read/write team data
    VIEWER = "viewer"      # Read-only access

class InvitationStatus(str, Enum):
    """Invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"

class ActivityType(str, Enum):
    """Activity types for audit log"""
    # Organization
    ORG_CREATED = "org.created"
    ORG_UPDATED = "org.updated"
    ORG_DELETED = "org.deleted"
    
    # Team
    TEAM_CREATED = "team.created"
    TEAM_UPDATED = "team.updated"
    TEAM_DELETED = "team.deleted"
    
    # Member
    MEMBER_INVITED = "member.invited"
    MEMBER_JOINED = "member.joined"
    MEMBER_LEFT = "member.left"
    MEMBER_REMOVED = "member.removed"
    MEMBER_ROLE_CHANGED = "member.role_changed"
    
    # Data
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    DATA_SHARED = "data.shared"
    
    # Access
    ACCESS_GRANTED = "access.granted"
    ACCESS_REVOKED = "access.revoked"

# ============================================================================
# Permission Constants
# ============================================================================

ROLE_PERMISSIONS = {
    MemberRole.OWNER: [
        "org.*",           # All org operations
        "team.*",          # All team operations
        "member.*",        # All member operations
        "data.*",          # All data operations
    ],
    MemberRole.ADMIN: [
        "team.read",
        "team.update",
        "team.create",
        "member.read",
        "member.invite",
        "member.remove",
        "member.update_role",
        "data.*",
    ],
    MemberRole.MEMBER: [
        "team.read",
        "member.read",
        "data.read",
        "data.create",
        "data.update",
        "data.delete",
    ],
    MemberRole.VIEWER: [
        "team.read",
        "member.read",
        "data.read",
    ]
}

# ============================================================================
# Organization Models
# ============================================================================

class OrganizationCreate(BaseModel):
    """Create organization request"""
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[Dict[str, Any]] = None

class OrganizationUpdate(BaseModel):
    """Update organization request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class Organization(BaseModel):
    """Organization model"""
    id: str
    name: str
    description: Optional[str] = None
    owner_id: str
    settings: Dict[str, Any] = {}
    member_count: int = 0
    team_count: int = 0
    created_at: str
    updated_at: str

# ============================================================================
# Team Models
# ============================================================================

class TeamCreate(BaseModel):
    """Create team request"""
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    organization_id: str

class TeamUpdate(BaseModel):
    """Update team request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class Team(BaseModel):
    """Team model"""
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    member_count: int = 0
    created_by: str
    created_at: str
    updated_at: str

# ============================================================================
# Member Models
# ============================================================================

class MemberInvite(BaseModel):
    """Invite member request"""
    email: Optional[EmailStr] = None
    user_id: Optional[str] = None
    role: MemberRole = MemberRole.MEMBER
    team_id: Optional[str] = None  # If None, org-level member

class MemberUpdate(BaseModel):
    """Update member request"""
    role: MemberRole

class Member(BaseModel):
    """Team/Organization member"""
    id: str
    organization_id: str
    team_id: Optional[str] = None  # None = org-level member
    user_id: str
    email: Optional[str] = None
    role: MemberRole
    invited_by: str
    joined_at: str
    updated_at: str

class Invitation(BaseModel):
    """Invitation model"""
    id: str
    organization_id: str
    team_id: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[str] = None
    role: MemberRole
    status: InvitationStatus
    invited_by: str
    invitation_code: str
    expires_at: str
    created_at: str
    accepted_at: Optional[str] = None

# ============================================================================
# Activity Log Models
# ============================================================================

class Activity(BaseModel):
    """Activity log entry"""
    id: str
    organization_id: str
    team_id: Optional[str] = None
    user_id: str
    user_email: Optional[str] = None
    activity_type: ActivityType
    resource_type: str  # "organization", "team", "member", "data"
    resource_id: str
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: str

class ActivityLogResponse(BaseModel):
    """Activity log response"""
    activities: List[Activity]
    total: int
    page: int
    page_size: int

# ============================================================================
# List Responses
# ============================================================================

class OrganizationListResponse(BaseModel):
    """List of organizations"""
    organizations: List[Organization]
    total: int

class TeamListResponse(BaseModel):
    """List of teams"""
    teams: List[Team]
    total: int

class MemberListResponse(BaseModel):
    """List of members"""
    members: List[Member]
    total: int

class InvitationListResponse(BaseModel):
    """List of invitations"""
    invitations: List[Invitation]
    total: int

# ============================================================================
# Team Data Models
# ============================================================================

class TeamDataPermission(BaseModel):
    """Data sharing permissions"""
    collection: str
    team_id: str
    role_required: MemberRole  # Minimum role required
    permissions: List[str]  # ["read", "write", "delete"]

class SharedDataInfo(BaseModel):
    """Shared data information"""
    data_id: str
    collection: str
    owner_id: str
    shared_with_teams: List[str]
    shared_at: str
    permissions: Dict[str, List[str]]  # team_id -> permissions

# ============================================================================
# Statistics Models
# ============================================================================

class OrganizationStats(BaseModel):
    """Organization statistics"""
    organization_id: str
    total_members: int
    total_teams: int
    total_data_items: int
    storage_used_bytes: int
    activity_last_30_days: int
    members_by_role: Dict[str, int]

class TeamStats(BaseModel):
    """Team statistics"""
    team_id: str
    total_members: int
    total_data_items: int
    storage_used_bytes: int
    activity_last_30_days: int
    members_by_role: Dict[str, int]

# ============================================================================
# Permission Check Models
# ============================================================================

class PermissionCheck(BaseModel):
    """Permission check request"""
    user_id: str
    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    permission: str  # e.g., "data.create", "team.update"

class PermissionCheckResponse(BaseModel):
    """Permission check response"""
    has_permission: bool
    user_role: Optional[MemberRole] = None
    reason: Optional[str] = None