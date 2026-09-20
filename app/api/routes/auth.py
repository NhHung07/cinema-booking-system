from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_auth_service, CurrentUser 
from app.application.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.application.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    request: RegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    user = service.register(request.email, request.password, request.full_name)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="Log in and receive a JWT")
def login(
    request: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    token = service.login(request.email, request.password)
    return TokenResponse(access_token=token)

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user",
    responses={401: {"description": "Missing or invalid Bearer token"}},
)
def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
