const apiBase = "/api";
const storageKey = "cateringDraft";
const eventStorageKey = "selectedEventId";

function getDraft() {
  return JSON.parse(sessionStorage.getItem(storageKey) || "{}");
}

function setDraft(nextDraft) {
  sessionStorage.setItem(storageKey, JSON.stringify(nextDraft));
}

function mergeDraft(patch) {
  const nextDraft = { ...getDraft(), ...patch };
  setDraft(nextDraft);
  return nextDraft;
}

async function request(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const rawText = await response.text();
  let data = null;

  if (rawText) {
    try {
      data = JSON.parse(rawText);
    } catch {
      data = rawText;
    }
  }

  if (!response.ok) {
    if (data && typeof data === "object" && "detail" in data) {
      throw new Error(data.detail);
    }
    throw new Error(typeof data === "string" && data ? data : "Ocurrio un error en la solicitud.");
  }
  return data ?? {};
}

function showMessage(target, text, variant = "") {
  if (!target) {
    return;
  }
  target.className = `message ${variant}`.trim();
  target.textContent = text;
}

function setApiStatus(text) {
  const apiStatus = document.getElementById("apiStatus");
  if (apiStatus) {
    apiStatus.textContent = text;
  }
}

function attachSeedButton() {
  const seedButton = document.getElementById("seedButton");
  if (!seedButton) {
    return;
  }

  seedButton.addEventListener("click", async () => {
    const feedback = document.getElementById("globalMessage");
    try {
      const data = await request("/setup/seed", { method: "POST" });
      showMessage(feedback, data.message, "success");
      setApiStatus("Conectada");
    } catch (error) {
      showMessage(feedback, error.message, "error");
    }
  });
}

function parseGuests(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [namePart, allergyPart = ""] = line.split(":");
      return {
        full_name: namePart.trim(),
        allergies: allergyPart
          .split(",")
          .map((item) => item.trim().toLowerCase())
          .filter(Boolean),
      };
    });
}

function renderOptions(select, items, labelBuilder) {
  select.innerHTML = items.map((item) => `<option value="${item.id}">${labelBuilder(item)}</option>`).join("");
}

