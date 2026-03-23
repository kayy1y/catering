import random
import string
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AlertLevel,
    Allergy,
    Client,
    CuisineRegion,
    Event,
    EventAdaptedDish,
    EventAlert,
    EventChangeLog,
    EventStatus,
    EventStatusHistory,
    EventType,
    Guest,
    GuestAllergy,
    Menu,
    MenuCuisineAvailability,
    Region,
    ResourceAllocation,
    ResourceItem,
    ServiceConfiguration,
    StaffMember,
    User,
    UserRole,
)
from app.schemas import EventCreate, EventUpdate
from app.services.allergy_service import build_adapted_dishes_by_guest
from app.services.cost_service import calculate_costs
from app.services.scheduler_service import build_resource_plan, find_conflicting_events, validate_operational_availability


MINIMUM_NOTICE_HOURS = 72
TRACKED_FIELDS = [
    "name",
    "description",
    "location",
    "event_datetime",
    "guest_count",
    "region_id",
    "cuisine_region_id",
    "menu_id",
    "event_type_id",
    "service_configuration_id",
]


def normalize_to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def generate_event_code(db: Session, length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(alphabet, k=length))
        exists = db.scalar(select(Event.id).where(Event.event_code == code))
        if not exists:
            return code


def validate_event_date(event_datetime: datetime) -> None:
    normalized_event_datetime = normalize_to_utc_naive(event_datetime)
    limit = datetime.utcnow() + timedelta(hours=MINIMUM_NOTICE_HOURS)
    if normalized_event_datetime < limit:
        raise HTTPException(status_code=400, detail="El evento debe registrarse con al menos 72 horas de anticipacion.")


def ensure_editable(event: Event) -> None:
    if event.status == EventStatus.CONFIRMADO:
        raise HTTPException(status_code=403, detail="El evento ya fue confirmado y no puede editarse.")


def _get_average_hourly_rate(db: Session) -> float:
    average_rate = db.scalar(select(func.avg(StaffMember.hourly_rate)).where(StaffMember.is_active.is_(True)))
    return float(average_rate or 12.5)


def _append_alert(db: Session, event: Event, category: str, message: str, level: AlertLevel = AlertLevel.INFO) -> None:
    db.add(EventAlert(event_id=event.id, category=category, message=message, level=level))


def _sync_guests(db: Session, event: Event, guest_inputs) -> None:
    event.guests.clear()
    db.flush()
    for guest_input in guest_inputs:
        guest = Guest(event_id=event.id, full_name=guest_input.full_name)
        db.add(guest)
        db.flush()
        for allergy_name in guest_input.allergies:
            allergy = db.scalar(select(Allergy).where(Allergy.name == allergy_name.lower()))
            if not allergy:
                allergy = Allergy(name=allergy_name.lower())
                db.add(allergy)
                db.flush()
            db.add(GuestAllergy(guest_id=guest.id, allergy_id=allergy.id))


def _sync_resource_allocations(db: Session, event: Event, service_configuration: ServiceConfiguration) -> None:
    event.resource_allocations.clear()
    db.flush()
    for resource_plan in build_resource_plan(db, event.guest_count, service_configuration):
        db.add(
            ResourceAllocation(
                event_id=event.id,
                resource_item_id=resource_plan["resource_item_id"],
                quantity=resource_plan["quantity"],
            )
        )


def _sync_adapted_dishes(db: Session, event: Event) -> None:
    event.adapted_dishes.clear()
    db.flush()
    for row in build_adapted_dishes_by_guest(event):
        db.add(
            EventAdaptedDish(
                event_id=event.id,
                guest_name=row["guest_name"],
                allergy_name=row["allergy_name"],
                dish_name=row["dish_name"],
            )
        )


def _log_field_changes(db: Session, event: Event, previous_values: dict, changed_by_user_id: int | None = None) -> None:
    for field_name in TRACKED_FIELDS:
        old_value = previous_values.get(field_name)
        new_value = getattr(event, field_name)
        if field_name == "event_datetime" and isinstance(new_value, datetime):
            new_value = new_value.isoformat()
        if field_name == "event_datetime" and isinstance(old_value, datetime):
            old_value = old_value.isoformat()
        if str(old_value) != str(new_value):
            db.add(
                EventChangeLog(
                    event_id=event.id,
                    field_name=field_name,
                    old_value=None if old_value is None else str(old_value),
                    new_value=None if new_value is None else str(new_value),
                    changed_by_user_id=changed_by_user_id,
                )
            )


