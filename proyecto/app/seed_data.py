from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Allergy,
    Client,
    CuisineRegion,
    Dish,
    EventType,
    Menu,
    MenuCuisineAvailability,
    Region,
    ResourceItem,
    ServiceConfiguration,
    StaffMember,
    User,
    UserRole,
)


def seed_database(db: Session) -> dict:
    if db.scalar(select(User.id).limit(1)):
        _ensure_menu_cuisine_availability(db)
        return {"message": "La base de datos ya tiene informacion inicial."}

    admin = User(full_name="Admin Principal", email="admin@catering.com", role=UserRole.ADMIN)
    client_user = User(full_name="Cliente Demo", email="cliente@catering.com", role=UserRole.CLIENT)
    system_user = User(full_name="Sistema", email="system@catering.com", role=UserRole.SYSTEM)
    db.add_all([admin, client_user, system_user])
    db.flush()

    client = Client(user_id=client_user.id, phone="8888-0000", company_name="Eventos Demo")
    db.add(client)

    regions = [
        Region(name="Central", menu_multiplier=1.0, transport_base_cost=20),
        Region(name="Costera", menu_multiplier=1.15, transport_base_cost=40),
        Region(name="Montanosa", menu_multiplier=1.25, transport_base_cost=55),
    ]
    db.add_all(regions)

    cuisine_regions = [
        CuisineRegion(name="Japonesa", description="Sabores delicados, montaje minimalista y opciones de sushi o bowls."),
        CuisineRegion(name="Italiana", description="Pastas, panes artesanales y servicio cálido para eventos sociales."),
        CuisineRegion(name="Latinoamericana", description="Preparaciones intensas, coloridas y ideales para celebraciones amplias."),
        CuisineRegion(name="Internacional", description="Selección versátil para eventos corporativos y mixtos."),
    ]
    db.add_all(cuisine_regions)

    configurations = [
        ServiceConfiguration(name="Buffet", description="Servicio ágil con estaciones autoservicio.", staff_multiplier=1.0, resource_multiplier=1.0),
        ServiceConfiguration(name="Mesa Servida", description="Atención formal a la mesa por tiempos.", staff_multiplier=1.35, resource_multiplier=1.1),
        ServiceConfiguration(name="Cocktail", description="Formato ligero con estaciones móviles.", staff_multiplier=0.9, resource_multiplier=0.85),
    ]
    db.add_all(configurations)
    db.flush()

    event_types = [
        EventType(name="Boda", category="Social", characteristics="Servicio formal, mayor coordinación y montaje especial.", default_service_configuration_id=configurations[1].id),
        EventType(name="Cumpleaños", category="Social", characteristics="Servicio flexible, alto recambio y ambientación personalizada.", default_service_configuration_id=configurations[0].id),
        EventType(name="Corporativo", category="Empresarial", characteristics="Cronograma rígido, tiempos de servicio precisos y facturación detallada.", default_service_configuration_id=configurations[0].id),
        EventType(name="Graduación", category="Académico", characteristics="Volumen medio-alto, control de invitados y servicio dinámico.", default_service_configuration_id=configurations[2].id),
    ]
    db.add_all(event_types)

    menus = [
        Menu(name="Menu Sushi Garden", description="Sushi rolls, nigiris y estaciones japonesas.", base_price_per_person=30),
        Menu(name="Menu Trattoria", description="Pastas frescas, focaccia y antipastos italianos.", base_price_per_person=26),
        Menu(name="Menu Fusión Latina", description="Parrilla, bowls y estaciones de sabores latinoamericanos.", base_price_per_person=24),
        Menu(name="Menu Ejecutivo", description="Formato eficiente para reuniones y conferencias con cocina internacional.", base_price_per_person=22),
    ]
    db.add_all(menus)
    db.flush()

    dishes = [
        Dish(menu_id=menus[0].id, name="Maki vegetal", category="Principal", is_gluten_free=False, is_dairy_free=True, is_nut_free=True, is_vegan=True),
        Dish(menu_id=menus[0].id, name="Sashimi mixto", category="Principal", is_gluten_free=True, is_dairy_free=True, is_nut_free=True, is_vegan=False),
        Dish(menu_id=menus[1].id, name="Pasta primavera", category="Principal", is_gluten_free=False, is_dairy_free=True, is_nut_free=True, is_vegan=True),
        Dish(menu_id=menus[1].id, name="Lasaña artesanal", category="Principal", is_gluten_free=False, is_dairy_free=False, is_nut_free=True, is_vegan=False),
        Dish(menu_id=menus[2].id, name="Bowl criollo", category="Principal", is_gluten_free=True, is_dairy_free=True, is_nut_free=True, is_vegan=False),
        Dish(menu_id=menus[2].id, name="Arepitas de vegetales", category="Entrada", is_gluten_free=True, is_dairy_free=True, is_nut_free=True, is_vegan=True),
        Dish(menu_id=menus[3].id, name="Wrap vegetal", category="Principal", is_gluten_free=False, is_dairy_free=True, is_nut_free=True, is_vegan=True),
        Dish(menu_id=menus[3].id, name="Bowl de quinoa", category="Principal", is_gluten_free=True, is_dairy_free=True, is_nut_free=True, is_vegan=True),
    ]
    db.add_all(dishes)

    allergies = [Allergy(name="gluten"), Allergy(name="lactosa"), Allergy(name="nueces"), Allergy(name="vegano")]
    db.add_all(allergies)

    staff_members = [
        StaffMember(full_name="Chef Ana", role="Chef", hourly_rate=15, is_active=True),
        StaffMember(full_name="Mesero Luis", role="Servicio", hourly_rate=10, is_active=True),
        StaffMember(full_name="Mesera Maria", role="Servicio", hourly_rate=10, is_active=True),
        StaffMember(full_name="Supervisor Joel", role="Supervisor", hourly_rate=14, is_active=True),
        StaffMember(full_name="Chef Marta", role="Chef", hourly_rate=16, is_active=True),
    ]
    db.add_all(staff_members)

    resources = [
        ResourceItem(name="Platos", total_quantity=300, unit_per_guest=1.0),
        ResourceItem(name="Cubiertos", total_quantity=300, unit_per_guest=1.0),
        ResourceItem(name="Copas", total_quantity=250, unit_per_guest=1.0),
        ResourceItem(name="Manteles", total_quantity=40, unit_per_guest=0.1),
    ]
    db.add_all(resources)

    db.commit()
    _ensure_menu_cuisine_availability(db)
    return {"message": "Datos iniciales creados.", "client_id_demo": client.id, "admin_user_id": admin.id}


