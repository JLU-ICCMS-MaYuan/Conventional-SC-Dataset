"""
创建超级管理员账户

使用方法：
python -m backend.create_superadmin

或设置环境变量后自动创建：
SUPERADMIN_EMAIL=admin@example.com
SUPERADMIN_PASSWORD=your_password
SUPERADMIN_NAME=管理员姓名
"""
from backend.database import SessionLocal
from backend.models import User
from backend.security import hash_password
from datetime import datetime
import os
import getpass


def create_superadmin(email: str, password: str, real_name: str):
    """创建超级管理员账户"""
    db = SessionLocal()

    try:
        # 检查是否已存在该邮箱
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            if existing_user.is_superadmin:
                print(f"❌ 超级管理员 {email} 已存在")
                return False
            else:
                # 升级为超级管理员
                existing_user.is_superadmin = True
                existing_user.is_admin = True
                existing_user.is_approved = True
                existing_user.is_email_verified = True
                existing_user.approved_at = datetime.utcnow()
                db.commit()
                print(f"✅ 已将用户 {email} 升级为超级管理员")
                return True

        # 创建新超级管理员
        superadmin = User(
            email=email,
            password_hash=hash_password(password),
            real_name=real_name,
            is_admin=True,
            is_superadmin=True,
            is_approved=True,
            is_email_verified=True,
            approved_at=datetime.utcnow()
        )

        db.add(superadmin)
        db.commit()

        print("=" * 60)
        print("✅ 超级管理员创建成功！")
        print("=" * 60)
        print(f"邮箱: {email}")
        print(f"姓名: {real_name}")
        print(f"密码: {'*' * len(password)}")
        print("=" * 60)
        print("请妥善保管登录凭证！")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ 创建失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    """主函数：交互式或环境变量创建超级管理员"""
    print("=" * 60)
    print("🔐 超级管理员账户创建工具")
    print("=" * 60)

    # 尝试从环境变量读取
    email = os.getenv("SUPERADMIN_EMAIL")
    password = os.getenv("SUPERADMIN_PASSWORD")
    real_name = os.getenv("SUPERADMIN_NAME")

    if email and password and real_name:
        print("检测到环境变量配置，使用环境变量创建...")
        create_superadmin(email, password, real_name)
        return

    # 交互式输入
    print("\n请输入超级管理员信息:")
    print("-" * 60)

    while True:
        email = input("邮箱 (用于登录): ").strip()
        if "@" in email and "." in email:
            break
        print("❌ 请输入有效的邮箱地址")

    real_name = input("真实姓名: ").strip()
    if not real_name:
        real_name = "超级管理员"

    # 密码输入（隐藏显示）
    while True:
        password = getpass.getpass("密码 (至少6位): ")
        if len(password) < 6:
            print("❌ 密码至少需要6位字符")
            continue

        password_confirm = getpass.getpass("确认密码: ")
        if password != password_confirm:
            print("❌ 两次密码输入不一致，请重新输入")
            continue

        break

    print("\n" + "-" * 60)
    print("即将创建超级管理员账户:")
    print(f"  邮箱: {email}")
    print(f"  姓名: {real_name}")
    print("-" * 60)

    confirm = input("确认创建? (yes/no): ").strip().lower()
    if confirm in ['yes', 'y']:
        create_superadmin(email, password, real_name)
    else:
        print("❌ 已取消")


if __name__ == "__main__":
    main()
