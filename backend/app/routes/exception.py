from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import exception_controller
from app.middlewares.auth import get_current_user
from app.middlewares.rbac import require_roles
from app.models import User
from app.schemas.exception import (
    ExceptionRegisterRequest,
    ExceptionRevokeRequest,
    KeyConfigRequest,
)

router = APIRouter(tags=["exceptions"])


# ---- business primary key per dataset -------------------------------------- #
@router.get("/datasets/{dataset_id}/key-config")
def get_key_config(
    dataset_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return exception_controller.get_key_config(db, dataset_id)


@router.put("/datasets/{dataset_id}/key-config")
def set_key_config(
    dataset_id: int,
    payload: KeyConfigRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("steward", "analyst")),
):
    return exception_controller.set_key_config(request, db, user, dataset_id, payload)


# ---- approved exceptions ---------------------------------------------------- #
@router.get("/exceptions")
def list_exceptions(
    dataset_id: int | None = None,
    rule_id: int | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return exception_controller.list_exceptions(
        db,
        dataset_id=dataset_id,
        rule_id=rule_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/exceptions/summary")
def exception_summary(
    dataset_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return exception_controller.summary(db, dataset_id)


@router.get("/exceptions/{exception_id}")
def get_exception(
    exception_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return exception_controller.get_exception(db, exception_id)


@router.get("/exceptions/{exception_id}/hits")
def list_hits(
    exception_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return exception_controller.list_hits(db, exception_id)


@router.post("/exceptions")
def register_exception(
    payload: ExceptionRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("steward", "analyst")),
):
    return exception_controller.register_exception(request, db, user, payload)


@router.post("/exceptions/{exception_id}/revoke")
def revoke_exception(
    exception_id: int,
    payload: ExceptionRevokeRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("steward", "analyst")),
):
    return exception_controller.revoke_exception(request, db, user, exception_id, payload)
