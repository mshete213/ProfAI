import { Link, useParams } from "react-router-dom";
import useSWR from "swr";
import { ArrowLeft, Upload } from "lucide-react";
import ChatWindow from "../../components/chat/ChatWindow";
import { api } from "../../lib/api";

export default function Chat() {
  const { courseId } = useParams<{ courseId: string }>();
  const { data: course } = useSWR(courseId ? `course-${courseId}` : null, () => api.getCourse(courseId!));

  if (!courseId) return null;

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <div className="mb-3 flex items-center justify-between">
        <Link to="/courses" className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
          <ArrowLeft size={14} />
          Back to courses
        </Link>
        <Link to={`/courses/${courseId}/ingest`} className="inline-flex items-center gap-1.5 rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700">
          <Upload size={14} />
          Add materials
        </Link>
      </div>
      <ChatWindow courseId={courseId} courseName={course?.name ?? "Course"} />
    </div>
  );
}
