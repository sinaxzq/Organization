from fastapi import APIRouter, HTTPException

import database

from dependencies import get_organization_or_404

from schemas import (
    OrganizationCreate,
    OrganizationResponse,
)


router = APIRouter(
    prefix="/organizations",
    tags=["organizations"],
)


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
def get_organization(
    organization_id: int,
):
    return get_organization_or_404(
        organization_id
    )


@router.post(
    "",
    status_code=201,
    response_model=OrganizationResponse,
)
def create_organization(organization: OrganizationCreate):
    created_organization = database.create_organization(
        organization.name
    )

    if created_organization is None:
        raise HTTPException(
            status_code=409,
            detail="Organization name already exists",
        )

    return created_organization


@router.get(
    "",
    response_model=list[OrganizationResponse],
    
)
def get_organizations():
    return database.get_organizations()