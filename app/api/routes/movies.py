from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_catalog_service
from app.application.schemas.catalog import MovieResponse
from app.application.services.catalog_service import CatalogService

router = APIRouter(prefix="/movies", tags=["Movies"])


@router.get("", response_model=list[MovieResponse], summary="List available movies")
def list_movies(service: Annotated[CatalogService, Depends(get_catalog_service)]) -> list[MovieResponse]:
    return [MovieResponse.model_validate(movie) for movie in service.list_movies()]


@router.get("/{movie_id}", response_model=MovieResponse, summary="Get a movie by ID")
def get_movie(
    movie_id: int,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> MovieResponse:
    return MovieResponse.model_validate(service.get_movie(movie_id))
