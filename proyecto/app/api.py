from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client, CuisineRegion, EventType, Menu, MenuCuisineAvailability, Region, ServiceConfiguration
from app.schemas import (
    AvailabilityResponse,
    CalendarItemResponse,
    ClientResponse,
    CuisineRegionResponse,
    DashboardResponse,
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventStatusChange,
    EventSummaryResponse,
    EventTypeResponse,
    EventUpdate,
    MenuResponse,
    RegionResponse,
    ServiceConfigurationResponse,
)
from app.seed_data import seed_database
from app.services.allergy_service import suggest_dishes_for_event
from app.services.event_service import (
    change_event_status,
    check_date_availability,
    create_event,
    get_event_with_details,
    list_calendar_events,
    search_events,
    update_event,
)
from app.services.scheduler_service import validate_operational_availability

router = APIRouter(prefix="/api")


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/setup/seed")
def setup_seed(db: Session = Depends(get_db)):
    return seed_database(db)


@router.get("/regions", response_model=list[RegionResponse])
def get_regions(db: Session = Depends(get_db)):
    return db.query(Region).order_by(Region.name.asc()).all()


@router.get("/cuisine-regions", response_model=list[CuisineRegionResponse])
def get_cuisine_regions(db: Session = Depends(get_db)):
    return db.query(CuisineRegion).order_by(CuisineRegion.name.asc()).all()


@router.get("/menus", response_model=list[MenuResponse])
def get_menus(cuisine_region_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Menu).filter(Menu.is_active.is_(True))
    if cuisine_region_id is not None:
        query = (
            query.join(MenuCuisineAvailability, MenuCuisineAvailability.menu_id == Menu.id)
            .filter(
                MenuCuisineAvailability.cuisine_region_id == cuisine_region_id,
                MenuCuisineAvailability.is_available.is_(True),
            )
        )
    return query.order_by(Menu.name.asc()).all()


@router.get("/clients", response_model=list[ClientResponse])
def get_clients(db: Session = Depends(get_db)):
    return db.query(Client).order_by(Client.id.asc()).all()


@router.get("/event-types", response_model=list[EventTypeResponse])
def get_event_types(db: Session = Depends(get_db)):
    return db.query(EventType).order_by(EventType.name.asc()).all()


@router.get("/service-configurations", response_model=list[ServiceConfigurationResponse])
def get_service_configurations(db: Session = Depends(get_db)):
    return db.query(ServiceConfiguration).order_by(ServiceConfiguration.name.asc()).all()


@router.get("/availability", response_model=AvailabilityResponse)
def get_availability(
    event_datetime: datetime,
    location: str,
    db: Session = Depends(get_db),
):
    return check_date_availability(db, event_datetime, location)


@router.post("/events", response_model=EventResponse)
def post_event(payload: EventCreate, db: Session = Depends(get_db)):
    event = create_event(db, payload)
    return EventResponse(
        id=event.id,
        event_code=event.event_code,
        name=event.name,
        description=event.description,
        location=event.location,
        category=event.category,
        cuisine_region_name=event.cuisine_region.name,
        event_datetime=event.event_datetime,
        guest_count=event.guest_count,
        status=event.status,
        food_cost=event.food_cost,
        transport_cost=event.transport_cost,
        staff_cost=event.staff_cost,
        total_estimated_cost=event.total_estimated_cost,
        portions_required=event.portions_required,
        staff_required=event.staff_required,
        is_operationally_viable=event.is_operationally_viable,
    )


@router.put("/events/{event_id}", response_model=EventResponse)
def put_event(event_id: int, payload: EventUpdate, db: Session = Depends(get_db)):
    event = update_event(db, event_id, payload)
    return EventResponse(
        id=event.id,
        event_code=event.event_code,
        name=event.name,
        description=event.description,
        location=event.location,
        category=event.category,
        cuisine_region_name=event.cuisine_region.name,
        event_datetime=event.event_datetime,
        guest_count=event.guest_count,
        status=event.status,
        food_cost=event.food_cost,
        transport_cost=event.transport_cost,
        staff_cost=event.staff_cost,
        total_estimated_cost=event.total_estimated_cost,
        portions_required=event.portions_required,
        staff_required=event.staff_required,
        is_operationally_viable=event.is_operationally_viable,
    )


@router.post("/events/{event_id}/status", response_model=EventResponse)
def post_event_status(event_id: int, payload: EventStatusChange, db: Session = Depends(get_db)):
    event = change_event_status(db, event_id, payload.changed_by_user_id, payload.new_status)
    return EventResponse(
        id=event.id,
        event_code=event.event_code,
        name=event.name,
        description=event.description,
        location=event.location,
        category=event.category,
        cuisine_region_name=event.cuisine_region.name,
        event_datetime=event.event_datetime,
        guest_count=event.guest_count,
        status=event.status,
        food_cost=event.food_cost,
        transport_cost=event.transport_cost,
        staff_cost=event.staff_cost,
        total_estimated_cost=event.total_estimated_cost,
        portions_required=event.portions_required,
        staff_required=event.staff_required,
        is_operationally_viable=event.is_operationally_viable,
    )


