import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import AnalyzePage from "./pages/AnalyzePage";
import ProductsPage from "./pages/ProductsPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import ScrapePage from "./pages/ScrapePage";
import ScanGuidePage from "./pages/ScanGuidePage";
import SettingsPage from "./pages/SettingsPage";
import ImportEstimatorPage from "./pages/ImportEstimatorPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/products/:id" element={<ProductDetailPage />} />
        <Route path="/scrape" element={<ScrapePage />} />
        <Route path="/scan-guide" element={<ScanGuidePage />} />
        <Route path="/import-estimator" element={<ImportEstimatorPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}