def _validate_dependencies(db: Session, payload) -> tuple[Client, Region, CuisineRegion, Menu, EventType, ServiceConfiguration]:
    client = db.get(Client, payload.client_id)
    region = db.get(Region, payload.region_id)
    cuisine_region = db.get(CuisineRegion, payload.cuisine_region_id)
    menu = db.get(Menu, payload.menu_id)
    event_type = db.get(EventType, payload.event_type_id)
    service_configuration = db.get(ServiceConfiguration, payload.service_configuration_id)
    if not client or not region or not cuisine_region or not menu or not event_type or not service_configuration:
        raise HTTPException(status_code=404, detail="Faltan datos relacionados del evento.")
    is_menu_available = db.scalar(
        select(MenuCuisineAvailability.id).where(
            MenuCuisineAvailability.cuisine_region_id == cuisine_region.id,
            MenuCuisineAvailability.menu_id == menu.id,
            MenuCuisineAvailability.is_available.is_(True),
        )
    )
    if not is_menu_available:
        raise HTTPException(status_code=400, detail="El menú seleccionado no está disponible para la región gastronómica elegida.")
    return client, region, cuisine_region, menu, event_type, service_configuration


def _assert_no_location_conflicts(db: Session, event_datetime: datetime, location: str, exclude_event_id: int | None = None) -> None:
    conflicts = find_conflicting_events(db, normalize_to_utc_naive(event_datetime), location, exclude_event_id=exclude_event_id)
    if conflicts:
        schedules = ", ".join(f"{item.name} ({item.event_datetime.isoformat(sep=' ', timespec='minutes')})" for item in conflicts)
        raise HTTPException(status_code=409, detail=f"Conflicto de horario en la ubicación seleccionada. Ocupado por: {schedules}.")


def create_event(db: Session, payload: EventCreate) -> Event:
    validate_event_date(payload.event_datetime)
    _, region, cuisine_region, menu, event_type, service_configuration = _validate_dependencies(db, payload)
    _assert_no_location_conflicts(db, payload.event_datetime, payload.location)

    costs = calculate_costs(
        menu,
        region,
        payload.guest_count,
        service_configuration,
        average_hourly_rate=_get_average_hourly_rate(db),
    )
    event = Event(
        event_code=generate_event_code(db),
        client_id=payload.client_id,
        region_id=payload.region_id,
        cuisine_region_id=payload.cuisine_region_id,
        menu_id=payload.menu_id,
        event_type_id=payload.event_type_id,
        service_configuration_id=payload.service_configuration_id,
        name=payload.name,
        description=payload.description,
        category=event_type.category,
        location=payload.location,
        event_datetime=normalize_to_utc_naive(payload.event_datetime),
        guest_count=payload.guest_count,
        status=EventStatus.BORRADOR,
        food_cost=costs["food_cost"],
        transport_cost=costs["transport_cost"],
        staff_cost=costs["staff_cost"],
        total_estimated_cost=costs["total_estimated_cost"],
        portions_required=costs["portions_required"],
        staff_required=costs["staff_required"],
    )
    db.add(event)
    db.flush()

    _sync_guests(db, event, payload.guests)
    db.refresh(event)
    _sync_resource_allocations(db, event, service_configuration)
    db.refresh(event)
    _sync_adapted_dishes(db, event)
    db.flush()

    alerts = validate_operational_availability(db, event)
    event.is_operationally_viable = not alerts
    _append_alert(db, event, "registro", "Evento registrado en borrador.", AlertLevel.INFO)
    _append_alert(db, event, "agenda", "Evento agregado a la agenda cronológica.", AlertLevel.INFO)
    for message in alerts:
        _append_alert(db, event, "operacion", message, AlertLevel.WARNING)

    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, event_id: int, payload: EventUpdate) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado.")

    ensure_editable(event)
    previous_values = {field_name: getattr(event, field_name) for field_name in TRACKED_FIELDS}

    if payload.event_datetime:
        validate_event_date(payload.event_datetime)
    if payload.location and (payload.location != event.location or payload.event_datetime):
        _assert_no_location_conflicts(db, payload.event_datetime or event.event_datetime, payload.location, exclude_event_id=event.id)
    elif payload.event_datetime:
        _assert_no_location_conflicts(db, payload.event_datetime, event.location, exclude_event_id=event.id)

    for field_name in ["name", "description", "location", "guest_count", "region_id", "cuisine_region_id", "menu_id", "event_type_id", "service_configuration_id"]:
        value = getattr(payload, field_name)
        if value is not None:
            setattr(event, field_name, value)
    if payload.event_datetime:
        event.event_datetime = normalize_to_utc_naive(payload.event_datetime)
    if payload.guests is not None:
        _sync_guests(db, event, payload.guests)

    fake_payload = type(
        "EventValidationPayload",
        (),
        {
            "client_id": event.client_id,
            "region_id": event.region_id,
            "cuisine_region_id": event.cuisine_region_id,
            "menu_id": event.menu_id,
            "event_type_id": event.event_type_id,
            "service_configuration_id": event.service_configuration_id,
        },
    )()
    _, region, cuisine_region, menu, event_type, service_configuration = _validate_dependencies(db, fake_payload)
    event.category = event_type.category

    costs = calculate_costs(
        menu,
        region,
        event.guest_count,
        service_configuration,
        average_hourly_rate=_get_average_hourly_rate(db),
    )
    event.food_cost = costs["food_cost"]
    event.transport_cost = costs["transport_cost"]
    event.staff_cost = costs["staff_cost"]
    event.total_estimated_cost = costs["total_estimated_cost"]
    event.portions_required = costs["portions_required"]
    event.staff_required = costs["staff_required"]

    _sync_resource_allocations(db, event, service_configuration)
    db.refresh(event)
    _sync_adapted_dishes(db, event)
    db.flush()

    alerts = validate_operational_availability(db, event)
    event.is_operationally_viable = not alerts
    _log_field_changes(db, event, previous_values, payload.changed_by_user_id)
    _append_alert(db, event, "actualizacion", "El evento fue actualizado y recalculado automáticamente.", AlertLevel.INFO)
    for message in alerts:
        _append_alert(db, event, "operacion", message, AlertLevel.WARNING)

    if event.status == EventStatus.BORRADOR:
        event.status = EventStatus.PENDIENTE

    db.commit()
    db.refresh(event)
    return event


