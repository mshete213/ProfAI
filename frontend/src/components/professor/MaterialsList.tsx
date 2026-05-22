import { Trash2, FileText, Youtube, Globe, FolderOpen } from "lucide-react";
import useSWR from "swr";
import { api } from "../../lib/api";
import type { DocumentMeta, SourceType } from "../../lib/types";

const ICONS: Record<SourceType, React.ReactNode> = {
  pdf: <FileText size={14} />,
  pptx: <FileText size={14} />,
  docx: <FileText size={14} />,
  youtube: <Youtube size={14} />,
  drive: <FolderOpen size={14} />,
  canvas: <Globe size={14} />,
};

export default function MaterialsList({ courseId }: { courseId: string }) {
  const { data, mutate } = useSWR(`materials-${courseId}`, () => api.listMaterials(courseId));

  const onDelete = async (doc: DocumentMeta) => {
    if (!confirm(`Delete "${doc.filename}"? Its vectors will be removed from search.`)) return;
    await api.deleteMaterial(courseId, doc.id);
    mutate();
  };

  if (!data) return <div className="text-sm text-gray-500">Loading materials…</div>;
  if (data.length === 0) return <div className="card text-center text-sm text-gray-500">No materials ingested yet.</div>;

  return (
    <div className="card">
      <h3 className="mb-3 font-semibold">Ingested materials</h3>
      <ul className="divide-y divide-gray-200">
        {data.map((doc) => (
          <li key={doc.id} className="flex items-center justify-between py-2 text-sm">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-gray-400">{ICONS[doc.source_type]}</span>
              <span className="truncate" title={doc.filename}>{doc.filename}</span>
              <span className="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                {doc.chunk_count} chunks
              </span>
            </div>
            <button onClick={() => onDelete(doc)} className="text-gray-400 hover:text-red-600">
              <Trash2 size={14} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
