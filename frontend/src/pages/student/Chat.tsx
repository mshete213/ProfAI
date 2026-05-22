import { Link, useParams } from "react-router-dom";
import useSWR from "swr";
import { ArrowLeft } from "lucide-react";
import ChatWindow from "../../components/chat/ChatWindow";
import { api } from "../../lib/api";

export default function Chat() {
  const { courseId } = useParams<{ courseId: string }>();
  const { data: course } = useSWR(courseId ? `course-${courseId}` : null, () => api.getCourse(courseId!));

  if (!courseId) return null;

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <Link to="/courses" className="mb-3 inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
        <ArrowLeft size={14} />
        Back to courses
      </Link>
      <ChatWindow courseId={courseId} courseName={course?.name ?? "Course"} />
    </div>
  );
}
