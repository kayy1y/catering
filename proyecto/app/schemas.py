from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import AlertLevel, EventStatus


class GuestCreate(BaseModel):
    full_name: str
    allergies: list[str] = Field(default_factory=list)


class EventCreate(BaseModel):
    client_id: int
    region_id: int
    cuisine_region_id: int
    menu_id: int
    event_type_id: int
    service_configuration_id: int
    name: str
    description: str
    location: str
    event_datetime: datetime
    guest_count: int = Field(gt=0)
    guests: list[GuestCreate] = Field(default_factory=list)


class EventUpdate(BaseModel):
    region_id: int | None = None
    cuisine_region_id: int | None = None
    menu_id: int | None = None
    event_type_id: int | None = None
    service_configuration_id: int | None = None
    name: str | None = None
    description: str | None = None
    location: str | None = None
    event_datetime: datetime | None = None
    guest_count: int | None = Field(default=None, gt=0)
    guests: list[GuestCreate] | None = None
    changed_by_user_id: int | None = None


class EventStatusChange(BaseModel):
    changed_by_user_id: int
    new_status: EventStatus = EventStatus.CONFIRMADO


class AvailabilityResponse(BaseModel):
    available: bool
    requested_datetime: datetime
    location: str
    conflicting_events: list[dict]
    occupied_slots: list[str]


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_code: str
    name: str
    description: str
    location: str
    category: str
    cuisine_region_name: str
    event_datetime: datetime
    guest_count: int
    status: EventStatus
    food_cost: float
    transport_cost: float
    staff_cost: float
    total_estimated_cost: float
    portions_required: int
    staff_required: int
    is_operationally_viable: bool


class RegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    menu_multiplier: float
    transport_base_cost: float


class CuisineRegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    base_price_per_person: float


class ServiceConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    staff_multiplier: float
    resource_multiplier: float


class EventTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    characteristics: str
    default_service_configuration_id: int | None


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    company_name: str | None


class GuestResponse(BaseModel):
    full_name: str
    allergies: list[str]


class AlertResponse(BaseModel):
    category: str
    message: str
    level: AlertLevel
    created_at: datetime


class EventDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_code: str
    name: str
    description: str
    category: str
    location: str
    event_datetime: datetime
    guest_count: int
    status: EventStatus
    food_cost: float
    transport_cost: float
    staff_cost: float
    total_estimated_cost: float
    portions_required: int
    staff_required: int
    region_name: str
    cuisine_region_name: str
    menu_name: str
    event_type_name: str
    service_configuration_name: str
    is_operationally_viable: bool
    guests: list[GuestResponse]
    status_history: list[dict]
    change_logs: list[dict]
    adapted_dishes: list[dict]
    alerts: list[AlertResponse]


class DashboardResponse(BaseModel):
    event_code: str
    customer_view_total: float
    admin_breakdown: dict
    operational_alerts: list[str]
    adapted_menu_plan: list[dict]
    progress_updates: list[str]


class CalendarItemResponse(BaseModel):
    id: int
    event_code: str
    name: str
    category: str
    location: str
    cuisine_region_name: str
    event_datetime: datetime
    status: EventStatus
    region: str


class EventSummaryResponse(BaseModel):
    id: int
    event_code: str
    name: str
    category: str
    client_name: str
    cuisine_region_name: str
    menu_name: str
    event_datetime: datetime
    total_estimated_cost: float
    status: EventStatus
