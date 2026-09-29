import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Film, Ticket, LogOut, LogIn, UserPlus, Menu, X, User } from "lucide-react";

import { useAuth } from "../context/AuthContext";

export function Navbar() {
  const { isAuthenticated, userEmail, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  function handleLogout() {
    logout();
    setMobileMenuOpen(false);
    navigate("/login");
  }

  const closeMobileMenu = () => setMobileMenuOpen(false);

  const userInitial = userEmail ? userEmail.charAt(0).toUpperCase() : "U";

  return (
    <header className="navbar">
      <div className="navbar__content">
        <Link to="/movies" className="navbar__brand" onClick={closeMobileMenu}>
          <span className="brand-logo-icon">
            <Film size={22} className="brand-icon-svg" />
          </span>
          <span className="brand-text">
            Cine<span className="brand-accent">Verse</span>
          </span>
        </Link>

        {/* Desktop Navigation Links */}
        <nav className="navbar__links desktop-nav" aria-label="Điều hướng chính">
          <NavLink
            to="/movies"
            className={({ isActive }) =>
              `nav-link ${isActive ? "nav-link--active" : ""}`
            }
          >
            <Film size={18} />
            <span>Phim chiếu</span>
          </NavLink>

          {isAuthenticated ? (
            <NavLink
              to="/my-bookings"
              className={({ isActive }) =>
                `nav-link ${isActive ? "nav-link--active" : ""}`
              }
            >
              <Ticket size={18} />
              <span>Vé của tôi</span>
            </NavLink>
          ) : null}
        </nav>

        {/* Desktop Auth Controls */}
        <div className="navbar__auth desktop-nav">
          {isAuthenticated ? (
            <div className="user-profile-badge">
              <div className="user-avatar" title={userEmail ?? "Tài khoản"}>
                <span className="user-avatar__initial">{userInitial}</span>
              </div>
              <span className="user-email-text" title={userEmail ?? ""}>
                {userEmail ? userEmail.split("@")[0] : "Thành viên"}
              </span>
              <button
                className="button-icon-logout"
                type="button"
                onClick={handleLogout}
                title="Đăng xuất"
                aria-label="Đăng xuất"
              >
                <LogOut size={16} />
                <span>Thoát</span>
              </button>
            </div>
          ) : (
            <div className="guest-actions">
              <NavLink
                to="/login"
                className={({ isActive }) =>
                  `nav-link nav-link--login ${isActive ? "nav-link--active" : ""}`
                }
              >
                <LogIn size={17} />
                <span>Đăng nhập</span>
              </NavLink>
              <NavLink to="/register" className="button button--small button--glow">
                <UserPlus size={16} />
                <span>Đăng ký</span>
              </NavLink>
            </div>
          )}
        </div>

        {/* Mobile Hamburger Button */}
        <button
          className="mobile-menu-toggle"
          type="button"
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          aria-label="Toggle menu"
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="mobile-drawer" onClick={closeMobileMenu}>
          <div
            className="mobile-drawer__content"
            onClick={(e) => e.stopPropagation()}
          >
            {isAuthenticated && (
              <div className="mobile-user-card">
                <div className="user-avatar">
                  <User size={20} />
                </div>
                <div>
                  <div className="mobile-user-title">Tài khoản</div>
                  <div className="mobile-user-sub">{userEmail ?? "Đã đăng nhập"}</div>
                </div>
              </div>
            )}

            <div className="mobile-nav-links">
              <NavLink
                to="/movies"
                onClick={closeMobileMenu}
                className={({ isActive }) =>
                  `mobile-nav-link ${isActive ? "mobile-nav-link--active" : ""}`
                }
              >
                <Film size={20} />
                <span>Danh sách phim</span>
              </NavLink>

              {isAuthenticated ? (
                <>
                  <NavLink
                    to="/my-bookings"
                    onClick={closeMobileMenu}
                    className={({ isActive }) =>
                      `mobile-nav-link ${isActive ? "mobile-nav-link--active" : ""}`
                    }
                  >
                    <Ticket size={20} />
                    <span>Vé của tôi</span>
                  </NavLink>
                  <button
                    className="mobile-nav-link mobile-nav-link--danger"
                    type="button"
                    onClick={handleLogout}
                  >
                    <LogOut size={20} />
                    <span>Đăng xuất</span>
                  </button>
                </>
              ) : (
                <>
                  <NavLink
                    to="/login"
                    onClick={closeMobileMenu}
                    className="mobile-nav-link"
                  >
                    <LogIn size={20} />
                    <span>Đăng nhập</span>
                  </NavLink>
                  <NavLink
                    to="/register"
                    onClick={closeMobileMenu}
                    className="button button--wide"
                  >
                    <UserPlus size={18} />
                    <span>Tạo tài khoản mới</span>
                  </NavLink>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
