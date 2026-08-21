"""
管理员认证 API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from backend.database import get_db
from backend.models import User
from backend.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_verification_code,
    get_current_user,
    get_current_admin,
    get_current_superadmin
)
from backend.email_service import email_service
from backend.username_policy import validate_username

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _is_admin(user: User) -> bool:
    return user.role in {"admin", "superadmin"}


def _is_superadmin(user: User) -> bool:
    return user.role == "superadmin"


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "username_change_allowed": user.username_change_allowed,
        "role": user.role,
        "is_admin": _is_admin(user),
        "is_superadmin": _is_superadmin(user),
        "is_approved": user.is_approved,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "approved_at": user.approved_at.isoformat() if user.approved_at else None,
    }


# Pydantic 模型
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: str
    real_name: str | None = None
    is_admin: bool = False  # 是否申请成为管理员


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.get("/username-availability", summary="检查公开用户名是否可用")
async def username_availability(username: str, db: Session = Depends(get_db)):
    reason = validate_username(username)
    if reason:
        return {"available": False, "reason": reason}
    exists = db.query(User.id).filter(User.username == username).first()
    return {
        "available": exists is None,
        **({"reason": "用户名已被占用"} if exists else {}),
    }


@router.post("/register", summary="用户/管理员注册（第一步：发送验证码）")
async def register_step1(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    注册流程第一步：验证邮箱并发送验证码

    流程：
    1. 检查邮箱是否已注册
    2. 生成6位数字验证码
    3. 发送验证码到邮箱
    4. 创建待验证的用户记录
    """
    username_error = validate_username(request.username)
    if username_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=username_error)

    # 检查邮箱和大小写敏感用户名是否已存在
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user and existing_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已注册"
        )
    if existing_user and existing_user.username != request.username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该邮箱已占用其他用户名",
        )
    username_owner = db.query(User.id).filter(User.username == request.username).first()
    if username_owner and (not existing_user or username_owner[0] != existing_user.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已被占用",
        )

    # 生成验证码
    code = generate_verification_code()
    expires = datetime.utcnow() + timedelta(minutes=5)

    # 发送验证码邮件
    success = email_service.send_verification_code(
        to_email=request.email,
        code=code,
        username=request.username,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证码失败，请稍后重试"
        )

    # 如果用户已存在但未验证，更新信息
    if existing_user:
        existing_user.password_hash = hash_password(request.password)
        existing_user.real_name = request.real_name or ""
        existing_user.role = "admin" if request.is_admin else "user"
        existing_user.verification_code = code
        existing_user.verification_expires = expires
        existing_user.is_approved = not request.is_admin
    else:
        # 创建新用户（待验证状态）
        new_user = User(
            email=request.email,
            username=request.username,
            username_change_allowed=False,
            password_hash=hash_password(request.password),
            real_name=request.real_name or "",
            role="admin" if request.is_admin else "user",
            is_email_verified=False,
            is_approved=not request.is_admin,  # 普通用户直接标记为已批准，只有管理员需要审核
            verification_code=code,
            verification_expires=expires
        )
        db.add(new_user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱或用户名已被占用",
        ) from exc

    return {
        "message": "验证码已发送到您的邮箱，请在5分钟内完成验证",
        "email": request.email,
        "requires_email_verification": True,
    }


@router.post("/verify-email", summary="注册验证（第二步：验证邮箱）")
async def register_step2(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    注册流程第二步：验证邮箱验证码

    验证成功后：
    - 管理员：进入待审批状态
    - 普通用户：直接可以登录
    """
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在，请先注册"
        )

    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已验证，请直接登录"
        )

    # 检查验证码
    if user.verification_code != request.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误"
        )

    # 检查验证码是否过期
    if user.verification_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期，请重新获取"
        )

    # 验证成功
    user.is_email_verified = True
    user.verification_code = None
    user.verification_expires = None
    db.commit()

    if _is_admin(user):
        message = "邮箱验证成功！您的管理员申请已提交，请等待超级管理员审批"
        status_val = "pending_approval"
    else:
        message = "注册成功！您现在可以登录并上传文献了"
        status_val = "active"

    return {
        "message": message,
        "email": user.email,
        "username": user.username,
        "status": status_val
    }


@router.post("/login", response_model=TokenResponse, summary="用户/管理员登录")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    用户/管理员登录
    """
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="邮箱未验证，请先完成邮箱验证"
        )

    # 如果是管理员，必须审批通过
    if _is_admin(user) and not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的管理员申请尚未通过审批，请耐心等待"
        )

    # 创建访问令牌
    access_token = create_access_token(data={"sub": user.email})

    return TokenResponse(
        access_token=access_token,
        user=_user_payload(user),
    )


@router.get("/me", summary="获取当前用户信息")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户的信息"""
    return _user_payload(current_user)
