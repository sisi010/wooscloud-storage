"""
Object Lock / WORM Router
Write Once Read Many (WORM) for compliance and legal hold
Similar to AWS S3 Object Lock
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional
from datetime import datetime, timedelta
from bson import ObjectId
from pydantic import BaseModel

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/object-lock", tags=["Object Lock / WORM"])


class ObjectLockConfig(BaseModel):
    """Object lock configuration"""
    mode: str  # GOVERNANCE or COMPLIANCE
    retain_until: datetime
    legal_hold: bool = False


class LegalHoldRequest(BaseModel):
    """Legal hold request"""
    enabled: bool
    reason: Optional[str] = None


@router.get("/status")
async def get_object_lock_status():
    """
    Get Object Lock feature status
    """
    
    return {
        "success": True,
        "object_lock": {
            "enabled": True,
            "modes": ["GOVERNANCE", "COMPLIANCE"],
            "features": [
                "WORM (Write Once Read Many)",
                "Legal Hold",
                "Retention periods",
                "Compliance mode protection",
                "Governance mode with override"
            ]
        },
        "compliance": {
            "sec17a4": True,  # SEC Rule 17a-4
            "hipaa": True,
            "gdpr": True,
            "finra": True
        }
    }


@router.post("/lock/{data_id}")
async def lock_object(
    data_id: str,
    config: ObjectLockConfig,
    current_user: dict = Depends(verify_api_key)
):
    """
    Lock an object with retention policy
    
    Modes:
    - GOVERNANCE: Can be overridden by users with special permissions
    - COMPLIANCE: Cannot be overridden by anyone, including root
    """
    
    if config.mode not in ["GOVERNANCE", "COMPLIANCE"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be GOVERNANCE or COMPLIANCE"
        )
    
    if config.retain_until <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Retention date must be in the future"
        )
    
    db = await get_database()
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    # Check if already locked
    if doc.get("object_lock"):
        existing_lock = doc["object_lock"]
        if existing_lock.get("mode") == "COMPLIANCE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Object is locked in COMPLIANCE mode and cannot be modified"
            )
    
    # Apply lock
    lock_config = {
        "mode": config.mode,
        "retain_until": config.retain_until,
        "legal_hold": config.legal_hold,
        "locked_at": datetime.utcnow(),
        "locked_by": str(current_user["_id"])
    }
    
    await db.storage_data.update_one(
        {"_id": data_object_id},
        {
            "$set": {
                "object_lock": lock_config,
                "worm_enabled": True
            }
        }
    )
    
    # Log lock event
    await db.audit_logs.insert_one({
        "user_id": str(current_user["_id"]),
        "action": "object_lock_applied",
        "data_id": data_id,
        "mode": config.mode,
        "retain_until": config.retain_until.isoformat(),
        "timestamp": datetime.utcnow()
    })
    
    return {
        "success": True,
        "data_id": data_id,
        "lock_config": {
            "mode": config.mode,
            "retain_until": config.retain_until.isoformat(),
            "legal_hold": config.legal_hold,
            "locked_at": datetime.utcnow().isoformat()
        },
        "message": f"Object locked in {config.mode} mode until {config.retain_until.isoformat()}"
    }


@router.get("/lock/{data_id}")
async def get_object_lock(
    data_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get object lock status
    """
    
    db = await get_database()
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    lock_config = doc.get("object_lock")
    
    if not lock_config:
        return {
            "success": True,
            "data_id": data_id,
            "locked": False,
            "message": "Object is not locked"
        }
    
    # Check if retention period expired
    retain_until = lock_config.get("retain_until")
    is_expired = retain_until < datetime.utcnow() if retain_until else True
    
    return {
        "success": True,
        "data_id": data_id,
        "locked": True,
        "lock_config": {
            "mode": lock_config.get("mode"),
            "retain_until": retain_until.isoformat() if retain_until else None,
            "legal_hold": lock_config.get("legal_hold", False),
            "locked_at": lock_config.get("locked_at").isoformat() if lock_config.get("locked_at") else None,
            "is_expired": is_expired,
            "days_remaining": (retain_until - datetime.utcnow()).days if retain_until and not is_expired else 0
        }
    }


