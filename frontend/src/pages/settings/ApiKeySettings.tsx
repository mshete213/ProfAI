import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Copy, Key, RefreshCw } from "lucide-react";
import { api } from "../../lib/api";

export default function ApiKeySettings() {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onGenerate = async () => {
    if (apiKey && !confirm("Generating a new key will invalidate the existing one. Continue?")) return;
    setGenerating(true);
    setError(null);
    try {
      const result = await api.generateApiKey();
      setApiKey(result.api_key);
      setCopied(false);
    } catch (err: any) {
      setError(err.message || "Failed to generate API key");
    } finally {
      setGenerating(false);
    }
  };

  const onCopy = async () => {
    if (!apiKey) return;
    await navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <Link to="/courses" className="mb-4 inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
        <ArrowLeft size={14} />
        Back to courses
      </Link>
      <h1 className="mb-1 flex items-center gap-2 text-2xl font-semibold">
        <Key size={22} />
        API key
      </h1>
      <p className="mb-6 text-sm text-gray-600">
        Use this key to authenticate MCP tools (Claude Desktop, etc.) against your study materials.
      </p>

      <div className="card space-y-4">
        {apiKey ? (
          <>
            <div>
              <label className="label">Your new API key</label>
              <div className="flex gap-2">
                <input
                  readOnly
                  value={apiKey}
                  className="input font-mono text-xs"
                  onFocus={(e) => e.target.select()}
                />
                <button onClick={onCopy} className="btn-secondary flex items-center gap-1">
                  <Copy size={14} />
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
              <p className="mt-2 text-xs text-amber-700">
                Save this now — it won't be shown again. Generate a new one anytime to rotate.
              </p>
            </div>
            <div className="rounded-md bg-gray-50 p-3 text-xs">
              <p className="mb-1 font-medium">MCP client config (Claude Desktop)</p>
              <pre className="overflow-x-auto text-[11px] text-gray-700">
{`{
  "mcpServers": {
    "study-assistant": {
      "command": "...",
      "env": { "API_KEY": "${apiKey.slice(0, 12)}..." }
    }
  }
}`}
              </pre>
            </div>
          </>
        ) : (
          <p className="text-sm text-gray-600">
            You don't have an API key yet. Generate one to use the MCP integration.
          </p>
        )}

        {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        <button onClick={onGenerate} disabled={generating} className="btn-primary flex items-center gap-2">
          <RefreshCw size={14} />
          {generating ? "Generating..." : apiKey ? "Generate new key" : "Generate API key"}
        </button>
      </div>
    </div>
  );
}
