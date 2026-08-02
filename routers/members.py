from fastapi import APIRouter, Depends, HTTPException

import database

from dependencies import get_organization_or_404
from schemas import MemberCreate, MemberResponse

router = APIRouter(
    prefix="/organizations/{organization_id}/members",
    tags=["members"],
    dependencies=[
        Depends(get_organization_or_404),
    ],
)


@router.get(
    "",
    response_model=list[MemberResponse],
)
def get_members(
    organization_id: int,
):
    return database.get_members(organization_id)


@router.post(
    "",
    status_code=201,
    response_model=MemberResponse,
)
def create_member(
    organization_id: int,
    member: MemberCreate,
):
    created_member = database.create_member(
        organization_id=organization_id,
        name=member.name,
    )

    if created_member is None:
        raise HTTPException(
            status_code=409,
            detail="Member name already exists",
        )

    return created_member
