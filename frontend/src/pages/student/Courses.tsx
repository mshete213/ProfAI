import { Link } from "react-router-dom";
import useSWR from "swr";
import { FileText, MessageSquare, Plus, Upload } from "lucide-react";
import { api } from "../../lib/api";

export default function Courses() {
  const { data: courses, isLoading } = useSWR("/api/v1/courses", api.listCourses);

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your courses</h1>
        <Link to="/courses/new" className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          New course
        </Link>
      </div>

      {isLoading && <div className="text-gray-500">Loading…</div>}

      {courses && courses.length === 0 && !isLoading && (
        <div className="card text-center text-gray-500">
          No courses yet. Create your first one to start ingesting materials.
        </div>
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
            </div>
            <div className="mt-4 flex gap-2">
              <Link
                to={`/courses/${course.id}/chat`}
                className="btn-primary flex flex-1 items-center justify-center gap-1"
              >
                <MessageSquare size={14} />
                Chat
              </Link>
              <Link
                to={`/courses/${course.id}/ingest`}
                className="btn-secondary flex items-center gap-1"
                title="Add materials"
              >
                <Upload size={14} />
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
