from sqlalchemy.orm import Session
from src.domain.entities.user import User
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.database.models import UserModel


class SqlUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            display_name=model.display_name,
            hashed_password=model.hashed_password,
            role=model.role,
            can_create=model.can_create,
            can_update=model.can_update,
            can_delete=model.can_delete,
            is_active=model.is_active,
            created_at=model.created_at,
            last_login_at=model.last_login_at,
            invite_token=model.invite_token,
            invite_expires_at=model.invite_expires_at,
        )

    def add(self, user: User) -> User:
        model = UserModel(
            email=user.email,
            display_name=user.display_name,
            hashed_password=user.hashed_password,
            role=user.role,
            can_create=user.can_create,
            can_update=user.can_update,
            can_delete=user.can_delete,
            invite_token=user.invite_token,
            invite_expires_at=user.invite_expires_at,
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, user_id: int) -> User | None:
        model = self._session.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        model = (
            self._session.query(UserModel)
            .filter(UserModel.email == email)
            .first()
        )
        return self._to_entity(model) if model else None

    def get_by_invite_token(self, token: str) -> User | None:
        model = (
            self._session.query(UserModel)
            .filter(UserModel.invite_token == token)
            .first()
        )
        return self._to_entity(model) if model else None

    def get_all(self) -> list[User]:
        models = (
            self._session.query(UserModel)
            .order_by(UserModel.created_at)
            .all()
        )
        return [self._to_entity(m) for m in models]

    def delete(self, user_id: int) -> None:
        model = self._session.get(UserModel, user_id)
        if model:
            self._session.delete(model)
            self._session.commit()

    def update(self, user: User) -> User:
        model = self._session.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"User {user.id} not found")
        model.display_name      = user.display_name
        model.hashed_password   = user.hashed_password
        model.role              = user.role
        model.can_create        = user.can_create
        model.can_update        = user.can_update
        model.can_delete        = user.can_delete
        model.is_active         = user.is_active
        model.last_login_at     = user.last_login_at
        model.invite_token      = user.invite_token
        model.invite_expires_at = user.invite_expires_at
        self._session.commit()
        self._session.refresh(model)
        return self._to_entity(model)
