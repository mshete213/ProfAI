import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { getCurrentUser, isAuthenticated } from "../../lib/auth";
import type { UserRole } from "../../lib/types";

interface Props {
  children: ReactNode;
  role?: UserRole;
}

export default function ProtectedRoute({ children, role }: Props) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />;
  if (role) {
    const user = getCurrentUser();
    if (user?.role !== role) return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
