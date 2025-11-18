"""
Team Collaboration Router
API endpoints for organizations, teams, and members
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional

from app.models.team_models import (
    OrganizationCreate, OrganizationUpdate, Organization, OrganizationListResponse,
    TeamCreate, TeamUpdate, Team, TeamListResponse,
    MemberInvite, MemberUpdate, Member, MemberListResponse,
    Invitation, InvitationListResponse,
    ActivityLogResponse
)
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.team_service import TeamService
from app.services.quota_manager import check_api_calls_quota, increment_api_calls

router = APIRouter()

# ============================================================================
# ORGANIZATIONS
# ============================================================================

@router.post("/organizations", response_model=Organization, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: OrganizationCreate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create a new organization
    
    The creator becomes the owner with full permissions.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        org = await team_service.create_organization(
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return org
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization: {str(e)}"
        )


@router.get("/organizations", response_model=OrganizationListResponse)
async def list_organizations(
    current_user: dict = Depends(verify_api_key)
):
    """
    List all organizations user is member of
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        orgs = await team_service.list_user_organizations(
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        return OrganizationListResponse(
            organizations=orgs,
            total=len(orgs)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list organizations: {str(e)}"
        )


@router.get("/organizations/{org_id}", response_model=Organization)
async def get_organization(
    org_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get organization details
    
    Requires: Organization membership
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        org = await team_service.get_organization(
            org_id=org_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )
        
        return org
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get organization: {str(e)}"
        )


@router.patch("/organizations/{org_id}", response_model=Organization)
async def update_organization(
    org_id: str,
    request: OrganizationUpdate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Update organization
    
    Requires: Admin or Owner role
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        org = await team_service.update_organization(
            org_id=org_id,
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return org
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organization: {str(e)}"
        )


@router.delete("/organizations/{org_id}")
async def delete_organization(
    org_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Delete organization
    
    Requires: Owner role
    WARNING: This will delete all teams, members, and data!
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        deleted = await team_service.delete_organization(
            org_id=org_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        return {"message": "Organization deleted successfully", "organization_id": org_id}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete organization: {str(e)}"
        )


# ============================================================================
# TEAMS
# ============================================================================

@router.post("/teams", response_model=Team, status_code=status.HTTP_201_CREATED)
async def create_team(
    request: TeamCreate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create a new team within an organization
    
    Requires: Admin or Owner role
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        team = await team_service.create_team(
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return team
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create team: {str(e)}"
        )


@router.get("/organizations/{org_id}/teams", response_model=TeamListResponse)
async def list_teams(
    org_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    List all teams in an organization
    
    Requires: Organization membership
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        teams = await team_service.list_organization_teams(
            org_id=org_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        return TeamListResponse(
            teams=teams,
            total=len(teams)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list teams: {str(e)}"
        )


@router.get("/teams/{team_id}", response_model=Team)
async def get_team(
    team_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get team details
    
    Requires: Organization membership
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        team = await team_service.get_team(
            team_id=team_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found or access denied"
            )
        
        return team
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get team: {str(e)}"
        )


# ============================================================================
# MEMBERS
# ============================================================================

@router.post("/organizations/{org_id}/invitations", response_model=Invitation, status_code=status.HTTP_201_CREATED)
async def invite_member(
    org_id: str,
    request: MemberInvite,
    current_user: dict = Depends(verify_api_key)
):
    """
    Invite a member to organization or team
    
    Requires: Admin or Owner role
    
    Returns an invitation with a unique code.
    Send this code to the invitee to join.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        invitation = await team_service.invite_member(
            org_id=org_id,
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return invitation
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invite member: {str(e)}"
        )


@router.post("/invitations/accept", response_model=Member)
async def accept_invitation(
    invitation_code: str = Query(..., description="Invitation code"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Accept an invitation and join organization/team
    
    Use the invitation code received from an admin/owner.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        member = await team_service.accept_invitation(
            invitation_code=invitation_code,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        return member
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to accept invitation: {str(e)}"
        )


@router.get("/organizations/{org_id}/members", response_model=MemberListResponse)
async def list_members(
    org_id: str,
    team_id: Optional[str] = Query(None, description="Filter by team"),
    current_user: dict = Depends(verify_api_key)
):
    """
    List members of organization or team
    
    Requires: Organization membership
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        members = await team_service.list_members(
            org_id=org_id,
            user_id=str(current_user["_id"]),
            team_id=team_id
        )
        
        await increment_api_calls(current_user["_id"])
        
        return MemberListResponse(
            members=members,
            total=len(members)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list members: {str(e)}"
        )


@router.delete("/organizations/{org_id}/members/{member_id}")
async def remove_member(
    org_id: str,
    member_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Remove a member from organization/team
    
    Requires: Admin or Owner role
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        team_service = TeamService(db)
        
        removed = await team_service.remove_member(
            org_id=org_id,
            member_id=member_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        
        return {"message": "Member removed successfully", "member_id": member_id}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove member: {str(e)}"
        )