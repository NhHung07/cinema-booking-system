import { Navigate, Route, Routes } from "react-router-dom";

import { Navbar } from "./components/Navbar";
import { LoginPage } from "./pages/LoginPage";
import { MovieDetailPage } from "./pages/MovieDetailPage";
import { MoviesPage } from "./pages/MoviesPage";
import { MyBookingsPage } from "./pages/MyBookingsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ShowtimeSeatsPage } from "./pages/ShowtimeSeatsPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";

export default function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="page-container">
        <Routes>
          <Route path="/" element={<Navigate to="/movies" replace />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/movies" element={<MoviesPage />} />
          <Route path="/movies/:movieId" element={<MovieDetailPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/showtimes/:showtimeId/seats" element={<ShowtimeSeatsPage />} />
            <Route path="/my-bookings" element={<MyBookingsPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}
