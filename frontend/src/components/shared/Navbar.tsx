import { Link, useNavigate } from "react-router-dom";
import { LogOut, BookOpen, Key } from "lucide-react";
import { clearSession, getCurrentUser } from "../../lib/auth";

export default function Navbar() {
  const navigate = useNavigate();
  const user = getCurrentUser();

  const handleLogout = () => {
    clearSession();
    navigate("/login");
  };

  return (
    <nav className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <BookOpen size={20} className="text-primary-600" />
          <span>Personal Study Assistant</span>
        </Link>
        {user && (
          <div className="flex items-center gap-3 text-sm">
            <span className="text-gray-600">{user.name}</span>
            <Link
              to="/settings/api-key"
              className="btn-secondary flex items-center gap-1.5"
              title="API key for MCP"
            >
              <Key size={14} />
              API key
            </Link>
            <button onClick={handleLogout} className="btn-secondary flex items-center gap-1.5">
              <LogOut size={14} />
              Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
