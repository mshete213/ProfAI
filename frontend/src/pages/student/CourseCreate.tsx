import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api } from "../../lib/api";

export default function CourseCreate() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [styleInstructions, setStyleInstructions] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const course = await api.createCourse({
        name,
        description,
        style_instructions: styleInstructions,
      });
      navigate(`/courses/${course.id}/ingest`);
    } catch (err: any) {
      setError(err.message || "Failed to create course");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <Link to="/courses" className="mb-4 inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
        <ArrowLeft size={14} />
        Back to courses
      </Link>
      <h1 className="mb-1 text-2xl font-semibold">New course</h1>
      <p className="mb-6 text-sm text-gray-600">Create a personal knowledge base for a subject.</p>

      <form onSubmit={onSubmit} className="card space-y-4">
        <div>
          <label className="label">Course name</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input"
            placeholder="e.g. Linear Algebra"
          />
        </div>
        <div>
          <label className="label">Description (optional)</label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="input"
          />
        </div>
        <div>
          <label className="label">Response style (optional)</label>
          <textarea
            rows={6}
            value={styleInstructions}
            onChange={(e) => setStyleInstructions(e.target.value)}
            className="input font-mono text-sm"
            placeholder={`Example:
- Always show full derivations step by step
- Use LaTeX for math
- End each solution with a sanity check`}
          />
          <p className="mt-1 text-xs text-gray-500">How the assistant should format and structure answers.</p>
        </div>
        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <button type="submit" disabled={submitting} className="btn-primary">
          {submitting ? "Creating..." : "Create course"}
        </button>
      </form>
    </div>
  );
}
