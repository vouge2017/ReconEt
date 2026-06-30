"""
JWT Authentication API — ReconET

Endpoints:
POST /api/auth/register — Register new user
POST /api/auth/login    — Login, get access + refresh tokens
POST /api/auth/refresh  — Refresh access token
GET  /api/auth/me       — Get current user profile
PUT  /api/auth/me       — Update current user profile
POST /api/auth/change-password — Change password
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import hmac
import os
import json
import base64
import time

from app.database import get_db
from app.models import User, Company, UserRole, AuditTrail

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "reconet-dev-secret-change-in-production-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ─── Pydantic Models ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    company_name: Optional[str] = None
    company_tin: Optional[str] = None
    role: str = "clerk"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    company_id: Optional[str]
    company_name: Optional[str]
    is_active: bool
    created_at: str


# ─── JWT Helpers (pure Python, no external deps) ──────────────────

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += '=' * padding
    return base64.urlsafe_b64decode(s)


def create_token(payload: dict, expires_delta: timedelta) -> str:
    """Create a JWT token (HS256)"""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    
    now = int(time.time())
    payload.update({
        "iat": now,
        "exp": now + int(expires_delta.total_seconds()),
        "iss": "reconet"
    })
    
    header_b64 = _b64url_encode(json.dumps(header).encode())
    payload_b64 = _b64url_encode(json.dumps(payload).encode())
    
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        JWT_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    sig_b64 = _b64url_encode(signature)
    
    return f"{message}.{sig_b64}"


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, sig_b64 = parts
        
        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            JWT_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(sig_b64)
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        # Decode payload
        payload = json.loads(_b64url_decode(payload_b64))
        
        # Check expiration
        if payload.get("exp", 0) < int(time.time()):
            return None
        
        return payload
    except Exception:
        return None


def hash_password(password: str) -> str:
    """Hash password with SHA-256 + salt"""
    salt = os.urandom(32).hex()
    pwd_hash = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    try:
        salt, pwd_hash = password_hash.split(':', 1)
        return hmac.compare_digest(
            pwd_hash,
            hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
        )
    except (ValueError, AttributeError):
        return False


# ─── Dependencies ─────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    return user


def require_role(*roles: str):
    """Dependency factory: require specific user roles"""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}. Your role: {current_user.role}",
            )
        return current_user
    return role_checker


# ─── Audit Helper ─────────────────────────────────────────────────

def log_audit(db: Session, user_id: str, company_id: str, action: str, 
              entity_type: str, entity_id: str, details: dict, ip: str = None):
    """Write to audit trail"""
    entry = AuditTrail(
        company_id=company_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip,
    )
    db.add(entry)
    db.commit()


# ─── Endpoints ────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if email exists
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Validate role
    try:
        role = UserRole(req.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
        )
    
    # Create company if provided
    company_id = None
    if req.company_name:
        company = Company(
            name=req.company_name,
            tin=req.company_tin,
        )
        db.add(company)
        db.flush()
        company_id = company.id
    
    # Create user
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        role=role.value,
        company_id=company_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Generate tokens
    access_token = create_token(
        {"sub": user.id, "email": user.email, "role": user.role, "company_id": company_id},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_token(
        {"sub": user.id, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    # Audit
    log_audit(db, user.id, company_id, "register", "user", user.id,
              {"email": user.email, "role": user.role},
              request.client.host if request.client else None)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "company_id": company_id,
            "company_name": req.company_name,
        }
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Login with email and password"""
    user = db.query(User).filter(User.email == req.email).first()
    
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Get company name
    company_name = None
    if user.company_id:
        company = db.query(Company).filter(Company.id == user.company_id).first()
        company_name = company.name if company else None
    
    # Generate tokens
    access_token = create_token(
        {"sub": user.id, "email": user.email, "role": user.role, "company_id": user.company_id},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_token(
        {"sub": user.id, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    # Audit
    log_audit(db, user.id, user.company_id, "login", "user", user.id,
              {"email": user.email},
              request.client.host if request.client else None)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "company_id": user.company_id,
            "company_name": company_name,
        }
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    """Refresh an expired access token"""
    payload = decode_token(req.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    company_name = None
    if user.company_id:
        company = db.query(Company).filter(Company.id == user.company_id).first()
        company_name = company.name if company else None
    
    access_token = create_token(
        {"sub": user.id, "email": user.email, "role": user.role, "company_id": user.company_id},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    new_refresh_token = create_token(
        {"sub": user.id, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "company_id": user.company_id,
            "company_name": company_name,
        }
    )


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user profile"""
    company_name = None
    if current_user.company_id:
        company = db.query(Company).filter(Company.id == current_user.company_id).first()
        company_name = company.name if company else None
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        company_id=current_user.company_id,
        company_name=company_name,
        is_active=current_user.is_active,
        created_at=str(current_user.created_at),
    )


@router.put("/me")
async def update_profile(
    full_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    if full_name:
        current_user.full_name = full_name
    db.commit()
    return {"status": "updated"}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password"""
    if not verify_password(req.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.password_hash = hash_password(req.new_password)
    db.commit()
    
    log_audit(db, current_user.id, current_user.company_id, "password_change", 
              "user", current_user.id, {},
              request.client.host if request.client else None)
    
    return {"status": "password_changed"}


@router.get("/users")
async def list_users(
    current_user: User = Depends(require_role(UserRole.CFO.value, UserRole.MANAGER.value)),
    db: Session = Depends(get_db)
):
    """List all users in the company (CFO/Manager only)"""
    users = db.query(User).filter(User.company_id == current_user.company_id).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": str(u.created_at),
        }
        for u in users
    ]
