const form = document.getElementById("travel-form");
const statusMessage = document.getElementById("status");
const submitButton = document.getElementById("submit-button");
const buttonLabel = document.getElementById("button-label");
const results = document.getElementById("results");
const startDate = document.getElementById("start-date");
const endDate = document.getElementById("end-date");

startDate.addEventListener("change", () => {
  endDate.min = startDate.value;
  if (endDate.value && endDate.value < startDate.value) {
    endDate.value = "";
  }
});

function showResult(cardId, contentId, value) {
  const card = document.getElementById(cardId);
  const content = document.getElementById(contentId);
  content.textContent = value || "";
  card.hidden = !value;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusMessage.textContent = "";
  statusMessage.classList.remove("error");

  if (endDate.value < startDate.value) {
    statusMessage.textContent = "La fecha de regreso debe ser posterior a la fecha de salida.";
    statusMessage.classList.add("error");
    return;
  }

  const formData = new FormData(form);
  const message = [
    `Quiero viajar a ${formData.get("destination")}.`,
    `Mi presupuesto aproximado es de $${formData.get("budget")} USD.`,
    `Las fechas del viaje son del ${formData.get("start_date")} al ${formData.get("end_date")}.`,
    "Sugiere vuelos, hoteles y un itinerario práctico dentro de mi presupuesto."
  ].join(" ");

  submitButton.disabled = true;
  buttonLabel.textContent = "Buscando...";
  statusMessage.textContent = "Estamos preparando tu propuesta. Esto puede tardar un momento.";
  results.hidden = true;

  try {
    const response = await fetch("/api/travel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "No se pudo completar la búsqueda. Inténtalo de nuevo.");
    }

    showResult("answer-card", "answer", data.answer);
    showResult("flights-card", "flights", data.flight_results);
    showResult("hotels-card", "hotels", data.hotel_results);
    showResult("itinerary-card", "itinerary", data.itinerary);
    results.hidden = false;
    statusMessage.textContent = "¡Tu propuesta está lista!";
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    statusMessage.textContent = error.message || "Ocurrió un error al conectar con el servidor.";
    statusMessage.classList.add("error");
  } finally {
    submitButton.disabled = false;
    buttonLabel.textContent = "Buscar mi viaje";
  }
});