import React from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

// no props needed yet; children are rendered via <Outlet />
const Layout: React.FC = () => {
  return (
    // min-h-screen ensures the page is at least the height of the viewport
    <div className="flex flex-col min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* STICKY HEADER: Added 'sticky top-0' and 'z-50' to stay on top of other elements */}
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-gray-800/80 backdrop-blur-md shadow-sm border-b border-gray-200 dark:border-gray-700">
        <nav className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="text-xl font-semibold text-gray-800 dark:text-gray-100">
            <Link to="/">House Plan Generator</Link>
          </div>
          <ul className="flex space-x-6 text-sm">
            <li>
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors` +
                  (isActive ? " font-bold text-blue-600 dark:text-blue-400" : "")
                }
              >
                Home
              </NavLink>
            </li>
          </ul>
        </nav>
      </header>

      {/* MAIN CONTENT: flex-grow + flex-col lets children fill available height */}
      <main className="grow flex flex-col min-h-0">
        <Outlet />
      </main>

      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 text-center py-6 text-sm text-gray-500">
        © {new Date().getFullYear()} House Plan Generator
      </footer>
    </div>
  );
};

export default Layout;
