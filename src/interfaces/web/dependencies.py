from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.infrastructure.database.session import SessionLocal
from src.infrastructure.database.sql_subscription_repository import SqlSubscriptionRepository
from src.infrastructure.database.sql_user_repository import SqlUserRepository
from src.infrastructure.database.sql_audit_log_repository import SqlAuditLogRepository
from src.infrastructure.database.sql_config_option_repository import SqlConfigOptionRepository
from src.application.use_cases.create_subscription import CreateSubscriptionUseCase
from src.application.use_cases.update_subscription import UpdateSubscriptionUseCase
from src.application.use_cases.delete_subscription import DeleteSubscriptionUseCase
from src.application.use_cases.get_subscription import GetSubscriptionUseCase
from src.application.use_cases.list_subscriptions import ListSubscriptionsUseCase
from src.application.use_cases.auth.login_user import LoginUserUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.application.use_cases.auth.update_user_permissions import UpdateUserPermissionsUseCase
from src.application.use_cases.auth.list_users import ListUsersUseCase
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.domain.entities.user import User
from src.interfaces.web.session import get_session_user_id

templates = Jinja2Templates(directory="src/interfaces/web/templates")


class NotAuthenticatedException(Exception):
    pass


class ForbiddenException(Exception):
    pass


def get_db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_repo(session: Session = Depends(get_db_session)) -> SqlSubscriptionRepository:
    return SqlSubscriptionRepository(session)


def get_user_repo(session: Session = Depends(get_db_session)) -> SqlUserRepository:
    return SqlUserRepository(session)


def get_audit_log_repo(session: Session = Depends(get_db_session)) -> SqlAuditLogRepository:
    return SqlAuditLogRepository(session)


def get_config_repo(session: Session = Depends(get_db_session)) -> SqlConfigOptionRepository:
    return SqlConfigOptionRepository(session)


# ── Subscription use cases ──────────────────────────────────────────────────
def get_list_uc(repo=Depends(get_repo)) -> ListSubscriptionsUseCase:
    return ListSubscriptionsUseCase(repo)


def get_create_uc(repo=Depends(get_repo)) -> CreateSubscriptionUseCase:
    return CreateSubscriptionUseCase(repo)


def get_update_uc(repo=Depends(get_repo)) -> UpdateSubscriptionUseCase:
    return UpdateSubscriptionUseCase(repo)


def get_delete_uc(repo=Depends(get_repo)) -> DeleteSubscriptionUseCase:
    return DeleteSubscriptionUseCase(repo)


def get_single_uc(repo=Depends(get_repo)) -> GetSubscriptionUseCase:
    return GetSubscriptionUseCase(repo)


# ── Auth use cases ──────────────────────────────────────────────────────────
def get_login_uc(repo=Depends(get_user_repo)) -> LoginUserUseCase:
    return LoginUserUseCase(repo)


def get_register_uc(repo=Depends(get_user_repo)) -> RegisterUserUseCase:
    return RegisterUserUseCase(repo)


def get_update_permissions_uc(repo=Depends(get_user_repo)) -> UpdateUserPermissionsUseCase:
    return UpdateUserPermissionsUseCase(repo)


def get_list_users_uc(repo=Depends(get_user_repo)) -> ListUsersUseCase:
    return ListUsersUseCase(repo)


def get_change_password_uc(repo=Depends(get_user_repo)) -> ChangePasswordUseCase:
    return ChangePasswordUseCase(repo)


# ── Auth guards ─────────────────────────────────────────────────────────────
def get_current_user(
    request: Request,
    repo: SqlUserRepository = Depends(get_user_repo),
) -> User:
    user_id = get_session_user_id(request)
    if not user_id:
        raise NotAuthenticatedException()
    user = repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise NotAuthenticatedException()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise ForbiddenException()
    return user


def require_create(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin" and not user.can_create:
        raise ForbiddenException()
    return user


def require_update(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin" and not user.can_update:
        raise ForbiddenException()
    return user


def require_delete(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin" and not user.can_delete:
        raise ForbiddenException()
    return user
