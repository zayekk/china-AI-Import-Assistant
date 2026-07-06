import React from "react";
import { NavLink } from "react-router-dom";
import { Home, Search, Package, Settings, ShoppingBag, Calculator, ListChecks } from "lucide-react";
import clsx from "clsx";

const navItems = [
  { to: "/", label: "Accueil", icon: Home, end: true },
  { to: "/analyze", label: "Analyser un produit", icon: Search },
  { to: "/products", label: "Produits", icon: Package },
  { to: "/scrape", label: "Scanner produits", icon: ShoppingBag },
  { to: "/scan-guide", label: "Scan guidé", icon: ListChecks },
  { to: "/import-estimator", label: "Estimer un import", icon: Calculator },
];

export default function Sidebar() {
  return (
    <aside className="w-64 shrink-0 bg-white border-r border-gray-200 h-screen sticky top-0 flex flex-col">
      <div className="px-6 py-5 border-b border-gray-200">
        <h1 className="text-lg font-bold text-brand-600 leading-tight">
          China AI
          <br />
          Import Assistant
        </h1>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-50 text-brand-700"
                  : "text-gray-600 hover:bg-gray-100"
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-gray-200">
        <NavLink
          to="/settings"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100"
        >
          <Settings size={18} />
          Paramètres
        </NavLink>
      </div>
    </aside>
  );
}