@router.get("/events", response_model=list[CalendarItemResponse])
def get_events(
    date: datetime | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
):
    events = list_calendar_events(db, date_filter=date, category=category)
    return [
        CalendarItemResponse(
            id=event.id,
            event_code=event.event_code,
            name=event.name,
            category=event.category,
            location=event.location,
            cuisine_region_name=event.cuisine_region.name,
            event_datetime=event.event_datetime,
            status=event.status,
            region=event.region.name,
        )
        for event in events
    ]


@router.get("/events/search", response_model=list[EventSummaryResponse])
def get_event_search(
    code: str | None = None,
    client_id: int | None = None,
    event_type_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    historical_only: bool = False,
    db: Session = Depends(get_db),
):
    events = search_events(
        db,
        code=code,
        client_id=client_id,
        event_type_id=event_type_id,
        date_from=date_from,
        date_to=date_to,
        historical_only=historical_only,
    )
    return [
        EventSummaryResponse(
            id=event.id,
            event_code=event.event_code,
            name=event.name,
            category=event.category,
            client_name=event.client.user.full_name,
            cuisine_region_name=event.cuisine_region.name,
            menu_name=event.menu.name,
            event_datetime=event.event_datetime,
            total_estimated_cost=event.total_estimated_cost,
            status=event.status,
        )
        for event in events
    ]


@router.get("/events/{event_id}", response_model=EventDetailResponse)
def get_event_detail(event_id: int, db: Session = Depends(get_db)):
    event = get_event_with_details(db, event_id)
    return EventDetailResponse(
        id=event.id,
        event_code=event.event_code,
        name=event.name,
        description=event.description,
        category=event.category,
        location=event.location,
        event_datetime=event.event_datetime,
        guest_count=event.guest_count,
        status=event.status,
        food_cost=event.food_cost,
        transport_cost=event.transport_cost,
        staff_cost=event.staff_cost,
        total_estimated_cost=event.total_estimated_cost,
        portions_required=event.portions_required,
        staff_required=event.staff_required,
        region_name=event.region.name,
        cuisine_region_name=event.cuisine_region.name,
        menu_name=event.menu.name,
        event_type_name=event.event_type.name,
        service_configuration_name=event.service_configuration.name,
        is_operationally_viable=event.is_operationally_viable,
        guests=[
            {
                "full_name": guest.full_name,
                "allergies": [link.allergy.name for link in guest.allergies],
            }
            for guest in event.guests
        ],
        status_history=[
            {
                "previous_status": history.previous_status,
                "new_status": history.new_status,
                "changed_by_user_id": history.changed_by_user_id,
                "changed_at": history.changed_at.isoformat(),
            }
            for history in event.status_history
        ],
        change_logs=[
            {
                "field_name": change.field_name,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "changed_by_user_id": change.changed_by_user_id,
                "changed_at": change.changed_at.isoformat(),
            }
            for change in event.changes
        ],
        adapted_dishes=[
            {
                "guest_name": row.guest_name,
                "allergy_name": row.allergy_name,
                "dish_name": row.dish_name,
            }
            for row in event.adapted_dishes
        ],
        alerts=event.alerts,
    )


@router.get("/events/{event_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(event_id: int, db: Session = Depends(get_db)):
    event = get_event_with_details(db, event_id)
    alerts = validate_operational_availability(db, event)
    progress_updates = [
        "Registro general completado.",
        "Costos regionales calculados.",
        "Restricciones alimentarias procesadas.",
        "Agenda actualizada en orden cronológico.",
    ]
    return DashboardResponse(
        event_code=event.event_code,
        customer_view_total=event.total_estimated_cost,
        admin_breakdown={
            "food_cost": event.food_cost,
            "staff_cost": event.staff_cost,
            "transport_cost": event.transport_cost,
            "portions_required": event.portions_required,
            "staff_required": event.staff_required,
            "viable": event.is_operationally_viable,
        },
        operational_alerts=alerts,
        adapted_menu_plan=[
            {
                "guest_name": item.guest_name,
                "allergy_name": item.allergy_name,
                "dish_name": item.dish_name,
            }
            for item in event.adapted_dishes
        ],
        progress_updates=progress_updates,
    )


@router.get("/events/{event_id}/allergy-suggestions")
def get_allergy_suggestions(event_id: int, db: Session = Depends(get_db)):
    event = get_event_with_details(db, event_id)
    return {
        "event_code": event.event_code,
        "restrictions": sorted({item.allergy_name for item in event.adapted_dishes}),
        "suggested_dishes": suggest_dishes_for_event(event),
    }
