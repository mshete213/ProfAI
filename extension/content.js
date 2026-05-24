const ALLOWED_EXTENSIONS = new Set([".pdf", ".pptx", ".docx"]);
const CANVAS_DOWNLOAD_RE = /\/courses\/\d+\/files\/\d+\/download/;

function parseLmsCourse(url) {
  const u = new URL(url);
  const hostname = u.hostname;
  let m;

  m = u.pathname.match(/^\/courses\/([^/]+)/);
  if (m && (hostname.endsWith(".instructure.com") || hostname.startsWith("canvas."))) {
    return { lmsDomain: hostname, lmsCourseId: m[1] };
  }

  m = u.pathname.match(/^\/ultra\/courses\/([^/]+)/);
  if (m && hostname.endsWith(".blackboard.com")) {
    return { lmsDomain: hostname, lmsCourseId: m[1] };
  }

  m = u.pathname.match(/^\/d2l\/le\/([^/]+)/);
  if (m && (hostname.endsWith(".brightspace.com") || hostname.endsWith(".d2l.com"))) {
    return { lmsDomain: hostname, lmsCourseId: m[1] };
  }

  return null;
}

function getFilenameFromUrl(url) {
  try {
    const u = new URL(url);
    const parts = u.pathname.split("/");
    return decodeURIComponent(parts[parts.length - 1]) || "file";
  } catch {
    return "file";
  }
}

function getMimeType(filename) {
  const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  const map = { ".pdf": "application/pdf", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document" };
  return map[ext] || "application/octet-stream";
}

function triggerBrowserDownload(arrayBuffer, filename, mimeType) {
  const url = URL.createObjectURL(new Blob([arrayBuffer], { type: mimeType }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function showToast(message, isError = false) {
  const host = document.createElement("div");
  const shadow = host.attachShadow({ mode: "closed" });
  shadow.innerHTML = `
    <style>
      .toast {
        position: fixed; bottom: 24px; right: 24px; z-index: 2147483647;
        background: ${isError ? "#ef4444" : "#1d4ed8"}; color: #fff;
        padding: 12px 16px; border-radius: 8px; font: 14px/1.4 sans-serif;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2); max-width: 320px;
        animation: fadein 0.2s ease;
      }
      @keyframes fadein { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:none } }
    </style>
    <div class="toast">${message}</div>
  `;
  document.body.appendChild(host);
  setTimeout(() => host.remove(), 4000);
}

function showMappingOverlay(courses, lmsContext, onSelected) {
  const host = document.createElement("div");
  const shadow = host.attachShadow({ mode: "closed" });

  const courseItems = courses.length
    ? courses.map(c => `<button class="course-btn" data-id="${c.id}" data-name="${escapeHtml(c.name)}">${escapeHtml(c.name)}</button>`).join("")
    : `<p class="empty">No courses found. Create one in ProfAI first.</p>`;

  shadow.innerHTML = `
    <style>
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      .backdrop { position:fixed; inset:0; background:rgba(0,0,0,0.5); z-index:2147483646; }
      .modal {
        position:fixed; top:50%; left:50%; transform:translate(-50%,-50%);
        z-index:2147483647; background:#fff; border-radius:12px;
        padding:24px; width:380px; max-width:90vw;
        box-shadow:0 20px 60px rgba(0,0,0,0.3); font-family:sans-serif;
      }
      .header { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
      .logo { font-size:18px; font-weight:700; color:#1d4ed8; }
      .close { background:none; border:none; cursor:pointer; font-size:18px; color:#6b7280; padding:4px; }
      .close:hover { color:#111; }
      .body { font-size:14px; color:#374151; margin-bottom:16px; line-height:1.5; }
      .body strong { color:#111; }
      .course-list { display:flex; flex-direction:column; gap:8px; max-height:240px; overflow-y:auto; }
      .course-btn {
        width:100%; text-align:left; padding:10px 14px; border:1px solid #e5e7eb;
        border-radius:8px; background:#fff; cursor:pointer; font-size:14px; color:#111;
        transition:background 0.15s, border-color 0.15s;
      }
      .course-btn:hover { background:#eff6ff; border-color:#1d4ed8; }
      .empty { font-size:14px; color:#6b7280; }
    </style>
    <div class="backdrop"></div>
    <div class="modal">
      <div class="header">
        <span class="logo">ProfAI</span>
        <button class="close" aria-label="Close">✕</button>
      </div>
      <p class="body">
        First time on this course. Which ProfAI course should files from
        <strong>${escapeHtml(lmsContext.lmsDomain)} / ${escapeHtml(lmsContext.lmsCourseId)}</strong>
        be added to?
      </p>
      <div class="course-list">${courseItems}</div>
    </div>
  `;

  document.body.appendChild(host);

  const close = () => host.remove();
  shadow.querySelector(".close").addEventListener("click", close);
  shadow.querySelector(".backdrop").addEventListener("click", close);
  shadow.querySelectorAll(".course-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      close();
      onSelected(btn.dataset.id, btn.dataset.name);
    });
  });
}

function escapeHtml(str) {
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function send(type, payload = {}) {
  if (typeof chrome === "undefined" || !chrome?.runtime?.sendMessage) {
    throw new Error("Extension context unavailable — refresh the page and try again.");
  }
  return chrome.runtime.sendMessage({ type, payload });
}

document.addEventListener("click", async (e) => {
  const link = e.target.closest("a[href]");
  if (!link) return;

  const href = link.href;
  const isCanvasDownload = CANVAS_DOWNLOAD_RE.test(new URL(href).pathname);
  const filename = getFilenameFromUrl(href);
  const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  if (!isCanvasDownload && !ALLOWED_EXTENSIONS.has(ext)) return;

  const lmsContext = parseLmsCourse(window.location.href);
  if (!lmsContext) return;

  // Don't prevent default — let the browser download normally.
  // We fetch and ingest in parallel via the background service worker.

  try {
    const settings = await send("GET_SETTINGS");
    if (settings.error === "not_configured") {
      showToast("ProfAI: paste your API key in the extension popup first.", true);
      return;
    }

    let { mapping } = await send("GET_MAPPING", lmsContext);

    if (!mapping) {
      const { courses, error } = await send("FETCH_PROFAI_COURSES");
      if (error) { showToast(`ProfAI: ${error}`, true); return; }

      await new Promise(resolve => {
        showMappingOverlay(courses, lmsContext, async (profaiCourseId, profaiCourseName) => {
          await send("SAVE_MAPPING", { ...lmsContext, profaiCourseId, profaiCourseName });
          mapping = { profaiCourseId, profaiCourseName };
          resolve();
        });
      });
    }

    if (!mapping) return;

    showToast(`Ingesting into ${mapping.profaiCourseName}…`);

    const result = await send("FETCH_AND_INGEST_FILE", {
      fileUrl: href,
      profaiCourseId: mapping.profaiCourseId,
    });

    if (result.error) {
      showToast(`ProfAI ingest failed: ${result.error}`, true);
    } else {
      showToast(`"${result.filename}" added to ${mapping.profaiCourseName}`);
    }
  } catch (err) {
    showToast(`ProfAI error: ${err.message}`, true);
  }
});
