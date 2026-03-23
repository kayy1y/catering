from datetime import timedelta
from math import ceil

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import Event, ResourceAllocation, ResourceItem, ServiceConfiguration, StaffAssignment, StaffMember


EVENT_DURATION_HOURS = 6


def get_event_window(event_datetime):
    event_start = event_datetime
    event_end = event_datetime + timedelta(hours=EVENT_DURATION_HOURS)
    return event_start, event_end


def find_conflicting_events(db: Session, event_datetime, location: str, exclude_event_id: int | None = None) -> list[Event]:
    event_start, event_end = get_event_window(event_datetime)
    query = select(Event).where(
        Event.location == location,
        Event.event_datetime < event_end,
        Event.event_datetime > event_start - timedelta(hours=EVENT_DURATION_HOURS),
    )
    if exclude_event_id:
        query = query.where(Event.id != exclude_event_id)
    return list(db.scalars(query.order_by(Event.event_datetime.asc())).all())


def build_resource_plan(db: Session, guest_count: int, service_configuration: ServiceConfiguration) -> list[dict]:
    resources = db.execute(select(ResourceItem).order_by(ResourceItem.name.asc())).scalars().all()
    return [
        {
            "resource_item_id": resource.id,
            "name": resource.name,
            "quantity": max(1, ceil(guest_count * resource.unit_per_guest * service_configuration.resource_multiplier)),
            "available": resource.total_quantity,
        }
        for resource in resources
    ]


def validate_operational_availability(db: Session, event: Event) -> list[str]:
    alerts: list[str] = []
    event_start, event_end = get_event_window(event.event_datetime)

    booked_staff = db.scalar(
        select(func.count(StaffAssignment.id)).where(
            and_(
                StaffAssignment.start_time < event_end,
                StaffAssignment.end_time > event_start,
                StaffAssignment.event_id != event.id,
            )
        )
    ) or 0

    active_staff = db.scalar(select(func.count(StaffMember.id)).where(StaffMember.is_active.is_(True))) or 0
    available_staff = max(active_staff - booked_staff, 0)
    if event.staff_required > available_staff:
        alerts.append(
            f"Personal insuficiente: disponible {available_staff}, requerido {event.staff_required}."
        )

    allocations = db.execute(
        select(ResourceAllocation, ResourceItem)
        .join(ResourceItem, ResourceAllocation.resource_item_id == ResourceItem.id)
        .where(ResourceAllocation.event_id == event.id)
    ).all()

    for allocation, resource in allocations:
        reserved = db.scalar(
            select(func.coalesce(func.sum(ResourceAllocation.quantity), 0))
            .join(Event, Event.id == ResourceAllocation.event_id)
            .where(
                ResourceAllocation.resource_item_id == resource.id,
                Event.id != event.id,
                Event.event_datetime.between(event_start - timedelta(hours=EVENT_DURATION_HOURS), event_end),
            )
        ) or 0
        available = resource.total_quantity - reserved
        if allocation.quantity > available:
            alerts.append(
                f"Recurso insuficiente: {resource.name}. Disponible {available}, solicitado {allocation.quantity}."
            )

    conflicts = find_conflicting_events(db, event.event_datetime, event.location, exclude_event_id=event.id)
    if conflicts:
        alerts.append("Conflicto de horario y lugar con otro evento registrado.")

    return alerts
