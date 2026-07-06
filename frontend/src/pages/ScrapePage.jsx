import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, ShoppingBag } from "lucide-react";
import { launchScrape } from "../services/productService";

export default function ScrapePage() {
  const [url, setUrl] = useState("");
  const [fetchReviews, setFetchReviews] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    try {
      const data = await launchScrape(url, { fetchReviews });
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Échec du scraping. Vérifiez le lien et réessayez."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Scanner un produit</h1>
        <p className="text-gray-500 mt-1">
          Récupère automatiquement le nom, le prix, les images, les variantes et les avis
          d'une fiche produit Taobao, Pinduoduo, Alibaba ou 1688.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
        <div>
          <label className="text-sm font-medium text-gray-700 mb-1.5 block">
            Lien produit
          </label>
          <input
            type="url"
            required
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://item.taobao.com/item.htm?id=..."
            className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={fetchReviews}
            onChange={(e) => setFetchReviews(e.target.checked)}
            className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
          />
          Récupérer aussi les avis clients
        </label>

        <button
          type="submit"
          disabled={loading}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-medium px-6 py-3 rounded-xl transition-colors"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <ShoppingBag size={16} />}
          {loading ? "Scan en cours..." : "Lancer le scan"}
        </button>
      </form>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-5 space-y-3">
          <p className="font-medium text-green-800">{result.message}</p>
          {result.data && (
            <div className="text-sm text-green-700 space-y-1">
              <p>Nom : {result.data.name}</p>
              <p>Prix : {result.data.price ?? "N/A"}</p>
              <p>Score fournisseur : {result.data.supplier_score ?? "N/A"}/100</p>
              <p>Avis récupérés : {result.data.reviews_count}</p>
            </div>
          )}
          {result.product_id && (
            <button
              onClick={() => navigate(`/products/${result.product_id}`)}
              className="text-sm font-medium text-brand-600 hover:text-brand-700"
            >
              Voir la fiche produit →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
