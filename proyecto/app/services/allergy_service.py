from app.models import Dish, Event


ALLERGY_FIELD_MAP = {
    "gluten": "is_gluten_free",
    "lactosa": "is_dairy_free",
    "lacteos": "is_dairy_free",
    "nueces": "is_nut_free",
    "vegano": "is_vegan",
}


def get_event_restrictions(event: Event) -> list[str]:
    return sorted(
        {
            allergy_link.allergy.name.lower()
            for guest in event.guests
            for allergy_link in guest.allergies
        }
    )


def suggest_dishes_for_event(event: Event) -> list[dict]:
    dishes: list[Dish] = event.menu.dishes
    suggestions = []
    for dish in dishes:
        compatible_allergies = []
        for restriction in get_event_restrictions(event):
            field_name = ALLERGY_FIELD_MAP.get(restriction)
            if field_name and getattr(dish, field_name):
                compatible_allergies.append(restriction)

        if compatible_allergies:
            suggestions.append(
                {
                    "dish_name": dish.name,
                    "category": dish.category,
                    "compatible_with": compatible_allergies,
                }
            )

    return suggestions


def build_adapted_dishes_by_guest(event: Event) -> list[dict]:
    dishes: list[Dish] = event.menu.dishes
    adapted = []
    for guest in event.guests:
        guest_restrictions = [link.allergy.name.lower() for link in guest.allergies]
        for restriction in guest_restrictions:
            field_name = ALLERGY_FIELD_MAP.get(restriction)
            if not field_name:
                continue
            for dish in dishes:
                if getattr(dish, field_name):
                    adapted.append(
                        {
                            "guest_name": guest.full_name,
                            "allergy_name": restriction,
                            "dish_name": dish.name,
                        }
                    )
    return adapted
