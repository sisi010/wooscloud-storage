"""
Object Lifecycle Router
Automatic data management with lifecycle rules
Similar to AWS S3 Lifecycle Policies
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId
from pydantic import BaseModel

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/lifecycle", tags=["Object Lifecycle"])


class LifecycleAction(BaseModel):
    """Lifecycle action types"""
    type: str  # delete, archive, transition
    days: int  # Days after creation
    storage_class: Optional[str] = None  # For transition action


class LifecycleRule(BaseModel):
    """Lifecycle rule definition"""
    rule_id: Optional[str] = None
    name: str
    collection: Optional[str] = None  # Apply to specific collection
    prefix: Optional[str] = None  # Apply to files with prefix
    enabled: bool = True
    actions: List[LifecycleAction]


@router.post("/rules")
async def create_lifecycle_rule(
    rule: LifecycleRule,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create a lifecycle rule
    
    Example:
    - Delete files older than 30 days
    - Move to Archive after 90 days
    - Transition to Cold storage after 60 days
    """
    
    db = await get_database()
    
    # Generate rule ID
    rule_id = f"rule-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    rule_doc = {
        "rule_id": rule_id,
        "user_id": str(current_user["_id"]),
        "name": rule.name,
        "collection": rule.collection,
        "prefix": rule.prefix,
        "enabled": rule.enabled,
        "actions": [action.dict() for action in rule.actions],
        "created_at": datetime.utcnow(),
        "last_executed": None,
        "stats": {
            "total_executions": 0,
            "total_affected": 0,
            "last_affected": 0
        }
    }
    
    await db.lifecycle_rules.insert_one(rule_doc)
    
    return {
        "success": True,
        "rule_id": rule_id,
        "message": "Lifecycle rule created"
    }


@router.get("/rules")
async def list_lifecycle_rules(
    current_user: dict = Depends(verify_api_key)
):
    """
    List all lifecycle rules
    """
    
    db = await get_database()
    
    cursor = db.lifecycle_rules.find({
        "user_id": str(current_user["_id"])
    }).sort("created_at", -1)
    
    rules = await cursor.to_list(None)
    
    result = []
    for rule in rules:
        result.append({
            "rule_id": rule["rule_id"],
            "name": rule["name"],
            "collection": rule.get("collection"),
            "prefix": rule.get("prefix"),
            "enabled": rule["enabled"],
            "actions": rule["actions"],
            "created_at": rule["created_at"].isoformat(),
            "stats": rule.get("stats", {})
        })
    
    return {
        "success": True,
        "total": len(result),
        "rules": result
    }


