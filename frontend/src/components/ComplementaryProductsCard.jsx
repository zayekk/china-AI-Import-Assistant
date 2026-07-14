import React from "react";
import { PackagePlus } from "lucide-react";

/**
 * Suggestions de produits complémentaires à vendre avec ce produit (upsell / cross-sell).
 */
export default function ComplementaryProductsCard({ products = [] }) {
  if (!products || products.length === 0) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <PackagePlus size={16} /> Produits à vendre ensemble
      </h3>
      <div className="flex flex-wrap gap-2">
        {products.map((product, idx) => (
          <span
            key={idx}
            className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-medium text-gray-700"
          >
            {product}
          </span>
        ))}
      </div>
    </div>
  );
}
