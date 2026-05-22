import { Navigate, Route, Routes } from "react-router-dom";
import Navbar from "./components/shared/Navbar";
import ProtectedRoute from "./components/shared/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/professor/Dashboard";
import CourseIngest from "./pages/professor/CourseIngest";
import CourseStyle from "./pages/professor/CourseStyle";
import StudentCourses from "./pages/student/Courses";
import Chat from "./pages/student/Chat";
import { getCurrentUser } from "./lib/auth";

function HomeRedirect() {
  const user = getCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  return user.role === "professor" ? (
    <Navigate to="/professor/dashboard" replace />
  ) : (
    <Navigate to="/student/courses" replace />
  );
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
            path="/professor/dashboard"
            element={
              <ProtectedRoute role="professor">
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/professor/courses/:courseId/ingest"
            element={
              <ProtectedRoute role="professor">
                <CourseIngest />
              </ProtectedRoute>
            }
          />
          <Route
            path="/professor/courses/:courseId/style"
            element={
              <ProtectedRoute role="professor">
                <CourseStyle />
              </ProtectedRoute>
            }
          />

          <Route
            path="/student/courses"
            element={
              <ProtectedRoute role="student">
                <StudentCourses />
              </ProtectedRoute>
            }
          />
          <Route
            path="/student/courses/:courseId/chat"
            element={
              <ProtectedRoute role="student">
                <Chat />
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
