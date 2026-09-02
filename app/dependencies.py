from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database_session
from app.repositories import DataRepository, UserRepository
from app.services import UserService


DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]


def get_data_repository(session: DatabaseSession) -> DataRepository:
    return DataRepository(session)


DataRepositoryDependency = Annotated[DataRepository, Depends(get_data_repository)]


def get_user_repository(session: DatabaseSession) -> UserRepository:
    return UserRepository(session)


UserRepositoryDependency = Annotated[UserRepository, Depends(get_user_repository)]


def get_user_service(repository: UserRepositoryDependency) -> UserService:
    return UserService(repository)


UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
