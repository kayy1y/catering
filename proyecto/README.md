# Plataforma de Catering

Proyecto base en Python para una plataforma integral de catering, pensado para abrirse en Visual Studio o Visual Studio Code.

## Stack tecnológico propuesto

- Backend: FastAPI
- ORM: SQLAlchemy
- Base de datos relacional: SQLite para desarrollo y PostgreSQL para producción
- Validaciones: Pydantic
- Frontend sugerido: React o Vue consumiendo la API
- Despliegue sugerido: Docker + Nginx + PostgreSQL

## Roles del sistema

- Administrador: controla eventos, menús, recursos, personal y confirma eventos
- Cliente: crea solicitudes, consulta costos, invitados y estado
- Sistema: recalcula costos, valida reglas y registra trazabilidad

## Módulos principales

- Gestión de Eventos
- Inventario y Menú
- Logística de Personal y Recursos
- Facturación
- Alergias e invitados

## Reglas de negocio implementadas

- No se puede registrar un evento con menos de 72 horas de anticipación
- Cada evento genera un identificador alfanumérico único automático
- Todo evento inicia como `BORRADOR` o `PENDIENTE`
- Si el administrador cambia el estado a `CONFIRMADO`, el evento queda bloqueado para edición
- Los costos del menú y transporte se recalculan por región
- Las porciones se calculan automáticamente según la cantidad de invitados
- Se guarda el historial de cambios de estado con usuario y fecha

## Estructura de base de datos

### Tabla `users`

- `id` PK
- `full_name`
- `email` único
- `role` (`ADMIN`, `CLIENT`, `SYSTEM`)

### Tabla `regions`

- `id` PK
- `name` único
- `menu_multiplier`
- `transport_base_cost`

### Tabla `clients`

- `id` PK
- `user_id` FK -> `users.id`
- `phone`
- `company_name`

### Tabla `menus`

- `id` PK
- `name`
- `description`
- `base_price_per_person`
- `is_active`

### Tabla `dishes`

- `id` PK
- `menu_id` FK -> `menus.id`
- `name`
- `category`
- `is_gluten_free`
- `is_dairy_free`
- `is_nut_free`
- `is_vegan`

### Tabla `events`

- `id` PK
- `event_code` único
- `client_id` FK -> `clients.id`
- `region_id` FK -> `regions.id`
- `menu_id` FK -> `menus.id`
- `name`
- `event_datetime`
- `guest_count`
- `status`
- `locked_at`
- `food_cost`
- `transport_cost`
- `staff_cost`
- `total_estimated_cost`
- `portions_required`
- `created_at`
- `updated_at`

### Tabla `guests`

- `id` PK
- `event_id` FK -> `events.id`
- `full_name`

### Tabla `allergies`

- `id` PK
- `name` único

### Tabla `guest_allergies`

- `guest_id` FK -> `guests.id`
- `allergy_id` FK -> `allergies.id`

### Tabla `staff_members`

- `id` PK
- `full_name`
- `role`
- `hourly_rate`
- `is_active`

### Tabla `resource_items`

- `id` PK
- `name`
- `total_quantity`

### Tabla `staff_assignments`

- `id` PK
- `event_id` FK -> `events.id`
- `staff_member_id` FK -> `staff_members.id`
- `start_time`
- `end_time`

### Tabla `resource_allocations`

- `id` PK
- `event_id` FK -> `events.id`
- `resource_item_id` FK -> `resource_items.id`
- `quantity`

### Tabla `event_status_history`

- `id` PK
- `event_id` FK -> `events.id`
- `previous_status`
- `new_status`
- `changed_by_user_id` FK -> `users.id`
- `changed_at`

## Relaciones clave

- Un `user` puede ser un `client`
- Un `client` tiene muchos `events`
- Un `event` pertenece a una `region` y a un `menu`
- Un `menu` tiene muchos `dishes`
- Un `event` tiene muchos `guests`
- Un `guest` puede tener muchas `allergies`
- Un `event` tiene asignaciones de personal y recursos
- Un `event` tiene historial de estados

## Flujo lógico: validación de fechas

1. El cliente envía la fecha y hora del evento
2. El sistema calcula la diferencia entre la fecha actual y la fecha del evento
3. Si la diferencia es menor a 72 horas, rechaza el registro
4. Si es válida, genera el código alfanumérico único
5. Crea el evento en estado `BORRADOR`

## Flujo lógico: cálculo de costos por región

1. El sistema obtiene el menú elegido y su precio base por persona
2. Multiplica el costo base por la cantidad de invitados
3. Consulta la región del evento
4. Aplica el multiplicador regional al costo del menú
5. Suma el costo de transporte base de la región
6. Calcula personal requerido según invitados
7. Calcula costo de personal según tarifa por hora
8. Guarda el desglose y el total estimado

## Cómo ejecutar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Luego abre:

- API: `http://127.0.0.1:8000/docs`
- Web: `http://127.0.0.1:8000/web`

## Endpoints principales

- `GET /` estado del sistema
- `GET /api/health`
- `POST /api/setup/seed` datos iniciales
- `GET /api/clients`
- `GET /api/regions`
- `GET /api/menus`
- `POST /api/events`
- `PUT /api/events/{event_id}`
- `POST /api/events/{event_id}/confirm`
- `GET /api/events`
- `GET /api/events/{event_id}`
- `GET /api/events/{event_id}/dashboard`
- `GET /api/events/{event_id}/allergy-suggestions`
