(function () {
  const form = document.getElementById("booking-form");
  if (!form) return;

  const serviceSelect = document.getElementById("id_service");
  const barberSelect = document.getElementById("id_barber");
  const dateInput = document.getElementById("id_date");
  const timeInput = document.getElementById("id_time");
  const calendarGrid = document.getElementById("calendar-grid");
  const calendarTitle = document.getElementById("calendar-title");
  const slotsNode = document.getElementById("slots");
  const submitButton = document.getElementById("submit-button");
  const summaryService = document.getElementById("summary-service");
  const summaryDate = document.getElementById("summary-date");
  const summaryTime = document.getElementById("summary-time");
  const summaryPrice = document.getElementById("summary-price");
  const availabilityUrl = form.dataset.availabilityUrl;
  const excludeId = form.dataset.excludeId;
  const serviceDataNode = document.getElementById("service-data");
  const serviceData = serviceDataNode ? JSON.parse(serviceDataNode.textContent) : {};

  const now = new Date();
  let currentYear = now.getFullYear();
  let currentMonth = now.getMonth();
  let availableDates = new Set();
  let selectedDate = form.dataset.initialDate || "";
  let selectedTime = form.dataset.initialTime || "";

  if (selectedDate) {
    const parsed = new Date(selectedDate + "T00:00:00");
    currentYear = parsed.getFullYear();
    currentMonth = parsed.getMonth();
    dateInput.value = selectedDate;
  }
  if (selectedTime) {
    timeInput.value = selectedTime.slice(0, 5);
    selectedTime = timeInput.value;
  }

  function optionText(select) {
    const option = select.options[select.selectedIndex];
    return option ? option.textContent.trim() : "";
  }

  function selectedServicePrice() {
    return serviceData[serviceSelect.value] ? serviceData[serviceSelect.value].price : "—";
  }

  function formatDate(value) {
    if (!value) return "—";
    const [year, month, day] = value.split("-");
    return `${day}.${month}.${year}`;
  }

  function updateSummary() {
    summaryService.textContent = serviceSelect.value ? optionText(serviceSelect) : "—";
    summaryDate.textContent = selectedDate ? formatDate(selectedDate) : "—";
    summaryTime.textContent = selectedTime || "—";
    summaryPrice.textContent = serviceSelect.value ? selectedServicePrice() : "—";
    submitButton.disabled = !(serviceSelect.value && barberSelect.value && selectedDate && selectedTime);
  }

  function monthName(year, month) {
    return new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" }).format(new Date(year, month, 1));
  }

  function isoDate(year, month, day) {
    const value = new Date(year, month, day);
    const yyyy = value.getFullYear();
    const mm = String(value.getMonth() + 1).padStart(2, "0");
    const dd = String(value.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  }

  function renderCalendar() {
    calendarTitle.textContent = monthName(currentYear, currentMonth);
    calendarGrid.innerHTML = "";

    const first = new Date(currentYear, currentMonth, 1);
    const startOffset = (first.getDay() + 6) % 7;
    const gridStart = new Date(currentYear, currentMonth, 1 - startOffset);

    for (let index = 0; index < 42; index += 1) {
      const day = new Date(gridStart);
      day.setDate(gridStart.getDate() + index);
      const value = isoDate(day.getFullYear(), day.getMonth(), day.getDate());
      const button = document.createElement("button");
      button.type = "button";
      button.className = "calendar-day";
      button.textContent = day.getDate();
      button.disabled = !availableDates.has(value);
      button.dataset.date = value;

      if (day.getMonth() !== currentMonth) button.classList.add("outside");
      if (availableDates.has(value)) button.classList.add("available");
      if (value === selectedDate) button.classList.add("selected");

      button.addEventListener("click", function () {
        selectedDate = value;
        selectedTime = "";
        dateInput.value = selectedDate;
        timeInput.value = "";
        renderCalendar();
        fetchSlots();
        updateSummary();
      });

      calendarGrid.appendChild(button);
    }
  }

  function renderSlots(slots) {
    slotsNode.innerHTML = "";
    if (!selectedDate) {
      slotsNode.textContent = "—";
      return;
    }
    if (!slots.length) {
      slotsNode.textContent = "Свободного времени нет";
      return;
    }

    slots.forEach(function (slot) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "slot-button";
      button.textContent = slot.label;
      if (slot.value === selectedTime) button.classList.add("selected");
      button.addEventListener("click", function () {
        selectedTime = slot.value;
        timeInput.value = selectedTime;
        renderSlots(slots);
        updateSummary();
      });
      slotsNode.appendChild(button);
    });
  }

  function availabilityParams(includeDate) {
    const params = new URLSearchParams({
      service: serviceSelect.value,
      barber: barberSelect.value,
      year: String(currentYear),
      month: String(currentMonth + 1),
    });
    if (includeDate && selectedDate) params.set("date", selectedDate);
    if (excludeId) params.set("exclude", excludeId);
    return params;
  }

  async function fetchAvailability() {
    if (!serviceSelect.value || !barberSelect.value) {
      availableDates = new Set();
      renderCalendar();
      renderSlots([]);
      updateSummary();
      return;
    }

    const response = await fetch(`${availabilityUrl}?${availabilityParams(Boolean(selectedDate))}`);
    const payload = await response.json();
    availableDates = new Set(payload.dates || []);
    if (selectedDate && !availableDates.has(selectedDate)) {
      selectedDate = "";
      selectedTime = "";
      dateInput.value = "";
      timeInput.value = "";
    }
    renderCalendar();
    renderSlots(payload.slots || []);
    updateSummary();
  }

  async function fetchSlots() {
    if (!serviceSelect.value || !barberSelect.value || !selectedDate) {
      renderSlots([]);
      return;
    }
    const response = await fetch(`${availabilityUrl}?${availabilityParams(true)}`);
    const payload = await response.json();
    renderSlots(payload.slots || []);
  }

  document.getElementById("prev-month").addEventListener("click", function () {
    currentMonth -= 1;
    if (currentMonth < 0) {
      currentMonth = 11;
      currentYear -= 1;
    }
    selectedDate = "";
    selectedTime = "";
    dateInput.value = "";
    timeInput.value = "";
    fetchAvailability();
  });

  document.getElementById("next-month").addEventListener("click", function () {
    currentMonth += 1;
    if (currentMonth > 11) {
      currentMonth = 0;
      currentYear += 1;
    }
    selectedDate = "";
    selectedTime = "";
    dateInput.value = "";
    timeInput.value = "";
    fetchAvailability();
  });

  serviceSelect.addEventListener("change", function () {
    selectedDate = "";
    selectedTime = "";
    dateInput.value = "";
    timeInput.value = "";
    fetchAvailability();
  });

  barberSelect.addEventListener("change", function () {
    selectedDate = "";
    selectedTime = "";
    dateInput.value = "";
    timeInput.value = "";
    fetchAvailability();
  });

  renderCalendar();
  fetchAvailability();
})();
