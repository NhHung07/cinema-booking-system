import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export function Navbar() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="navbar">
      <div className="navbar__content">
        <NavLink to="/movies" className="navbar__brand">
          Cinema Booking
        </NavLink>
        <nav className="navbar__links" aria-label="Điều hướng chính">
          <NavLink to="/movies" className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}>
            Movies
          </NavLink>
          {isAuthenticated ? (
            <>
              <NavLink
                to="/my-bookings"
                className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}
              >
                My Bookings
              </NavLink>
              <button className="nav-link nav-link--button" type="button" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <>
              <NavLink
                to="/login"
                className={({ isActive }) => (isActive ? "nav-link nav-link--active" : "nav-link")}
              >
                Login
              </NavLink>
              <NavLink to="/register" className="button button--small">
                Register
              </NavLink>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
