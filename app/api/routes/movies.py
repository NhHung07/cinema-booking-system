import base64
from pathlib import Path
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentAdminUser, get_catalog_service
from app.application.schemas.catalog import (
    ImageUploadRequest,
    ImageUploadResponse,
    MovieCreateRequest,
    MovieResponse,
    MovieUpdateRequest,
)
from app.application.services.catalog_service import CatalogService
from app.core.exceptions import InvalidBookingError

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("", response_model=list[MovieResponse], summary="List available movies")
def list_movies(service: Annotated[CatalogService, Depends(get_catalog_service)]) -> list[MovieResponse]:
    return [MovieResponse.model_validate(movie) for movie in service.list_movies()]


@router.post(
    "/upload-image",
    response_model=ImageUploadResponse,
    summary="Upload a movie poster image (Admin only)",
)
def upload_movie_image(
    request: ImageUploadRequest,
    _: CurrentAdminUser,
) -> ImageUploadResponse:
    data = request.image_data
    if "," in data:
        _, base64_data = data.split(",", 1)
    else:
        base64_data = data

    try:
        binary_data = base64.b64decode(base64_data)
    except Exception as exc:
        raise InvalidBookingError("Dữ liệu hình ảnh không hợp lệ") from exc

    if len(binary_data) > 10 * 1024 * 1024:
        raise InvalidBookingError("Kích thước tệp ảnh vượt quá giới hạn 10MB")

    raw_ext = Path(request.filename).suffix.lower()
    if raw_ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        raw_ext = ".jpg"

    safe_name = f"{uuid.uuid4().hex}{raw_ext}"
    uploads_dir = Path("static/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / safe_name
    file_path.write_bytes(binary_data)

    return ImageUploadResponse(image_url=f"/static/uploads/{safe_name}")


@router.post(
    "",
    response_model=MovieResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new movie (Admin only)",
)
def create_movie(
    request: MovieCreateRequest,
    _: CurrentAdminUser,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> MovieResponse:
    movie = service.create_movie(
        title=request.title,
        description=request.description,
        duration_minutes=request.duration_minutes,
        release_date=request.release_date,
        poster_url=request.poster_url,
    )
    return MovieResponse.model_validate(movie)


@router.get("/{movie_id}", response_model=MovieResponse, summary="Get a movie by ID")
def get_movie(
    movie_id: int,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> MovieResponse:
    return MovieResponse.model_validate(service.get_movie(movie_id))


@router.put(
    "/{movie_id}",
    response_model=MovieResponse,
    summary="Update an existing movie (Admin only)",
)
def update_movie(
    movie_id: int,
    request: MovieUpdateRequest,
    _: CurrentAdminUser,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> MovieResponse:
    movie = service.update_movie(
        movie_id=movie_id,
        title=request.title,
        description=request.description,
        duration_minutes=request.duration_minutes,
        release_date=request.release_date,
        poster_url=request.poster_url,
    )
    return MovieResponse.model_validate(movie)


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a movie (Admin only)",
)
def delete_movie(
    movie_id: int,
    _: CurrentAdminUser,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> dict[str, str]:
    service.delete_movie(movie_id)
    return {"message": "Đã xóa phim thành công"}
