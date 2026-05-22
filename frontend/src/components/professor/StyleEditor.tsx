import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function StyleEditor({ courseId }: { courseId: string }) {
  const [instructions, setInstructions] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCourse(courseId).then((c) => {
      setInstructions(c.style_instructions || "");
      setLoading(false);
    });
  }, [courseId]);

  const onSave = async () => {
    setSaving(true);
    try {
      await api.updateCourse(courseId, { style_instructions: instructions });
      setSavedAt(new Date());
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="text-sm text-gray-500">Loading…</div>;

  return (
    <div className="card">
      <h3 className="mb-2 font-semibold">Response style instructions</h3>
      <p className="mb-3 text-sm text-gray-600">
        Tell the AI how it should answer student questions. Be specific about format, depth, and conventions.
      </p>
      <textarea
        rows={10}
        value={instructions}
        onChange={(e) => setInstructions(e.target.value)}
        className="input font-mono text-sm"
        placeholder={`Example:
- Always show full derivations step by step
- Use LaTeX for math: $x^2$ for inline, $$..$$ for display
- Include the formula being applied at each step
- End each solution with a one-sentence sanity check`}
      />
      <div className="mt-3 flex items-center gap-3">
        <button onClick={onSave} disabled={saving} className="btn-primary">
          {saving ? "Saving..." : "Save"}
        </button>
        {savedAt && <span className="text-xs text-gray-500">Saved {savedAt.toLocaleTimeString()}</span>}
      </div>
    </div>
  );
}