function formatDate(dateValue) {
  return new Date(dateValue).toLocaleString("es-CR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function buildMinimumDateTime() {
  const now = new Date();
  now.setHours(now.getHours() + 73);
  return now.toISOString().slice(0, 16);
}

async function setupLandingPage() {
  const globalMessage = document.getElementById("globalMessage");
  try {
    await request("/health");
    setApiStatus("Conectada");
  } catch (error) {
    setApiStatus("Sin conexion");
    showMessage(globalMessage, error.message, "error");
  }
}

async function setupRegionsPage() {
  const regionSelect = document.getElementById("region_id");
  const cuisineRegionSelect = document.getElementById("cuisine_region_id");
  const clientSelect = document.getElementById("client_id");
  const eventTypeSelect = document.getElementById("event_type_id");
  const eventDateInput = document.getElementById("event_datetime");
  const eventNameInput = document.getElementById("event_name");
  const descriptionInput = document.getElementById("description");
  const locationInput = document.getElementById("location");
  const regionForm = document.getElementById("regionForm");
  const availabilityButton = document.getElementById("checkAvailability");
  const availabilityResult = document.getElementById("availabilityResult");
  const message = document.getElementById("pageMessage");
  const draft = getDraft();

  eventDateInput.min = buildMinimumDateTime();

  try {
    const [regions, clients, eventTypes, cuisineRegions] = await Promise.all([
      request("/regions"),
      request("/clients"),
      request("/event-types"),
      request("/cuisine-regions"),
    ]);
    renderOptions(regionSelect, regions, (region) => `${region.name} · transporte $${region.transport_base_cost}`);
    renderOptions(cuisineRegionSelect, cuisineRegions, (region) => `${region.name} · ${region.description}`);
    renderOptions(clientSelect, clients, (client) => client.company_name || `Cliente ${client.id}`);
    renderOptions(eventTypeSelect, eventTypes, (eventType) => `${eventType.name} · ${eventType.category}`);

    if (draft.region_id) {
      regionSelect.value = String(draft.region_id);
    }
    if (draft.client_id) {
      clientSelect.value = String(draft.client_id);
    }
    if (draft.event_name) {
      eventNameInput.value = draft.event_name;
    }
    if (draft.description) {
      descriptionInput.value = draft.description;
    }
    if (draft.location) {
      locationInput.value = draft.location;
    }
    if (draft.event_type_id) {
      eventTypeSelect.value = String(draft.event_type_id);
    }
    if (draft.cuisine_region_id) {
      cuisineRegionSelect.value = String(draft.cuisine_region_id);
    }
    if (draft.event_datetime) {
      eventDateInput.value = draft.event_datetime;
    }
  } catch (error) {
    showMessage(message, error.message, "error");
  }

  availabilityButton.addEventListener("click", async () => {
    if (!eventDateInput.value || !locationInput.value.trim()) {
      showMessage(availabilityResult, "Indica fecha y lugar para consultar disponibilidad.", "error");
      return;
    }
    try {
      const result = await request(`/availability?event_datetime=${encodeURIComponent(new Date(eventDateInput.value).toISOString())}&location=${encodeURIComponent(locationInput.value.trim())}`);
      if (result.available) {
        showMessage(availabilityResult, "La fecha y el lugar están disponibles.", "success");
      } else {
        showMessage(availabilityResult, `Conflicto detectado. Horarios ocupados: ${result.occupied_slots.join(" | ")}`, "error");
      }
    } catch (error) {
      showMessage(availabilityResult, error.message, "error");
    }
  });

  regionForm.addEventListener("submit", (event) => {
    event.preventDefault();
    mergeDraft({
      region_id: Number(regionSelect.value),
      cuisine_region_id: Number(cuisineRegionSelect.value),
      client_id: Number(clientSelect.value),
      event_type_id: Number(eventTypeSelect.value),
      event_name: eventNameInput.value.trim(),
      description: descriptionInput.value.trim(),
      location: locationInput.value.trim(),
      event_datetime: eventDateInput.value,
    });
    window.location.href = "/web/menu.html";
  });
}

async function setupMenuPage() {
  const menuList = document.getElementById("menuList");
  const guestCountInput = document.getElementById("guest_count");
  const serviceConfigurationSelect = document.getElementById("service_configuration_id");
  const cuisineSummary = document.getElementById("cuisineSummary");
  const continueButton = document.getElementById("continueMenu");
  const message = document.getElementById("pageMessage");
  const draft = getDraft();
  let menus = [];

  if (!draft.cuisine_region_id) {
    showMessage(message, "Primero selecciona la región gastronómica para cargar los menús correctos.", "error");
    return;
  }

  guestCountInput.value = draft.guest_count || 50;

  try {
    const [catalogMenus, serviceConfigurations, cuisineRegions] = await Promise.all([
      request(`/menus?cuisine_region_id=${draft.cuisine_region_id}`),
      request("/service-configurations"),
      request("/cuisine-regions"),
    ]);
    menus = catalogMenus;
    const selectedCuisine = cuisineRegions.find((item) => item.id === draft.cuisine_region_id);
    if (selectedCuisine) {
      showMessage(cuisineSummary, `Región gastronómica seleccionada: ${selectedCuisine.name}. Los menús mostrados pertenecen a esta cocina.`, "success");
    }
    if (draft.menu_id && !menus.some((menu) => menu.id === draft.menu_id)) {
      mergeDraft({ menu_id: null });
    }
    renderOptions(serviceConfigurationSelect, serviceConfigurations, (item) => `${item.name} · ${item.description}`);
    if (draft.service_configuration_id) {
      serviceConfigurationSelect.value = String(draft.service_configuration_id);
    }
    if (!menus.length) {
      menuList.innerHTML = "<div class='empty-state'>No hay menús disponibles para esta región. Vuelve y selecciona otra región.</div>";
      return;
    }
    menuList.innerHTML = menus
      .map(
        (menu, index) => `
          <button class="menu-card media-${index % 2 === 0 ? "service" : "buffet"} ${draft.menu_id === menu.id ? "selected" : ""}" type="button" data-menu-id="${menu.id}">
            <span>${menu.name}</span>
            <small>${menu.description}</small>
            <strong>$${menu.base_price_per_person} por persona</strong>
          </button>
        `
      )
      .join("");
  } catch (error) {
    showMessage(message, error.message, "error");
    return;
  }

  const menuButtons = menuList.querySelectorAll("[data-menu-id]");
  menuButtons.forEach((button) => {
    button.addEventListener("click", () => {
      menuButtons.forEach((item) => item.classList.remove("selected"));
      button.classList.add("selected");
      mergeDraft({ menu_id: Number(button.dataset.menuId) });
    });
  });

  continueButton.addEventListener("click", () => {
    const currentDraft = getDraft();
    if (!currentDraft.menu_id) {
      showMessage(message, "Selecciona un tipo de menu antes de continuar.", "error");
      return;
    }

    mergeDraft({ guest_count: Number(guestCountInput.value) });
    mergeDraft({ service_configuration_id: Number(serviceConfigurationSelect.value) });
    window.location.href = "/web/configuracion.html";
  });
}

async function setupConfigPage() {
  const guestsInput = document.getElementById("guest_list");
  const preferencesInput = document.getElementById("preferences");
  const continueButton = document.getElementById("continueConfig");
  const message = document.getElementById("pageMessage");
  const draft = getDraft();

  guestsInput.value = draft.guest_list || "";
  preferencesInput.value = draft.preferences || "";

  continueButton.addEventListener("click", () => {
    const guests = parseGuests(guestsInput.value);
    if (!guests.length) {
      showMessage(message, "Agrega al menos un invitado para generar sugerencias y trazabilidad.", "error");
      return;
    }

    mergeDraft({
      guest_list: guestsInput.value,
      preferences: preferencesInput.value,
      guests,
    });
    window.location.href = "/web/resumen.html";
  });
}

function renderDraftSummary() {
  const draft = getDraft();
  const summaryTarget = document.getElementById("draftSummary");
  if (!summaryTarget) {
    return;
  }

  const guestLines = draft.guests?.length
    ? `<ul class="detail-list">${draft.guests.map((guest) => `<li>${guest.full_name} · ${guest.allergies.join(", ") || "sin alergias"}</li>`).join("")}</ul>`
    : "<p class='muted'>Aun no has registrado invitados.</p>";

  summaryTarget.innerHTML = `
    <div class="summary-card">
      <span class="badge">Resumen del recorrido</span>
      <h2>${draft.event_name || "Evento sin nombre"}</h2>
      <p class="muted">${draft.event_datetime ? formatDate(draft.event_datetime) : "Fecha no definida"} · ${draft.location || "Lugar no definido"}</p>
      <div class="chip-row">
        <span class="chip">Zona logística: ${draft.region_id || "-"}</span>
        <span class="chip">Región gastronómica: ${draft.cuisine_region_id || "-"}</span>
        <span class="chip">Menu: ${draft.menu_id || "-"}</span>
        <span class="chip">Tipo: ${draft.event_type_id || "-"}</span>
        <span class="chip">Servicio: ${draft.service_configuration_id || "-"}</span>
        <span class="chip">Invitados: ${draft.guest_count || 0}</span>
      </div>
    </div>
    <div class="summary-card">
      <h3>Descripción</h3>
      <p class="muted">${draft.description || "Sin descripción registrada."}</p>
    </div>
    <div class="summary-card">
      <h3>Invitados y alergias</h3>
      ${guestLines}
    </div>
  `;
}

function getAdminId() {
  return 1;
}

async function renderEventList() {
  const eventList = document.getElementById("eventList");
  if (!eventList) {
    return;
  }

  const events = await request("/events");
  if (!events.length) {
    eventList.innerHTML = "<div class='empty-state'>Aun no hay eventos registrados en el sistema.</div>";
    return;
  }

  eventList.innerHTML = events
    .map(
      (event) => `
        <article class="event-item">
          <div>
            <span class="badge">${event.status}</span>
            <h3>${event.name}</h3>
            <p class="muted">${event.event_code} · ${event.region} · ${formatDate(event.event_datetime)}</p>
          </div>
          <button class="action-button secondary" type="button" data-open-event="${event.id}">Abrir detalle</button>
        </article>
      `
    )
    .join("");

  eventList.querySelectorAll("[data-open-event]").forEach((button) => {
    button.addEventListener("click", async () => {
      sessionStorage.setItem(eventStorageKey, button.dataset.openEvent);
      await renderSelectedEvent();
    });
  });
}

async function renderSelectedEvent() {
  const target = document.getElementById("selectedEvent");
  if (!target) {
    return;
  }

  const eventId = sessionStorage.getItem(eventStorageKey);
  if (!eventId) {
    target.innerHTML = "<div class='empty-state'>Selecciona un evento guardado para revisar su panel operativo.</div>";
    return;
  }

  try {
    const [detail, dashboard, allergy] = await Promise.all([
      request(`/events/${eventId}`),
      request(`/events/${eventId}/dashboard`),
      request(`/events/${eventId}/allergy-suggestions`),
    ]);

    target.innerHTML = `
      <div class="detail-card">
        <span class="badge">${detail.status}</span>
        <h3>${detail.name}</h3>
        <p class="muted">${detail.event_code} · ${detail.region_name} · ${detail.menu_name} · ${detail.location}</p>
        <p>${detail.description}</p>
        <div class="stats-grid">
          <div class="stat-box"><span>Total estimado</span><strong>$${dashboard.customer_view_total.toFixed(2)}</strong></div>
          <div class="stat-box"><span>Porciones</span><strong>${detail.portions_required}</strong></div>
          <div class="stat-box"><span>Invitados</span><strong>${detail.guest_count}</strong></div>
        </div>
      </div>
      <div class="detail-card">
        <h3>Desglose administrativo</h3>
        <ul class="detail-list">
          <li>Alimentos: $${dashboard.admin_breakdown.food_cost.toFixed(2)}</li>
          <li>Personal: $${dashboard.admin_breakdown.staff_cost.toFixed(2)}</li>
          <li>Transporte: $${dashboard.admin_breakdown.transport_cost.toFixed(2)}</li>
        </ul>
      </div>
      <div class="detail-card">
        <h3>Sugerencias por alergias</h3>
        ${
          detail.adapted_dishes.length
            ? `<ul class="detail-list">${detail.adapted_dishes.map((dish) => `<li>${dish.guest_name}: ${dish.dish_name} (${dish.allergy_name})</li>`).join("")}</ul>`
            : "<p class='muted'>No se generaron platillos compatibles con las restricciones registradas.</p>"
        }
      </div>
      <div class="detail-card">
        <h3>Alertas operativas</h3>
        ${
          dashboard.operational_alerts.length
            ? `<ul class="detail-list">${dashboard.operational_alerts.map((alert) => `<li>${alert}</li>`).join("")}</ul>`
            : "<p class='muted'>Sin alertas de sobrecupo o falta de recursos.</p>"
        }
      </div>
      <div class="detail-card">
        <h3>Historial de cambios</h3>
        ${
          detail.change_logs.length
            ? `<ul class="detail-list">${detail.change_logs.map((item) => `<li>${item.field_name}: ${item.old_value || "-"} → ${item.new_value || "-"} (${new Date(item.changed_at).toLocaleString("es-CR")})</li>`).join("")}</ul>`
            : "<p class='muted'>Aún no hay cambios registrados.</p>"
        }
      </div>
    `;
  } catch (error) {
    target.innerHTML = `<div class="empty-state">${error.message}</div>`;
  }
}

async function setupSummaryPage() {
  const saveButton = document.getElementById("saveEvent");
  const confirmButton = document.getElementById("confirmEvent");
  const searchClientSelect = document.getElementById("search_client_id");
  const searchEventTypeSelect = document.getElementById("search_event_type_id");
  const runHistorySearchButton = document.getElementById("runHistorySearch");
  const historyResults = document.getElementById("historyResults");
  const message = document.getElementById("pageMessage");

  renderDraftSummary();
  const [clients, eventTypes] = await Promise.all([request("/clients"), request("/event-types")]);
  renderOptions(searchClientSelect, [{ id: "", company_name: "Todos" }, ...clients], (item) => item.company_name || "Todos");
  renderOptions(searchEventTypeSelect, [{ id: "", name: "Todos" }, ...eventTypes], (item) => item.name || "Todos");
  await renderEventList();
  await renderSelectedEvent();

  saveButton.addEventListener("click", async () => {
    const draft = getDraft();
    if (!draft.client_id || !draft.region_id || !draft.menu_id || !draft.event_type_id || !draft.service_configuration_id || !draft.event_name || !draft.description || !draft.location || !draft.event_datetime || !draft.guest_count) {
      showMessage(message, "Completa las paginas anteriores antes de guardar el evento.", "error");
      return;
    }

    try {
      const created = await request("/events", {
        method: "POST",
        body: JSON.stringify({
          client_id: draft.client_id,
          region_id: draft.region_id,
          cuisine_region_id: draft.cuisine_region_id,
          menu_id: draft.menu_id,
          event_type_id: draft.event_type_id,
          service_configuration_id: draft.service_configuration_id,
          name: draft.event_name,
          description: draft.description,
          location: draft.location,
          event_datetime: new Date(draft.event_datetime).toISOString(),
          guest_count: draft.guest_count,
          guests: draft.guests || [],
        }),
      });

      sessionStorage.setItem(eventStorageKey, String(created.id));
      showMessage(message, `Evento creado con codigo ${created.event_code}.`, "success");
      await renderEventList();
      await renderSelectedEvent();
    } catch (error) {
      showMessage(message, error.message, "error");
    }
  });

  confirmButton.addEventListener("click", async () => {
    const eventId = sessionStorage.getItem(eventStorageKey);
    if (!eventId) {
      showMessage(message, "Primero guarda un evento para poder confirmarlo.", "error");
      return;
    }

    try {
      await request(`/events/${eventId}/status`, {
        method: "POST",
        body: JSON.stringify({ changed_by_user_id: getAdminId(), new_status: "CONFIRMADO" }),
      });
      showMessage(message, "Evento confirmado y bloqueado para edicion.", "success");
      await renderEventList();
      await renderSelectedEvent();
    } catch (error) {
      showMessage(message, error.message, "error");
    }
  });

  runHistorySearchButton.addEventListener("click", async () => {
    const params = new URLSearchParams();
    const code = document.getElementById("search_code").value.trim();
    if (code) {
      params.set("code", code);
    }
    if (searchClientSelect.value) {
      params.set("client_id", searchClientSelect.value);
    }
    if (searchEventTypeSelect.value) {
      params.set("event_type_id", searchEventTypeSelect.value);
    }
    params.set("historical_only", document.getElementById("historical_only").value);

    try {
      const results = await request(`/events/search?${params.toString()}`);
      if (!results.length) {
        historyResults.innerHTML = "<div class='empty-state'>No se encontraron eventos con esos criterios.</div>";
        return;
      }
      historyResults.innerHTML = results
        .map(
          (event) => `
            <article class="event-item">
              <div>
                <span class="badge">${event.status}</span>
                <h3>${event.name}</h3>
                <p class="muted">${event.event_code} · ${event.client_name} · ${event.category}</p>
                <p class="muted">${formatDate(event.event_datetime)} · $${event.total_estimated_cost.toFixed(2)}</p>
              </div>
              <button class="action-button secondary" type="button" data-open-event="${event.id}">Abrir</button>
            </article>
          `
        )
        .join("");
      historyResults.querySelectorAll("[data-open-event]").forEach((button) => {
        button.addEventListener("click", async () => {
          sessionStorage.setItem(eventStorageKey, button.dataset.openEvent);
          await renderSelectedEvent();
        });
      });
    } catch (error) {
      historyResults.innerHTML = `<div class='empty-state'>${error.message}</div>`;
    }
  });
}

async function bootstrap() {
  attachSeedButton();
  try {
    await request("/health");
    setApiStatus("Conectada");
  } catch (error) {
    setApiStatus("Sin conexion");
  }

  const page = document.body.dataset.page;
  if (page === "landing") {
    await setupLandingPage();
  } else if (page === "regions") {
    await setupRegionsPage();
  } else if (page === "menu") {
    await setupMenuPage();
  } else if (page === "config") {
    await setupConfigPage();
  } else if (page === "summary") {
    await setupSummaryPage();
  }
}

bootstrap();
