"""
Team Collaboration Service
Handles organizations, teams, members, and permissions
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import secrets
import logging

from app.models.team_models import (
    MemberRole, InvitationStatus, ActivityType,
    ROLE_PERMISSIONS,
    OrganizationCreate, OrganizationUpdate, Organization,
    TeamCreate, TeamUpdate, Team,
    MemberInvite, MemberUpdate, Member, Invitation,
    Activity, OrganizationStats, TeamStats
)

logger = logging.getLogger(__name__)

class TeamService:
    """
    Team Collaboration Service
    
    Features:
    - Organization management
    - Team creation and management
    - Member invitations and roles
    - Role-based access control (RBAC)
    - Activity logging
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.organizations = db.organizations
        self.teams = db.teams
        self.members = db.team_members
        self.invitations = db.team_invitations
        self.activities = db.team_activities
    
    # ========================================================================
    # ORGANIZATIONS
    # ========================================================================
    
    async def create_organization(
        self,
        user_id: str,
        request: OrganizationCreate
    ) -> Organization:
        """Create a new organization"""
        
        org_id = str(ObjectId())
        
        org_doc = {
            "_id": org_id,
            "name": request.name,
            "description": request.description,
            "owner_id": user_id,
            "settings": request.settings or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.organizations.insert_one(org_doc)
        
        # Add owner as member
        await self._add_member_internal(
            organization_id=org_id,
            user_id=user_id,
            role=MemberRole.OWNER,
            invited_by=user_id
        )
        
        # Log activity
        await self._log_activity(
            organization_id=org_id,
            user_id=user_id,
            activity_type=ActivityType.ORG_CREATED,
            resource_type="organization",
            resource_id=org_id,
            details={"name": request.name}
        )
        
        return await self.get_organization(org_id, user_id)
    
    async def get_organization(
        self,
        org_id: str,
        user_id: str
    ) -> Optional[Organization]:
        """Get organization by ID"""
        
        # Check membership
        member = await self.members.find_one({
            "organization_id": org_id,
            "user_id": user_id
        })
        
        if not member:
            return None
        
        org = await self.organizations.find_one({"_id": org_id})
        
        if not org:
            return None
        
        # Get counts
        member_count = await self.members.count_documents({
            "organization_id": org_id
        })
        
        team_count = await self.teams.count_documents({
            "organization_id": org_id
        })
        
        return Organization(
            id=str(org["_id"]),
            name=org["name"],
            description=org.get("description"),
            owner_id=org["owner_id"],
            settings=org.get("settings", {}),
            member_count=member_count,
            team_count=team_count,
            created_at=org["created_at"].isoformat(),
            updated_at=org["updated_at"].isoformat()
        )
    
    async def list_user_organizations(
        self,
        user_id: str
    ) -> List[Organization]:
        """List organizations user is member of"""
        
        # Get all memberships
        memberships = await self.members.find({
            "user_id": user_id
        }).to_list(None)
        
        org_ids = list(set([m["organization_id"] for m in memberships]))
        
        organizations = []
        for org_id in org_ids:
            org = await self.get_organization(org_id, user_id)
            if org:
                organizations.append(org)
        
        return organizations
    
    async def update_organization(
        self,
        org_id: str,
        user_id: str,
        request: OrganizationUpdate
    ) -> Organization:
        """Update organization"""
        
        # Check permission
        if not await self._check_permission(user_id, org_id, "org.update"):
            raise ValueError("Insufficient permissions")
        
        update_doc = {"updated_at": datetime.utcnow()}
        
        if request.name:
            update_doc["name"] = request.name
        if request.description is not None:
            update_doc["description"] = request.description
        if request.settings is not None:
            update_doc["settings"] = request.settings
        
        await self.organizations.update_one(
            {"_id": org_id},
            {"$set": update_doc}
        )
        
        await self._log_activity(
            organization_id=org_id,
            user_id=user_id,
            activity_type=ActivityType.ORG_UPDATED,
            resource_type="organization",
            resource_id=org_id,
            details={"updates": list(update_doc.keys())}
        )
        
        return await self.get_organization(org_id, user_id)
    
    async def delete_organization(
        self,
        org_id: str,
        user_id: str
    ) -> bool:
        """Delete organization (owner only)"""
        
        # Check if user is owner
        member = await self.members.find_one({
            "organization_id": org_id,
            "user_id": user_id,
            "role": MemberRole.OWNER.value
        })
        
        if not member:
            raise ValueError("Only organization owner can delete")
        
        # Delete all teams
        await self.teams.delete_many({"organization_id": org_id})
        
        # Delete all members
        await self.members.delete_many({"organization_id": org_id})
        
        # Delete all invitations
        await self.invitations.delete_many({"organization_id": org_id})
        
        # Delete organization
        result = await self.organizations.delete_one({"_id": org_id})
        
        return result.deleted_count > 0
    
    # ========================================================================
    # TEAMS
    # ========================================================================
    
    async def create_team(
        self,
        user_id: str,
        request: TeamCreate
    ) -> Team:
        """Create a new team"""
        
        # Check permission
        if not await self._check_permission(user_id, request.organization_id, "team.create"):
            raise ValueError("Insufficient permissions")
        
        team_id = str(ObjectId())
        
        team_doc = {
            "_id": team_id,
            "organization_id": request.organization_id,
            "name": request.name,
            "description": request.description,
            "created_by": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.teams.insert_one(team_doc)
        
        await self._log_activity(
            organization_id=request.organization_id,
            user_id=user_id,
            activity_type=ActivityType.TEAM_CREATED,
            resource_type="team",
            resource_id=team_id,
            details={"name": request.name}
        )
        
        return await self.get_team(team_id, user_id)
    
    async def get_team(
        self,
        team_id: str,
        user_id: str
    ) -> Optional[Team]:
        """Get team by ID"""
        
        team = await self.teams.find_one({"_id": team_id})
        
        if not team:
            return None
        
        # Check membership
        member = await self.members.find_one({
            "organization_id": team["organization_id"],
            "user_id": user_id
        })
        
        if not member:
            return None
        
        # Get member count
        member_count = await self.members.count_documents({
            "team_id": team_id
        })
        
        return Team(
            id=str(team["_id"]),
            organization_id=team["organization_id"],
            name=team["name"],
            description=team.get("description"),
            member_count=member_count,
            created_by=team["created_by"],
            created_at=team["created_at"].isoformat(),
            updated_at=team["updated_at"].isoformat()
        )
    
    async def list_organization_teams(
        self,
        org_id: str,
        user_id: str
    ) -> List[Team]:
        """List teams in organization"""
        
        # Check membership
        member = await self.members.find_one({
            "organization_id": org_id,
            "user_id": user_id
        })
        
        if not member:
            return []
        
        teams = await self.teams.find({
            "organization_id": org_id
        }).to_list(None)
        
        result = []
        for team in teams:
            team_obj = await self.get_team(str(team["_id"]), user_id)
            if team_obj:
                result.append(team_obj)
        
        return result
    
    # ========================================================================
    # MEMBERS
    # ========================================================================
    
    async def invite_member(
        self,
        org_id: str,
        user_id: str,
        request: MemberInvite
    ) -> Invitation:
        """Invite a member to organization or team"""
        
        # Check permission
        if not await self._check_permission(user_id, org_id, "member.invite"):
            raise ValueError("Insufficient permissions")
        
        # Generate invitation code
        invitation_code = secrets.token_urlsafe(32)
        invitation_id = str(ObjectId())
        
        invitation_doc = {
            "_id": invitation_id,
            "organization_id": org_id,
            "team_id": request.team_id,
            "email": request.email,
            "user_id": request.user_id,
            "role": request.role.value,
            "status": InvitationStatus.PENDING.value,
            "invited_by": user_id,
            "invitation_code": invitation_code,
            "expires_at": datetime.utcnow() + timedelta(days=7),
            "created_at": datetime.utcnow()
        }
        
        await self.invitations.insert_one(invitation_doc)
        
        await self._log_activity(
            organization_id=org_id,
            team_id=request.team_id,
            user_id=user_id,
            activity_type=ActivityType.MEMBER_INVITED,
            resource_type="invitation",
            resource_id=invitation_id,
            details={"email": request.email, "role": request.role.value}
        )
        
        invitation_doc["id"] = invitation_id
        return self._doc_to_invitation(invitation_doc)
    
    async def accept_invitation(
        self,
        invitation_code: str,
        user_id: str
    ) -> Member:
        """Accept invitation and join organization/team"""
        
        invitation = await self.invitations.find_one({
            "invitation_code": invitation_code,
            "status": InvitationStatus.PENDING.value
        })
        
        if not invitation:
            raise ValueError("Invalid or expired invitation")
        
        # Check expiration
        if invitation["expires_at"] < datetime.utcnow():
            await self.invitations.update_one(
                {"_id": invitation["_id"]},
                {"$set": {"status": InvitationStatus.EXPIRED.value}}
            )
            raise ValueError("Invitation expired")
        
        # Add member
        member = await self._add_member_internal(
            organization_id=invitation["organization_id"],
            team_id=invitation.get("team_id"),
            user_id=user_id,
            role=MemberRole(invitation["role"]),
            invited_by=invitation["invited_by"]
        )
        
        # Update invitation
        await self.invitations.update_one(
            {"_id": invitation["_id"]},
            {
                "$set": {
                    "status": InvitationStatus.ACCEPTED.value,
                    "accepted_at": datetime.utcnow()
                }
            }
        )
        
        await self._log_activity(
            organization_id=invitation["organization_id"],
            team_id=invitation.get("team_id"),
            user_id=user_id,
            activity_type=ActivityType.MEMBER_JOINED,
            resource_type="member",
            resource_id=member.id,
            details={"role": invitation["role"]}
        )
        
        return member
    
    async def _add_member_internal(
        self,
        organization_id: str,
        user_id: str,
        role: MemberRole,
        invited_by: str,
        team_id: Optional[str] = None
    ) -> Member:
        """Internal method to add member"""
        
        member_id = str(ObjectId())
        
        member_doc = {
            "_id": member_id,
            "organization_id": organization_id,
            "team_id": team_id,
            "user_id": user_id,
            "role": role.value,
            "invited_by": invited_by,
            "joined_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.members.insert_one(member_doc)
        
        member_doc["id"] = member_id
        return self._doc_to_member(member_doc)
    
    async def list_members(
        self,
        org_id: str,
        user_id: str,
        team_id: Optional[str] = None
    ) -> List[Member]:
        """List members of organization or team"""
        
        # Check permission
        if not await self._check_permission(user_id, org_id, "member.read"):
            raise ValueError("Insufficient permissions")
        
        query = {"organization_id": org_id}
        if team_id:
            query["team_id"] = team_id
        
        members = await self.members.find(query).to_list(None)
        
        return [self._doc_to_member(m) for m in members]
    
    async def remove_member(
        self,
        org_id: str,
        member_id: str,
        user_id: str
    ) -> bool:
        """Remove member from organization/team"""
        
        # Check permission
        if not await self._check_permission(user_id, org_id, "member.remove"):
            raise ValueError("Insufficient permissions")
        
        result = await self.members.delete_one({
            "_id": member_id,
            "organization_id": org_id
        })
        
        if result.deleted_count > 0:
            await self._log_activity(
                organization_id=org_id,
                user_id=user_id,
                activity_type=ActivityType.MEMBER_REMOVED,
                resource_type="member",
                resource_id=member_id,
                details={}
            )
        
        return result.deleted_count > 0
    
    # ========================================================================
    # PERMISSIONS
    # ========================================================================
    
    async def _check_permission(
        self,
        user_id: str,
        org_id: str,
        permission: str,
        team_id: Optional[str] = None
    ) -> bool:
        """Check if user has permission"""
        
        # Get member
        query = {
            "organization_id": org_id,
            "user_id": user_id
        }
        
        if team_id:
            query["team_id"] = team_id
        
        member = await self.members.find_one(query)
        
        if not member:
            return False
        
        role = MemberRole(member["role"])
        permissions = ROLE_PERMISSIONS.get(role, [])
        
        # Check wildcard permissions
        for perm in permissions:
            if perm == permission:
                return True
            if perm.endswith(".*"):
                prefix = perm[:-2]
                if permission.startswith(prefix + "."):
                    return True
        
        return False
    
    # ========================================================================
    # ACTIVITY LOGGING
    # ========================================================================
    
    async def _log_activity(
        self,
        organization_id: str,
        user_id: str,
        activity_type: ActivityType,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any],
        team_id: Optional[str] = None
    ):
        """Log activity"""
        
        activity_doc = {
            "_id": str(ObjectId()),
            "organization_id": organization_id,
            "team_id": team_id,
            "user_id": user_id,
            "activity_type": activity_type.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "created_at": datetime.utcnow()
        }
        
        await self.activities.insert_one(activity_doc)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _doc_to_member(self, doc: Dict[str, Any]) -> Member:
        """Convert document to Member"""
        return Member(
            id=str(doc.get("id", doc.get("_id"))),
            organization_id=doc["organization_id"],
            team_id=doc.get("team_id"),
            user_id=doc["user_id"],
            role=MemberRole(doc["role"]),
            invited_by=doc["invited_by"],
            joined_at=doc["joined_at"].isoformat(),
            updated_at=doc["updated_at"].isoformat()
        )
    
    def _doc_to_invitation(self, doc: Dict[str, Any]) -> Invitation:
        """Convert document to Invitation"""
        return Invitation(
            id=str(doc.get("id", doc.get("_id"))),
            organization_id=doc["organization_id"],
            team_id=doc.get("team_id"),
            email=doc.get("email"),
            user_id=doc.get("user_id"),
            role=MemberRole(doc["role"]),
            status=InvitationStatus(doc["status"]),
            invited_by=doc["invited_by"],
            invitation_code=doc["invitation_code"],
            expires_at=doc["expires_at"].isoformat(),
            created_at=doc["created_at"].isoformat(),
            accepted_at=doc.get("accepted_at").isoformat() if doc.get("accepted_at") else None
        )