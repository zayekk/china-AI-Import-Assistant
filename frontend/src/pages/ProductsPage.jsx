import React, { useEffect, useState } from "react";
import { Loader2, SlidersHorizontal } from "lucide-react";
import ProductCard from "../components/ProductCard";
import { listProducts } from "../services/productService";

export default function ProductsPage() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [platform, setPlatform] = useState("");

  const fetchProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const filters = {};
      if (search) filters.search = search;
      if (platform) filters.platform = platform;
      const data = await listProducts(filters);
      setProducts(data);
    } catch (err) {
      setError("Impossible de charger les produits.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchProducts();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Produits</h1>
        <p className="text-gray-500 mt-1">
          Classement des produits scannés, avec filtres par plateforme et prix.
        </p>
      </div>

      <form
        onSubmit={handleSearchSubmit}
        className="bg-white rounded-2xl border border-gray-200 p-4 flex flex-wrap gap-3 items-center"
      >
        <SlidersHorizontal size={18} className="text-gray-400" />
        <input
          type="text"
          placeholder="Rechercher un produit..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-[180px] rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">Toutes plateformes</option>
          <option value="taobao">Taobao</option>
          <option value="pinduoduo">Pinduoduo</option>
          <option value="alibaba">Alibaba</option>
          <option value="1688">1688</option>
        </select>
        <button
          type="submit"
          className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          Filtrer
        </button>
      </form>

      {loading && (
        <div className="flex justify-center py-12 text-gray-400">
          <Loader2 className="animate-spin" size={28} />
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {!loading && !error && products.length === 0 && (
        <p className="text-gray-400 text-sm text-center py-12">
          Aucun produit trouvé. Lancez un scan depuis la page "Scanner produits".
        </p>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
}