def change_event_status(db: Session, event_id: int, changed_by_user_id: int, new_status: EventStatus) -> Event:
    event = db.get(Event, event_id)
    user = db.get(User, changed_by_user_id)

    if not event or not user:
        raise HTTPException(status_code=404, detail="Evento o usuario no encontrado.")
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo un administrador puede cambiar estados.")
    if new_status == EventStatus.CONFIRMADO and not event.is_operationally_viable:
        raise HTTPException(status_code=409, detail="No se puede confirmar un evento sin capacidad operativa suficiente.")

    previous_status = event.status.value
    event.status = new_status
    if new_status == EventStatus.CONFIRMADO:
        event.locked_at = datetime.utcnow()

    db.add(
        EventStatusHistory(
            event_id=event.id,
            previous_status=previous_status,
            new_status=new_status.value,
            changed_by_user_id=changed_by_user_id,
        )
    )
    _append_alert(db, event, "estado", f"El estado del evento cambió a {new_status.value}.", AlertLevel.INFO)
    db.commit()
    db.refresh(event)
    return event


def list_calendar_events(db: Session, date_filter: datetime | None = None, category: str | None = None) -> list[Event]:
    query = select(Event).options(selectinload(Event.region), selectinload(Event.cuisine_region)).order_by(Event.event_datetime.asc())
    if date_filter:
        start = date_filter.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        query = query.where(Event.event_datetime >= start, Event.event_datetime < end)
    if category:
        query = query.where(Event.category == category)
    return list(db.scalars(query).all())


def search_events(
    db: Session,
    code: str | None = None,
    client_id: int | None = None,
    event_type_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    historical_only: bool = False,
) -> list[Event]:
    query = (
        select(Event)
        .options(selectinload(Event.client).selectinload(Client.user), selectinload(Event.menu))
        .order_by(Event.event_datetime.desc())
    )
    if code:
        query = query.where(Event.event_code == code.upper())
    if client_id:
        query = query.where(Event.client_id == client_id)
    if event_type_id:
        query = query.where(Event.event_type_id == event_type_id)
    if date_from:
        query = query.where(Event.event_datetime >= normalize_to_utc_naive(date_from))
    if date_to:
        query = query.where(Event.event_datetime <= normalize_to_utc_naive(date_to))
    if historical_only:
        query = query.where(Event.event_datetime < datetime.utcnow())
    return list(db.scalars(query).all())


def get_event_with_details(db: Session, event_id: int) -> Event:
    query = (
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.client).selectinload(Client.user),
            selectinload(Event.region),
            selectinload(Event.cuisine_region),
            selectinload(Event.menu).selectinload(Menu.dishes),
            selectinload(Event.event_type),
            selectinload(Event.service_configuration),
            selectinload(Event.guests).selectinload(Guest.allergies).selectinload(GuestAllergy.allergy),
            selectinload(Event.status_history),
            selectinload(Event.alerts),
            selectinload(Event.changes),
            selectinload(Event.adapted_dishes),
        )
    )
    event = db.scalar(query)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado.")
    return event


def check_date_availability(db: Session, event_datetime: datetime, location: str) -> dict:
    normalized = normalize_to_utc_naive(event_datetime)
    conflicts = find_conflicting_events(db, normalized, location)
    return {
        "available": not conflicts,
        "requested_datetime": normalized,
        "location": location,
        "conflicting_events": [
            {
                "event_code": event.event_code,
                "name": event.name,
                "event_datetime": event.event_datetime.isoformat(),
            }
            for event in conflicts
        ],
        "occupied_slots": [event.event_datetime.isoformat(sep=" ", timespec="minutes") for event in conflicts],
    }
