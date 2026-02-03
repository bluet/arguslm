"""Model Management API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.model import ModelCreate, ModelListResponse, ModelResponse, ModelUpdate
from app.db.init import get_db
from app.models.model import Model, create_manual_model, update_custom_name, validate_model_id

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("", response_model=ModelListResponse)
async def list_models(
    provider_id: Optional[UUID] = Query(None, description="Filter by provider account ID"),
    enabled_for_monitoring: Optional[bool] = Query(None, description="Filter by monitoring status"),
    enabled_for_benchmark: Optional[bool] = Query(None, description="Filter by benchmark status"),
    search: Optional[str] = Query(None, description="Search in model_id and custom_name"),
    limit: int = Query(50, ge=1, le=200, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
) -> ModelListResponse:
    """List all models with optional filters.

    Supports filtering by provider, monitoring/benchmark status, and text search.
    Results are paginated with limit and offset.
    """
    # Build query
    query = select(Model)

    # Apply filters
    if provider_id:
        query = query.where(Model.provider_account_id == provider_id)

    if enabled_for_monitoring is not None:
        query = query.where(Model.enabled_for_monitoring == enabled_for_monitoring)

    if enabled_for_benchmark is not None:
        query = query.where(Model.enabled_for_benchmark == enabled_for_benchmark)

    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Model.model_id).ilike(search_pattern),
                func.lower(Model.custom_name).ilike(search_pattern),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(Model)
    if provider_id:
        count_query = count_query.where(Model.provider_account_id == provider_id)
    if enabled_for_monitoring is not None:
        count_query = count_query.where(Model.enabled_for_monitoring == enabled_for_monitoring)
    if enabled_for_benchmark is not None:
        count_query = count_query.where(Model.enabled_for_benchmark == enabled_for_benchmark)
    if search:
        search_pattern = f"%{search.lower()}%"
        count_query = count_query.where(
            or_(
                func.lower(Model.model_id).ilike(search_pattern),
                func.lower(Model.custom_name).ilike(search_pattern),
            )
        )

    total = await db.scalar(count_query)

    # Apply pagination and eager load provider_account
    query = query.options(selectinload(Model.provider_account)).offset(offset).limit(limit)

    # Execute query
    result = await db.execute(query)
    models = result.scalars().all()

    items = []
    for m in models:
        model_data = ModelResponse.model_validate(m)
        if m.provider_account:
            model_data.provider_name = (
                m.provider_account.display_name or m.provider_account.provider_type
            )
        items.append(model_data)

    return ModelListResponse(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ModelResponse:
    """Get a specific model by ID."""
    query = select(Model).where(Model.id == model_id).options(selectinload(Model.provider_account))
    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    response = ModelResponse.model_validate(model)
    if model.provider_account:
        response.provider_name = (
            model.provider_account.display_name or model.provider_account.provider_type
        )
    return response


@router.patch("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    update_data: ModelUpdate,
    db: AsyncSession = Depends(get_db),
) -> ModelResponse:
    """Update a model's custom name and enabled flags.

    Cannot update model_id (provider's identifier).
    """
    query = select(Model).where(Model.id == model_id)
    result = await db.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Update custom_name if provided (including None to clear it)
    if "custom_name" in update_data.model_dump(exclude_unset=True):
        model = await update_custom_name(db, model, update_data.custom_name)

    # Update enabled_for_monitoring if provided
    if update_data.enabled_for_monitoring is not None:
        model.enabled_for_monitoring = update_data.enabled_for_monitoring

    # Update enabled_for_benchmark if provided
    if update_data.enabled_for_benchmark is not None:
        model.enabled_for_benchmark = update_data.enabled_for_benchmark

    # Commit changes
    await db.commit()
    await db.refresh(model)

    return ModelResponse.model_validate(model)


@router.post("", response_model=ModelResponse, status_code=201)
async def create_model(
    create_data: ModelCreate,
    db: AsyncSession = Depends(get_db),
) -> ModelResponse:
    """Create a new manual model.

    Manual models are added by users and not discovered from provider APIs.
    """
    # Validate model_id format
    if not validate_model_id(create_data.model_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid model_id format. Must contain only alphanumeric characters, hyphens, and underscores.",
        )

    # Create the model
    model = await create_manual_model(
        db,
        provider_account_id=create_data.provider_account_id,
        model_id=create_data.model_id,
        custom_name=create_data.custom_name,
        metadata=create_data.metadata or {},
    )

    return ModelResponse.model_validate(model)
