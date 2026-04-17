from fastapi import Depends
from sqlalchemy.orm import Session
from src.infrastructure.database.session import SessionLocal
from src.infrastructure.database.sql_subscription_repository import SqlSubscriptionRepository
from src.application.use_cases.create_subscription import CreateSubscriptionUseCase
from src.application.use_cases.update_subscription import UpdateSubscriptionUseCase
from src.application.use_cases.delete_subscription import DeleteSubscriptionUseCase
from src.application.use_cases.get_subscription import GetSubscriptionUseCase
from src.application.use_cases.list_subscriptions import ListSubscriptionsUseCase


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_repo(session: Session = Depends(get_session)) -> SqlSubscriptionRepository:
    return SqlSubscriptionRepository(session)


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
