import { useState } from "react";
import { Link } from "react-router-dom";
import useSWR, { mutate } from "swr";
import { FileText, Plus, Users, Wand2 } from "lucide-react";
import { api } from "../../lib/api";

export default function Dashboard() {
  const { data: courses, isLoading } = useSWR("/api/v1/courses", api.listCourses);
  const [showNew, setShowNew] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.createCourse({ name, description });
      setName("");
      setDescription("");
      setShowNew(false);
      mutate("/api/v1/courses");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your courses</h1>
        <button onClick={() => setShowNew(!showNew)} className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          New course
        </button>
      </div>

      {showNew && (
        <form onSubmit={onCreate} className="card mb-6 space-y-3">
          <div>
            <label className="label">Course name</label>
            <input required value={name} onChange={(e) => setName(e.target.value)} className="input" />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input"
            />
          </div>
          <button type="submit" disabled={creating} className="btn-primary">
            {creating ? "Creating..." : "Create"}
          </button>
        </form>
      )}

      {isLoading && <div className="text-gray-500">Loading…</div>}

      {courses && courses.length === 0 && !isLoading && (
        <div className="card text-center text-gray-500">No courses yet. Create your first one above.</div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {courses?.map((course) => (
          <div key={course.id} className="card flex flex-col">
            <h2 className="mb-1 font-semibold">{course.name}</h2>
            <p className="mb-4 line-clamp-2 text-sm text-gray-600">{course.description || "No description"}</p>
            <div className="mt-auto flex items-center gap-3 text-xs text-gray-500">
              <span className="flex items-center gap-1">
                <FileText size={12} /> {course.document_count ?? 0} docs
              </span>
              <span className="flex items-center gap-1">
                <Users size={12} /> {course.enrollment_count ?? 0} students
              </span>
            </div>
            <div className="mt-4 flex gap-2">
              <Link to={`/professor/courses/${course.id}/ingest`} className="btn-secondary flex-1">
                Materials
              </Link>
              <Link
                to={`/professor/courses/${course.id}/style`}
                className="btn-secondary flex items-center gap-1"
                title="Style instructions"
              >
                <Wand2 size={14} />
              </Link>
            </div>
            <code className="mt-3 truncate text-[10px] text-gray-400" title={course.id}>
              {course.id}
            </code>
          </div>
        ))}
      </div>
    </div>
  );
}
