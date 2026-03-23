from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CLIENT = "CLIENT"
    SYSTEM = "SYSTEM"


class EventStatus(str, Enum):
    BORRADOR = "BORRADOR"
    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    EN_PROCESO = "EN_PROCESO"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), nullable=False)

    client_profile: Mapped["Client"] = relationship(back_populates="user", uselist=False)
    status_changes: Mapped[list["EventStatusHistory"]] = relationship(back_populates="changed_by_user")
    change_logs: Mapped[list["EventChangeLog"]] = relationship(back_populates="changed_by_user")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(120))

    user: Mapped["User"] = relationship(back_populates="client_profile")
    events: Mapped[list["Event"]] = relationship(back_populates="client")


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    menu_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    transport_base_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    events: Mapped[list["Event"]] = relationship(back_populates="region")


class CuisineRegion(Base):
    __tablename__ = "cuisine_regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    events: Mapped[list["Event"]] = relationship(back_populates="cuisine_region")
    menu_availabilities: Mapped[list["MenuCuisineAvailability"]] = relationship(back_populates="cuisine_region", cascade="all, delete-orphan")


class ServiceConfiguration(Base):
    __tablename__ = "service_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    staff_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    resource_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    event_types: Mapped[list["EventType"]] = relationship(back_populates="default_service_configuration")
    events: Mapped[list["Event"]] = relationship(back_populates="service_configuration")


class EventType(Base):
    __tablename__ = "event_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    characteristics: Mapped[str] = mapped_column(String(400), nullable=False)
    default_service_configuration_id: Mapped[int | None] = mapped_column(ForeignKey("service_configurations.id"))

    default_service_configuration: Mapped["ServiceConfiguration"] = relationship(back_populates="event_types")
    events: Mapped[list["Event"]] = relationship(back_populates="event_type")


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    base_price_per_person: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    dishes: Mapped[list["Dish"]] = relationship(back_populates="menu")
    events: Mapped[list["Event"]] = relationship(back_populates="menu")
    cuisine_availabilities: Mapped[list["MenuCuisineAvailability"]] = relationship(back_populates="menu", cascade="all, delete-orphan")


class MenuCuisineAvailability(Base):
    __tablename__ = "menu_cuisine_availabilities"
    __table_args__ = (UniqueConstraint("menu_id", "cuisine_region_id", name="uq_menu_cuisine"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id"), nullable=False)
    cuisine_region_id: Mapped[int] = mapped_column(ForeignKey("cuisine_regions.id"), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    menu: Mapped["Menu"] = relationship(back_populates="cuisine_availabilities")
    cuisine_region: Mapped["CuisineRegion"] = relationship(back_populates="menu_availabilities")


class Dish(Base):
    __tablename__ = "dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    is_gluten_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dairy_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_nut_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_vegan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    menu: Mapped["Menu"] = relationship(back_populates="dishes")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), nullable=False)
    cuisine_region_id: Mapped[int] = mapped_column(ForeignKey("cuisine_regions.id"), nullable=False)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id"), nullable=False)
    event_type_id: Mapped[int] = mapped_column(ForeignKey("event_types.id"), nullable=False)
    service_configuration_id: Mapped[int] = mapped_column(ForeignKey("service_configurations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    location: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    event_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EventStatus] = mapped_column(SqlEnum(EventStatus), default=EventStatus.BORRADOR, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime)
    food_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    transport_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    staff_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    portions_required: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    staff_required: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_operationally_viable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="events")
    region: Mapped["Region"] = relationship(back_populates="events")
    cuisine_region: Mapped["CuisineRegion"] = relationship(back_populates="events")
    menu: Mapped["Menu"] = relationship(back_populates="events")
    event_type: Mapped["EventType"] = relationship(back_populates="events")
    service_configuration: Mapped["ServiceConfiguration"] = relationship(back_populates="events")
    guests: Mapped[list["Guest"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    staff_assignments: Mapped[list["StaffAssignment"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    resource_allocations: Mapped[list["ResourceAllocation"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    status_history: Mapped[list["EventStatusHistory"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    alerts: Mapped[list["EventAlert"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    changes: Mapped[list["EventChangeLog"]] = relationship(back_populates="event", cascade="all, delete-orphan")
    adapted_dishes: Mapped[list["EventAdaptedDish"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)

    event: Mapped["Event"] = relationship(back_populates="guests")
    allergies: Mapped[list["GuestAllergy"]] = relationship(back_populates="guest", cascade="all, delete-orphan")


class Allergy(Base):
    __tablename__ = "allergies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)

    guest_links: Mapped[list["GuestAllergy"]] = relationship(back_populates="allergy")


class GuestAllergy(Base):
    __tablename__ = "guest_allergies"
    __table_args__ = (UniqueConstraint("guest_id", "allergy_id", name="uq_guest_allergy"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id"), nullable=False)
    allergy_id: Mapped[int] = mapped_column(ForeignKey("allergies.id"), nullable=False)

    guest: Mapped["Guest"] = relationship(back_populates="allergies")
    allergy: Mapped["Allergy"] = relationship(back_populates="guest_links")


class StaffMember(Base):
    __tablename__ = "staff_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assignments: Mapped[list["StaffAssignment"]] = relationship(back_populates="staff_member")


class ResourceItem(Base):
    __tablename__ = "resource_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_per_guest: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    allocations: Mapped[list["ResourceAllocation"]] = relationship(back_populates="resource_item")


class StaffAssignment(Base):
    __tablename__ = "staff_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    staff_member_id: Mapped[int] = mapped_column(ForeignKey("staff_members.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    event: Mapped["Event"] = relationship(back_populates="staff_assignments")
    staff_member: Mapped["StaffMember"] = relationship(back_populates="assignments")


class ResourceAllocation(Base):
    __tablename__ = "resource_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    resource_item_id: Mapped[int] = mapped_column(ForeignKey("resource_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    event: Mapped["Event"] = relationship(back_populates="resource_allocations")
    resource_item: Mapped["ResourceItem"] = relationship(back_populates="allocations")


class EventStatusHistory(Base):
    __tablename__ = "event_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    event: Mapped["Event"] = relationship(back_populates="status_history")
    changed_by_user: Mapped["User"] = relationship(back_populates="status_changes")


class EventChangeLog(Base):
    __tablename__ = "event_change_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(255))
    new_value: Mapped[str | None] = mapped_column(String(255))
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    event: Mapped["Event"] = relationship(back_populates="changes")
    changed_by_user: Mapped["User"] = relationship(back_populates="change_logs")


class EventAlert(Base):
    __tablename__ = "event_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[AlertLevel] = mapped_column(SqlEnum(AlertLevel), default=AlertLevel.INFO, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    event: Mapped["Event"] = relationship(back_populates="alerts")


class EventAdaptedDish(Base):
    __tablename__ = "event_adapted_dishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(120), nullable=False)
    allergy_name: Mapped[str] = mapped_column(String(80), nullable=False)
    dish_name: Mapped[str] = mapped_column(String(120), nullable=False)

    event: Mapped["Event"] = relationship(back_populates="adapted_dishes")
