const form = document.getElementById("scheduleForm");
const button = document.getElementById("submitButton");
const statusPill = document.getElementById("statusPill");
const results = document.getElementById("results");
const scheduledCount = document.getElementById("scheduledCount");
const unscheduledCount = document.getElementById("unscheduledCount");
const pendingCount = document.getElementById("pendingCount");
const downloadLink = document.getElementById("downloadLink");
const loadList = document.getElementById("loadList");
const assignmentList = document.getElementById("assignmentList");
const unscheduledSection = document.getElementById("unscheduledSection");
const unscheduledList = document.getElementById("unscheduledList");

function setStatus(text, isError = false) {
  statusPill.textContent = text;
  statusPill.classList.toggle("error", isError);
}

function item(primary, secondary) {
  const node = document.createElement("div");
  node.className = "item";
  const strong = document.createElement("strong");
  strong.textContent = primary;
  const span = document.createElement("span");
  span.textContent = secondary;
  node.append(strong, span);
  return node;
}

function renderList(container, rows, emptyText) {
  container.replaceChildren();
  if (!rows.length) {
    container.append(item(emptyText, ""));
    return;
  }
  rows.forEach((row) => container.append(row));
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  button.disabled = true;
  results.hidden = true;
  setStatus("Working");

  try {
    const response = await fetch("/api/schedule", {
      method: "POST",
      body: new FormData(form),
    });
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "Unable to generate schedule.");
    }

    const summary = payload.summary;
    scheduledCount.textContent = summary.scheduled;
    unscheduledCount.textContent = summary.unscheduled;
    pendingCount.textContent = summary.pending;
    downloadLink.href = payload.downloadUrl;

    const loadRows = Object.entries(summary.assessorLoad || {}).map(([name, count]) =>
      item(name, `${count} assessment${count === 1 ? "" : "s"}`),
    );
    renderList(loadList, loadRows, "No scheduled assessor load");

    const assignmentRows = (summary.assignments || []).map((entry) =>
      item(`${entry.student} - ${entry.assessment}`, `${entry.assessor} on ${entry.date}`),
    );
    renderList(assignmentList, assignmentRows, "No generated assignments");

    const unscheduledRows = (summary.unscheduledItems || []).map((entry) =>
      item(`${entry.student} - ${entry.assessment}`, entry.reason),
    );
    unscheduledSection.hidden = unscheduledRows.length === 0;
    renderList(unscheduledList, unscheduledRows, "All pending slots were scheduled");

    results.hidden = false;
    setStatus("Complete");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    button.disabled = false;
  }
});