@router.get("/rules/{rule_id}")
async def get_lifecycle_rule(
    rule_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get specific lifecycle rule
    """
    
    db = await get_database()
    
    rule = await db.lifecycle_rules.find_one({
        "rule_id": rule_id,
        "user_id": str(current_user["_id"])
    })
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lifecycle rule not found"
        )
    
    return {
        "success": True,
        "rule": {
            "rule_id": rule["rule_id"],
            "name": rule["name"],
            "collection": rule.get("collection"),
            "prefix": rule.get("prefix"),
            "enabled": rule["enabled"],
            "actions": rule["actions"],
            "created_at": rule["created_at"].isoformat(),
            "last_executed": rule["last_executed"].isoformat() if rule.get("last_executed") else None,
            "stats": rule.get("stats", {})
        }
    }


@router.put("/rules/{rule_id}")
async def update_lifecycle_rule(
    rule_id: str,
    rule: LifecycleRule,
    current_user: dict = Depends(verify_api_key)
):
    """
    Update lifecycle rule
    """
    
    db = await get_database()
    
    existing = await db.lifecycle_rules.find_one({
        "rule_id": rule_id,
        "user_id": str(current_user["_id"])
    })
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lifecycle rule not found"
        )
    
    update_data = {
        "name": rule.name,
        "collection": rule.collection,
        "prefix": rule.prefix,
        "enabled": rule.enabled,
        "actions": [action.dict() for action in rule.actions],
        "updated_at": datetime.utcnow()
    }
    
    await db.lifecycle_rules.update_one(
        {"rule_id": rule_id},
        {"$set": update_data}
    )
    
    return {
        "success": True,
        "message": "Lifecycle rule updated"
    }


@router.delete("/rules/{rule_id}")
async def delete_lifecycle_rule(
    rule_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Delete lifecycle rule
    """
    
    db = await get_database()
    
    result = await db.lifecycle_rules.delete_one({
        "rule_id": rule_id,
        "user_id": str(current_user["_id"])
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lifecycle rule not found"
        )
    
    return {
        "success": True,
        "message": "Lifecycle rule deleted"
    }


@router.post("/execute")
async def execute_lifecycle_rules(
    rule_id: Optional[str] = None,
    current_user: dict = Depends(verify_api_key)
):
    """
    Manually execute lifecycle rules
    
    If rule_id provided, execute only that rule
    Otherwise, execute all enabled rules
    """
    
    db = await get_database()
    
    # Get rules to execute
    if rule_id:
        rules = await db.lifecycle_rules.find({
            "rule_id": rule_id,
            "user_id": str(current_user["_id"]),
            "enabled": True
        }).to_list(None)
    else:
        rules = await db.lifecycle_rules.find({
            "user_id": str(current_user["_id"]),
            "enabled": True
        }).to_list(None)
    
    if not rules:
        return {
            "success": True,
            "message": "No enabled rules to execute",
            "executed": 0,
            "affected": 0
        }
    
    total_affected = 0
    execution_results = []
    
    for rule in rules:
        # Build query
        query = {"user_id": str(current_user["_id"])}
        
        if rule.get("collection"):
            query["collection"] = rule["collection"]
        
        # Execute each action
        for action in rule["actions"]:
            action_type = action["type"]
            days = action["days"]
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Add date filter
            query["created_at"] = {"$lt": cutoff_date}
            
            if action_type == "delete":
                # Delete old objects
                result = await db.storage_data.delete_many(query)
                affected = result.deleted_count
                
            elif action_type == "archive":
                # Move to archive storage class
                result = await db.storage_data.update_many(
                    query,
                    {"$set": {
                        "storage_class": "archive",
                        "archived_at": datetime.utcnow()
                    }}
                )
                affected = result.modified_count
                
            elif action_type == "transition":
                # Transition to different storage class
                storage_class = action.get("storage_class", "cold")
                result = await db.storage_data.update_many(
                    query,
                    {"$set": {
                        "storage_class": storage_class,
                        "transitioned_at": datetime.utcnow()
                    }}
                )
                affected = result.modified_count
            
            else:
                affected = 0
            
            total_affected += affected
            
            execution_results.append({
                "rule_id": rule["rule_id"],
                "rule_name": rule["name"],
                "action": action_type,
                "days": days,
                "affected": affected
            })
        
        # Update rule stats
        await db.lifecycle_rules.update_one(
            {"rule_id": rule["rule_id"]},
            {
                "$set": {
                    "last_executed": datetime.utcnow(),
                    "stats.last_affected": total_affected
                },
                "$inc": {
                    "stats.total_executions": 1,
                    "stats.total_affected": total_affected
                }
            }
        )
    
    return {
        "success": True,
        "message": "Lifecycle rules executed",
        "executed": len(rules),
        "total_affected": total_affected,
        "results": execution_results
    }


@router.get("/preview/{rule_id}")
async def preview_lifecycle_rule(
    rule_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Preview what would be affected by a lifecycle rule
    Without actually executing it
    """
    
    db = await get_database()
    
    rule = await db.lifecycle_rules.find_one({
        "rule_id": rule_id,
        "user_id": str(current_user["_id"])
    })
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lifecycle rule not found"
        )
    
    # Build query
    query = {"user_id": str(current_user["_id"])}
    
    if rule.get("collection"):
        query["collection"] = rule["collection"]
    
    preview_results = []
    
    for action in rule["actions"]:
        days = action["days"]
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query["created_at"] = {"$lt": cutoff_date}
        
        # Count affected documents
        count = await db.storage_data.count_documents(query)
        
        # Get sample documents
        sample_cursor = db.storage_data.find(query).limit(5)
        samples = await sample_cursor.to_list(None)
        
        preview_results.append({
            "action": action["type"],
            "days": days,
            "would_affect": count,
            "samples": [
                {
                    "id": str(doc["_id"]),
                    "collection": doc.get("collection"),
                    "created_at": doc["created_at"].isoformat()
                }
                for doc in samples
            ]
        })
    
    return {
        "success": True,
        "rule_id": rule_id,
        "rule_name": rule["name"],
        "preview": preview_results
    }