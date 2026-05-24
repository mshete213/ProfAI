const backendInput = document.getElementById("input-backend");
const keyInput = document.getElementById("input-key");
const saveBtn = document.getElementById("btn-save");
const statusEl = document.getElementById("status");
const mappingList = document.getElementById("mapping-list");

async function loadSettings() {
  const data = await chrome.storage.local.get("profai_settings");
  const s = data.profai_settings;
  if (s) {
    backendInput.value = s.backendUrl || "";
    keyInput.value = s.apiKey || "";
  }
}

async function loadMappings() {
  const data = await chrome.storage.local.get(null);
  const mappings = Object.entries(data).filter(([k]) => k.startsWith("mapping:")).map(([k, v]) => ({ key: k, ...v }));

  mappingList.innerHTML = "";
  if (mappings.length === 0) {
    mappingList.innerHTML = `<li class="empty">No mappings yet — browse an LMS course and click a file.</li>`;
    return;
  }

  mappings.forEach(({ key, profaiCourseName, lmsDomain, lmsCourseId }) => {
    const li = document.createElement("li");
    li.className = "mapping-item";
    li.innerHTML = `
      <div class="mapping-info">
        <div class="course">${escapeHtml(profaiCourseName)}</div>
        <div class="lms">${escapeHtml(lmsDomain)} / ${escapeHtml(lmsCourseId)}</div>
      </div>
      <button class="remove-btn" data-key="${escapeHtml(key)}" title="Remove mapping">✕</button>
    `;
    li.querySelector(".remove-btn").addEventListener("click", async (e) => {
      await chrome.storage.local.remove(e.target.dataset.key);
      loadMappings();
    });
    mappingList.appendChild(li);
  });
}

saveBtn.addEventListener("click", async () => {
  const backendUrl = backendInput.value.trim().replace(/\/$/, "");
  const apiKey = keyInput.value.trim();
  if (!backendUrl || !apiKey) {
    setStatus("Both fields are required.", true);
    return;
  }
  await chrome.storage.local.set({ profai_settings: { backendUrl, apiKey } });
  setStatus("Saved.");
});

function setStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.className = isError ? "error" : "";
  setTimeout(() => { statusEl.textContent = ""; }, 3000);
}

function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

loadSettings();
loadMappings();
