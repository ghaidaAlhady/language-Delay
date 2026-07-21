"""Child profile endpoints, scoped to the authenticated parent."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_child_service, get_current_user
from app.models.user import User
from app.schemas.child import ChildCreateRequest, ChildResponse, ChildUpdateRequest
from app.services.child_service import ChildService, build_child_response

router = APIRouter(prefix="/children", tags=["children"])


@router.post("", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
async def create_child(
    payload: ChildCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    child_service: Annotated[ChildService, Depends(get_child_service)],
) -> ChildResponse:
    child = await child_service.create(user_id=current_user.id, payload=payload)
    return build_child_response(child)


@router.get("", response_model=list[ChildResponse])
async def list_children(
    current_user: Annotated[User, Depends(get_current_user)],
    child_service: Annotated[ChildService, Depends(get_child_service)],
) -> list[ChildResponse]:
    children = await child_service.list_for_user(current_user.id)
    return [build_child_response(child) for child in children]


@router.get("/{child_id}", response_model=ChildResponse)
async def get_child(
    child_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    child_service: Annotated[ChildService, Depends(get_child_service)],
) -> ChildResponse:
    child = await child_service.get_owned(child_id=child_id, user_id=current_user.id)
    return build_child_response(child)


@router.patch("/{child_id}", response_model=ChildResponse)
async def update_child(
    child_id: str,
    payload: ChildUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    child_service: Annotated[ChildService, Depends(get_child_service)],
) -> ChildResponse:
    child = await child_service.get_owned(child_id=child_id, user_id=current_user.id)
    child = await child_service.update(child=child, payload=payload)
    return build_child_response(child)


@router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_child(
    child_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    child_service: Annotated[ChildService, Depends(get_child_service)],
) -> None:
    child = await child_service.get_owned(child_id=child_id, user_id=current_user.id)
    await child_service.delete(child)
