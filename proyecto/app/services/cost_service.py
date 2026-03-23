from math import ceil

from app.models import Menu, Region, ServiceConfiguration


SERVICE_HOURS_PER_EVENT = 6


def calculate_portions(guest_count: int) -> int:
    return ceil(guest_count * 1.1)


def calculate_staff_required(guest_count: int, service_configuration: ServiceConfiguration) -> int:
    return max(2, ceil((guest_count / 25) * service_configuration.staff_multiplier))


def calculate_costs(
    menu: Menu,
    region: Region,
    guest_count: int,
    service_configuration: ServiceConfiguration,
    average_hourly_rate: float = 12.5,
) -> dict:
    portions_required = calculate_portions(guest_count)
    food_cost = menu.base_price_per_person * guest_count * region.menu_multiplier
    staff_required = calculate_staff_required(guest_count, service_configuration)
    staff_cost = staff_required * average_hourly_rate * SERVICE_HOURS_PER_EVENT
    transport_cost = region.transport_base_cost
    total_estimated_cost = round(food_cost + staff_cost + transport_cost, 2)

    return {
        "food_cost": round(food_cost, 2),
        "transport_cost": round(transport_cost, 2),
        "staff_cost": round(staff_cost, 2),
        "total_estimated_cost": total_estimated_cost,
        "portions_required": portions_required,
        "staff_required": staff_required,
    }
