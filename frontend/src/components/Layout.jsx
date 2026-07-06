import React from "react";
import Sidebar from "./Sidebar";

export default function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 p-6 sm:p-8 max-w-6xl mx-auto w-full">{children}</main>
    </div>
  );
}