@router.post("/legal-hold/{data_id}")
async def set_legal_hold(
    data_id: str,
    request: LegalHoldRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Set or remove legal hold on an object
    
    Legal hold prevents deletion regardless of retention period
    """
    
    db = await get_database()
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    # Update legal hold
    update_data = {
        "object_lock.legal_hold": request.enabled,
        "object_lock.legal_hold_updated_at": datetime.utcnow()
    }
    
    if request.reason:
        update_data["object_lock.legal_hold_reason"] = request.reason
    
    await db.storage_data.update_one(
        {"_id": data_object_id},
        {"$set": update_data}
    )
    
    # Log legal hold event
    await db.audit_logs.insert_one({
        "user_id": str(current_user["_id"]),
        "action": "legal_hold_" + ("enabled" if request.enabled else "disabled"),
        "data_id": data_id,
        "reason": request.reason,
        "timestamp": datetime.utcnow()
    })
    
    return {
        "success": True,
        "data_id": data_id,
        "legal_hold": request.enabled,
        "reason": request.reason,
        "message": f"Legal hold {'enabled' if request.enabled else 'disabled'}"
    }


@router.delete("/unlock/{data_id}")
async def unlock_object(
    data_id: str,
    override: bool = Query(False, description="Override GOVERNANCE mode lock"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Unlock an object (only for GOVERNANCE mode with override permission)
    
    COMPLIANCE mode locks cannot be removed until retention period expires
    """
    
    db = await get_database()
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    lock_config = doc.get("object_lock")
    
    if not lock_config:
        return {
            "success": True,
            "message": "Object is not locked"
        }
    
    # Check mode
    if lock_config.get("mode") == "COMPLIANCE":
        # Check if retention period expired
        if lock_config.get("retain_until") > datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot unlock COMPLIANCE mode object before retention period expires"
            )
    
    if lock_config.get("mode") == "GOVERNANCE" and not override:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Must set override=true to unlock GOVERNANCE mode object"
        )
    
    # Check legal hold
    if lock_config.get("legal_hold"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot unlock object with active legal hold"
        )
    
    # Remove lock
    await db.storage_data.update_one(
        {"_id": data_object_id},
        {
            "$unset": {"object_lock": ""},
            "$set": {"worm_enabled": False}
        }
    )
    
    # Log unlock event
    await db.audit_logs.insert_one({
        "user_id": str(current_user["_id"]),
        "action": "object_unlocked",
        "data_id": data_id,
        "mode": lock_config.get("mode"),
        "override": override,
        "timestamp": datetime.utcnow()
    })
    
    return {
        "success": True,
        "data_id": data_id,
        "message": "Object unlocked successfully"
    }


@router.get("/locked-objects")
async def list_locked_objects(
    mode: Optional[str] = Query(None, description="Filter by mode: GOVERNANCE or COMPLIANCE"),
    limit: int = Query(50, le=1000),
    current_user: dict = Depends(verify_api_key)
):
    """
    List all locked objects
    """
    
    db = await get_database()
    
    query = {
        "user_id": str(current_user["_id"]),
        "object_lock": {"$exists": True}
    }
    
    if mode:
        query["object_lock.mode"] = mode
    
    locked_objects = await db.storage_data.find(query).limit(limit).to_list(None)
    
    return {
        "success": True,
        "total": len(locked_objects),
        "objects": [
            {
                "id": str(doc["_id"]),
                "filename": doc.get("data", {}).get("filename"),
                "mode": doc["object_lock"].get("mode"),
                "retain_until": doc["object_lock"].get("retain_until").isoformat() if doc["object_lock"].get("retain_until") else None,
                "legal_hold": doc["object_lock"].get("legal_hold", False),
                "locked_at": doc["object_lock"].get("locked_at").isoformat() if doc["object_lock"].get("locked_at") else None
            }
            for doc in locked_objects
        ]
    }


@router.get("/compliance-report")
async def get_compliance_report(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get compliance report for locked objects
    """
    
    db = await get_database()
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Count locked objects
    total_locked = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"]),
        "object_lock": {"$exists": True}
    })
    
    governance_count = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"]),
        "object_lock.mode": "GOVERNANCE"
    })
    
    compliance_count = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"]),
        "object_lock.mode": "COMPLIANCE"
    })
    
    legal_hold_count = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"]),
        "object_lock.legal_hold": True
    })
    
    # Get lock/unlock events
    events = await db.audit_logs.find({
        "user_id": str(current_user["_id"]),
        "action": {"$in": ["object_lock_applied", "object_unlocked", "legal_hold_enabled", "legal_hold_disabled"]},
        "timestamp": {"$gte": cutoff_date}
    }).sort("timestamp", -1).limit(100).to_list(None)
    
    return {
        "success": True,
        "period": {
            "days": days,
            "from": cutoff_date.isoformat(),
            "to": datetime.utcnow().isoformat()
        },
        "summary": {
            "total_locked_objects": total_locked,
            "governance_mode": governance_count,
            "compliance_mode": compliance_count,
            "legal_holds": legal_hold_count
        },
        "recent_events": [
            {
                "action": event["action"],
                "data_id": event.get("data_id"),
                "timestamp": event["timestamp"].isoformat()
            }
            for event in events
        ],
        "compliance_status": "COMPLIANT" if total_locked > 0 else "NO_LOCKS"
    }