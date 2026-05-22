import { Link, useParams } from "react-router-dom";
import useSWR from "swr";
import { ArrowLeft } from "lucide-react";
import StyleEditor from "../../components/professor/StyleEditor";
import { api } from "../../lib/api";

export default function CourseStyle() {
  const { courseId } = useParams<{ courseId: string }>();
  const { data: course } = useSWR(courseId ? `course-${courseId}` : null, () => api.getCourse(courseId!));

  if (!courseId) return null;

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <Link to="/professor/dashboard" className="mb-4 inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
        <ArrowLeft size={14} />
        Back to dashboard
      </Link>
      <h1 className="mb-1 text-2xl font-semibold">{course?.name ?? "Loading…"}</h1>
      <p className="mb-6 text-sm text-gray-600">Configure how the AI answers questions about this course</p>
      <StyleEditor courseId={courseId} />
    </div>
  );
}
