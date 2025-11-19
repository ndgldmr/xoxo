"""
Base repository with generic CRUD operations.
All repositories should inherit from this class.
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic repository with CRUD operations.

    Type parameters:
        - ModelType: SQLAlchemy model class
        - CreateSchemaType: Pydantic schema for creation
        - UpdateSchemaType: Pydantic schema for updates
    """

    def __init__(self, model: type[ModelType], db: AsyncSession):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Async database session
        """
        self.model = model
        self.db = db

    async def get(self, id: Any) -> Optional[ModelType]:
        """
        Get a single record by ID.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """
        return await self.db.get(self.model, id)

    async def get_multi(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        """
        Get multiple records with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record.

        Args:
            obj_in: Pydantic schema with creation data

        Returns:
            Created model instance
        """
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self, *, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
        """
        Update an existing record.

        Args:
            db_obj: Existing model instance
            obj_in: Pydantic schema or dict with update data

        Returns:
            Updated model instance
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, *, id: Any) -> Optional[ModelType]:
        """
        Delete a record by ID.

        Args:
            id: Primary key value

        Returns:
            Deleted model instance or None if not found
        """
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.commit()
        return obj

    async def exists(self, *, id: Any) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Primary key value

        Returns:
            True if record exists, False otherwise
        """
        obj = await self.get(id)
        return obj is not None
