import { useState } from "react";
import { Upload, Youtube, FolderOpen, Globe } from "lucide-react";
import { api } from "../../lib/api";
import type { CanvasIngestResponse } from "../../lib/types";

type Tab = "upload" | "youtube" | "drive" | "canvas";

interface Props {
  courseId: string;
  onJobQueued: (jobId: string) => void;
}

export default function IngestForm({ courseId, onJobQueued }: Props) {
  const [tab, setTab] = useState<Tab>("upload");

  return (
    <div className="card">
      <div className="mb-4 flex gap-1 border-b border-gray-200">
        <TabButton active={tab === "upload"} onClick={() => setTab("upload")} icon={<Upload size={14} />} label="Upload" />
        <TabButton active={tab === "youtube"} onClick={() => setTab("youtube")} icon={<Youtube size={14} />} label="YouTube" />
        <TabButton active={tab === "drive"} onClick={() => setTab("drive")} icon={<FolderOpen size={14} />} label="Google Drive" />
        <TabButton active={tab === "canvas"} onClick={() => setTab("canvas")} icon={<Globe size={14} />} label="Canvas" />
      </div>

      {tab === "upload" && <UploadTab courseId={courseId} onQueued={onJobQueued} />}
      {tab === "youtube" && <YouTubeTab courseId={courseId} onQueued={onJobQueued} />}
      {tab === "drive" && <DriveTab courseId={courseId} onQueued={onJobQueued} />}
      {tab === "canvas" && <CanvasTab courseId={courseId} onQueued={onJobQueued} />}
    </div>
  );
}

function TabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition ${active ? "border-primary-600 text-primary-700" : "border-transparent text-gray-500 hover:text-gray-700"}`}
    >
      {icon}
      {label}
    </button>
  );
}

function UploadTab({ courseId, onQueued }: { courseId: string; onQueued: (id: string) => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.uploadFiles(courseId, files);
      onQueued(result.job_id);
      setFiles([]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <label className="block cursor-pointer rounded-md border-2 border-dashed border-gray-300 p-6 text-center hover:bg-gray-50">
        <input
          type="file"
          multiple
          accept=".pdf,.pptx,.docx"
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
          className="hidden"
        />
        <Upload size={24} className="mx-auto mb-2 text-gray-400" />
        <p className="text-sm text-gray-600">
          {files.length === 0 ? "Click to select PDF, PPTX, or DOCX files" : `${files.length} file(s) selected`}
        </p>
      </label>
      {files.length > 0 && (
        <ul className="text-xs text-gray-600">
          {files.map((f) => (
            <li key={f.name}>• {f.name}</li>
          ))}
        </ul>
      )}
      {error && <div className="rounded bg-red-50 p-2 text-xs text-red-700">{error}</div>}
      <button type="submit" disabled={files.length === 0 || submitting} className="btn-primary">
        {submitting ? "Uploading..." : "Upload & ingest"}
      </button>
    </form>
  );
}

function YouTubeTab({ courseId, onQueued }: { courseId: string; onQueued: (id: string) => void }) {
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const r = await api.ingestYoutube(courseId, url);
      onQueued(r.job_id);
      setUrl("");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div>
        <label className="label">YouTube URL</label>
        <input required value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://www.youtube.com/watch?v=..." className="input" />
      </div>
      {error && <div className="rounded bg-red-50 p-2 text-xs text-red-700">{error}</div>}
      <button type="submit" disabled={submitting} className="btn-primary">
        {submitting ? "Queuing..." : "Ingest transcript"}
      </button>
    </form>
  );
}

function DriveTab({ courseId, onQueued }: { courseId: string; onQueued: (id: string) => void }) {
  const [folderId, setFolderId] = useState("");
  const [oauthToken, setOauthToken] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const r = await api.ingestDrive(courseId, folderId, oauthToken);
      onQueued(r.job_id);
      setFolderId("");
      setOauthToken("");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div>
        <label className="label">Google Drive folder ID</label>
        <input required value={folderId} onChange={(e) => setFolderId(e.target.value)} className="input" />
      </div>
      <div>
        <label className="label">OAuth access token</label>
        <input required value={oauthToken} onChange={(e) => setOauthToken(e.target.value)} className="input font-mono text-xs" />
        <p className="mt-1 text-xs text-gray-500">Requires drive.readonly scope.</p>
      </div>
      {error && <div className="rounded bg-red-50 p-2 text-xs text-red-700">{error}</div>}
      <button type="submit" disabled={submitting} className="btn-primary">
        {submitting ? "Queuing..." : "Pull from Drive"}
      </button>
    </form>
  );
}

function CanvasTab({ courseId, onQueued }: { courseId: string; onQueued: (id: string) => void }) {
  const [domain, setDomain] = useState("");
  const [token, setToken] = useState("");
  const [canvasCourseId, setCanvasCourseId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CanvasIngestResponse | null>(null);
  const [enabling, setEnabling] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.ingestCanvas(courseId, {
        canvas_domain: domain,
        canvas_token: token,
        canvas_course_id: parseInt(canvasCourseId, 10),
      });
      setResult(r);
      onQueued(r.job_id);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const onEnableWebhooks = async () => {
    setEnabling(true);
    try {
      await api.enableCanvasWebhooks(courseId);
      setResult(result ? { ...result, webhook_compatible: false } : null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setEnabling(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div>
        <label className="label">Canvas domain</label>
        <input required value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="university.instructure.com" className="input" />
      </div>
      <div>
        <label className="label">Canvas API token</label>
        <input required value={token} onChange={(e) => setToken(e.target.value)} className="input font-mono text-xs" />
      </div>
      <div>
        <label className="label">Canvas course ID</label>
        <input required type="number" value={canvasCourseId} onChange={(e) => setCanvasCourseId(e.target.value)} className="input" />
      </div>
      {error && <div className="rounded bg-red-50 p-2 text-xs text-red-700">{error}</div>}
      <button type="submit" disabled={submitting} className="btn-primary">
        {submitting ? "Connecting..." : "Connect Canvas"}
      </button>

      {result && (
        <div className="rounded-md bg-gray-50 p-3 text-sm">
          {result.webhook_compatible ? (
            <>
              <p className="mb-2 font-medium text-emerald-700">Real-time sync available</p>
              <p className="mb-3 text-xs text-gray-600">
                Your institution supports Canvas webhooks. Enable real-time sync to push new materials instantly,
                instead of polling every 6 hours.
              </p>
              <button type="button" onClick={onEnableWebhooks} disabled={enabling} className="btn-primary">
                {enabling ? "Enabling..." : "Enable real-time sync"}
              </button>
            </>
          ) : (
            <p className="text-xs text-gray-600">
              Polling mode active — new Canvas materials will sync within 6 hours.
            </p>
          )}
        </div>
      )}
    </form>
  );
}