def _ensure_menu_cuisine_availability(db: Session) -> None:
    cuisine_regions = db.execute(select(CuisineRegion).order_by(CuisineRegion.id.asc())).scalars().all()
    menus = db.execute(select(Menu).order_by(Menu.id.asc())).scalars().all()
    if not cuisine_regions or not menus:
        return

    availability_rules = {
        "Japonesa": {"Menu Sushi Garden", "Menu Ejecutivo"},
        "Italiana": {"Menu Trattoria", "Menu Ejecutivo"},
        "Latinoamericana": {"Menu Fusión Latina", "Menu Ejecutivo"},
        "Internacional": {"Menu Ejecutivo", "Menu Sushi Garden", "Menu Trattoria", "Menu Fusión Latina"},
    }

    for cuisine_region in cuisine_regions:
        allowed_menus = availability_rules.get(cuisine_region.name, set())
        for menu in menus:
            existing = db.scalar(
                select(MenuCuisineAvailability).where(
                    MenuCuisineAvailability.cuisine_region_id == cuisine_region.id,
                    MenuCuisineAvailability.menu_id == menu.id,
                )
            )
            if existing:
                existing.is_available = menu.name in allowed_menus
                continue
            db.add(
                MenuCuisineAvailability(
                    cuisine_region_id=cuisine_region.id,
                    menu_id=menu.id,
                    is_available=menu.name in allowed_menus,
                )
            )
    db.commit()
