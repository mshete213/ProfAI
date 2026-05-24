import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import useSWR, { mutate } from "swr";
import { ArrowLeft, MessageSquare } from "lucide-react";
import IngestForm from "../../components/ingest/IngestForm";
import MaterialsList from "../../components/ingest/MaterialsList";
import { api } from "../../lib/api";
import type { IngestionJob } from "../../lib/types";

export default function CourseIngest() {
  const { courseId } = useParams<{ courseId: string }>();
  const { data: course } = useSWR(courseId ? `course-${courseId}` : null, () => api.getCourse(courseId!));
  const [activeJobs, setActiveJobs] = useState<string[]>([]);

  if (!courseId) return null;

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-4 flex items-center justify-between">
        <Link to="/courses" className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
          <ArrowLeft size={14} />
          Back to courses
        </Link>
        <Link to={`/courses/${courseId}/chat`} className="inline-flex items-center gap-1.5 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700">
          <MessageSquare size={14} />
          Go to chat
        </Link>
      </div>
      <h1 className="mb-1 text-2xl font-semibold">{course?.name ?? "Loading…"}</h1>
      <p className="mb-6 text-sm text-gray-600">Add materials to this course</p>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <IngestForm courseId={courseId} onJobQueued={(id) => setActiveJobs((j) => [id, ...j])} />
          {activeJobs.map((id) => (
            <JobStatusCard key={id} jobId={id} courseId={courseId} />
          ))}
        </div>
        <MaterialsList courseId={courseId} />
      </div>
    </div>
  );
}

function JobStatusCard({ jobId, courseId }: { jobId: string; courseId: string }) {
  const [job, setJob] = useState<IngestionJob | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const j = await api.getJob(jobId);
        if (!cancelled) setJob(j);
        if (!cancelled && j.status === "completed") mutate(`materials-${courseId}`);
        if (!cancelled && j.status !== "queued" && j.status !== "running") return;
        if (!cancelled) setTimeout(poll, 1500);
      } catch {
        // ignore
      }
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [jobId, courseId]);

  if (!job) return null;
  const isDone = job.status === "completed" || job.status === "failed" || job.status === "skipped_duplicate";
  const pct = job.total_items > 0 ? Math.round((job.processed_items / job.total_items) * 100) : 0;

  return (
    <div className="card">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium">Job {jobId.slice(0, 8)}…</span>
        <span className={`rounded px-2 py-0.5 text-xs ${isDone ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
          {job.status}
        </span>
      </div>
      <div className="mb-1 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div className="h-full bg-primary-600 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-gray-500">
        {job.processed_items}/{job.total_items} processed
        {job.failed_items > 0 && ` • ${job.failed_items} failed`}
      </div>
      {job.error_message && <div className="mt-2 text-xs text-red-600">{job.error_message}</div>}
    </div>
  );
}
