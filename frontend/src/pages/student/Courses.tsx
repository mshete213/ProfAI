import { useState } from "react";
import { Link } from "react-router-dom";
import useSWR, { mutate } from "swr";
import { MessageSquare, Plus } from "lucide-react";
import { api } from "../../lib/api";

export default function StudentCourses() {
  const { data: courses, isLoading } = useSWR("/api/v1/courses", api.listCourses);
  const [showEnroll, setShowEnroll] = useState(false);
  const [courseId, setCourseId] = useState("");
  const [enrolling, setEnrolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    setEnrolling(true);
    setError(null);
    try {
      await api.enrollInCourse(courseId);
      setCourseId("");
      setShowEnroll(false);
      mutate("/api/v1/courses");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setEnrolling(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your courses</h1>
        <button onClick={() => setShowEnroll(!showEnroll)} className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          Enroll
        </button>
      </div>

      {showEnroll && (
        <form onSubmit={onEnroll} className="card mb-6 space-y-3">
          <div>
            <label className="label">Course ID</label>
            <input
              required
              value={courseId}
              onChange={(e) => setCourseId(e.target.value)}
              placeholder="paste the course UUID provided by your professor"
              className="input font-mono text-sm"
            />
          </div>
          {error && <div className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</div>}
          <button type="submit" disabled={enrolling} className="btn-primary">
            {enrolling ? "Enrolling..." : "Enroll"}
          </button>
        </form>
      )}

      {isLoading && <div className="text-gray-500">Loading…</div>}
      {courses && courses.length === 0 && !isLoading && (
        <div className="card text-center text-gray-500">You're not enrolled in any courses yet.</div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {courses?.map((c) => (
          <div key={c.id} className="card">
            <h2 className="mb-1 font-semibold">{c.name}</h2>
            <p className="mb-4 line-clamp-2 text-sm text-gray-600">{c.description || "No description"}</p>
            <Link to={`/student/courses/${c.id}/chat`} className="btn-primary flex w-full items-center justify-center gap-2">
              <MessageSquare size={14} />
              Open chat
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
