from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_database_session
from app.repositories import DataRepository


DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]


def get_data_repository(session: DatabaseSession) -> DataRepository:
    return DataRepository(session)


DataRepositoryDependency = Annotated[DataRepository, Depends(get_data_repository)]
