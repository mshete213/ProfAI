chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message).then(sendResponse).catch(err => sendResponse({ error: err.message }));
  return true;
});

async function getSettings() {
  const data = await chrome.storage.local.get("profai_settings");
  const s = data.profai_settings;
  if (!s?.apiKey || !s?.backendUrl) throw new Error("not_configured");
  return s;
}

async function handleMessage({ type, payload }) {
  if (type === "GET_SETTINGS") {
    const data = await chrome.storage.local.get("profai_settings");
    const s = data.profai_settings;
    if (!s?.apiKey || !s?.backendUrl) return { error: "not_configured" };
    return s;
  }

  if (type === "GET_MAPPING") {
    const key = `mapping:${payload.lmsDomain}:${payload.lmsCourseId}`;
    const data = await chrome.storage.local.get(key);
    return { mapping: data[key] ?? null };
  }

  if (type === "SAVE_MAPPING") {
    const key = `mapping:${payload.lmsDomain}:${payload.lmsCourseId}`;
    await chrome.storage.local.set({
      [key]: {
        profaiCourseId: payload.profaiCourseId,
        profaiCourseName: payload.profaiCourseName,
        lmsDomain: payload.lmsDomain,
        lmsCourseId: payload.lmsCourseId,
        createdAt: new Date().toISOString(),
      },
    });
    return { ok: true };
  }

  if (type === "FETCH_PROFAI_COURSES") {
    const { apiKey, backendUrl } = await getSettings();
    const resp = await fetch(`${backendUrl}/api/v1/courses`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    if (!resp.ok) throw new Error(`Failed to fetch courses: ${resp.status}`);
    const courses = await resp.json();
    return { courses };
  }

  // Fetch the file from Canvas and ingest it in one shot — never pass
  // binary data through the content-script message channel (it corrupts).
  if (type === "FETCH_AND_INGEST_FILE") {
    const { apiKey, backendUrl } = await getSettings();
    const { fileUrl, profaiCourseId } = payload;

    const fileResp = await fetch(fileUrl, { credentials: "include" });
    if (!fileResp.ok) throw new Error(`Download failed: ${fileResp.status}`);

    const disposition = fileResp.headers.get("content-disposition") || "";
    const nameMatch = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)/i);
    const filename = nameMatch
      ? decodeURIComponent(nameMatch[1].trim())
      : decodeURIComponent((fileResp.url || fileUrl).split("/").pop().split("?")[0]) || "file";
    const mimeType = fileResp.headers.get("content-type")?.split(";")[0] || "application/octet-stream";
    const fileBlob = await fileResp.blob();

    const fd = new FormData();
    fd.append("files", fileBlob, filename);
    const ingestResp = await fetch(`${backendUrl}/api/v1/ingest/${profaiCourseId}/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${apiKey}` },
      body: fd,
    });
    if (!ingestResp.ok) {
      const text = await ingestResp.text();
      throw new Error(`Ingest failed ${ingestResp.status}: ${text}`);
    }
    const result = await ingestResp.json();
    return { ok: true, filename, jobId: result.job_id };
  }

  throw new Error(`Unknown message type: ${type}`);
}
