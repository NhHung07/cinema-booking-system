from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import CurrentAdminUser, get_analytics_service
from app.application.schemas.analytics import AnalyticsOverviewResponse
from app.application.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get admin dashboard analytics and overview metrics",
)
def get_analytics_overview(
    _: CurrentAdminUser,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    days: int | None = Query(
        default=7,
        ge=0,
        description="Số ngày cần thống kê (mặc định 7; 0 hoặc None là toàn thời gian)",
    ),
) -> AnalyticsOverviewResponse:
    filter_days = None if (days is None or days == 0) else days
    return service.get_overview(days=filter_days)

