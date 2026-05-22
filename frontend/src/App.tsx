import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/shared/Navbar";
import ProtectedRoute from "./components/shared/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Courses from "./pages/student/Courses";
import CourseCreate from "./pages/student/CourseCreate";
import CourseIngest from "./pages/student/CourseIngest";
import Chat from "./pages/student/Chat";
import ApiKeySettings from "./pages/settings/ApiKeySettings";
import { isAuthenticated } from "./lib/auth";

function HomeRedirect() {
  return isAuthenticated() ? <Navigate to="/courses" replace /> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route
            path="/courses"
            element={
              <ProtectedRoute>
                <Courses />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses/new"
            element={
              <ProtectedRoute>
                <CourseCreate />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses/:courseId/ingest"
            element={
              <ProtectedRoute>
                <CourseIngest />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses/:courseId/chat"
            element={
              <ProtectedRoute>
                <Chat />
              </ProtectedRoute>
            }
          />

          <Route
            path="/settings/api-key"
            element={
              <ProtectedRoute>
                <ApiKeySettings />
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
