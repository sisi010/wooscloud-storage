"""
Authentication router
Handles user registration, login, and user management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timedelta
from bson import ObjectId

from app.models.user import UserCreate, UserLogin, Token, User
from app.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token
)
from app.database import get_database
from app.config import settings
from app.middleware.auth_middleware import verify_token

router = APIRouter()

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user
    
    Creates a new user account with FREE plan by default
    """
    db = await get_database()
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    user_doc = {
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": hashed_password,
        "plan": "free",
        "storage_used": 0,
        "storage_limit": settings.FREE_STORAGE_LIMIT,
        "api_calls_count": 0,
        "api_calls_limit": settings.FREE_API_CALLS_LIMIT,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_active": True
    }
    
    result = await db.users.insert_one(user_doc)
    
    return {
        "success": True,
        "message": "User registered successfully",
        "user_id": str(result.inserted_id),
        "email": user_data.email
    }

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Login and get access token
    
    Returns JWT token for authentication
    """
    db = await get_database()
    
    # Find user
    user = await db.users.find_one({"email": credentials.email})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=dict)
async def get_current_user(current_user: dict = Depends(verify_token)):
    """
    Get current user information
    
    Requires valid JWT token
    """
    return {
        "success": True,
        "user": {
            "id": str(current_user["_id"]),
            "email": current_user["email"],
            "name": current_user["name"],
            "plan": current_user.get("plan", "free"),
            "storage_used": current_user.get("storage_used", 0),
            "storage_limit": current_user.get("storage_limit", settings.FREE_STORAGE_LIMIT),
            "created_at": current_user["created_at"].isoformat()
        }
    }

@router.put("/me", response_model=dict)
async def update_user(
    name: str = None,
    current_user: dict = Depends(verify_token)
):
    """
    Update current user information
    
    Requires valid JWT token
    """
    db = await get_database()
    
    update_data = {
        "updated_at": datetime.utcnow()
    }
    
    if name:
        update_data["name"] = name
    
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": update_data}
    )
    
    return {
        "success": True,
        "message": "User updated successfully"
    }