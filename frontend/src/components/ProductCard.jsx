import React from "react";
import { Link } from "react-router-dom";
import { Star, ShoppingCart } from "lucide-react";

export default function ProductCard({ product }) {
  const image = product.images?.[0];

  return (
    <Link
      to={`/products/${product.id}`}
      className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-md transition-shadow group"
    >
      <div className="aspect-square bg-gray-100 overflow-hidden">
        {image ? (
          <img
            src={image}
            alt={product.name_translated || product.name_original}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-300">
            <ShoppingCart size={32} />
          </div>
        )}
      </div>
      <div className="p-3 space-y-1">
        <p className="text-sm font-medium text-gray-800 line-clamp-2 leading-snug">
          {product.name_translated || product.name_original}
        </p>
        <div className="flex items-center justify-between pt-1">
          <span className="text-brand-600 font-bold text-sm">
            {product.price_value
              ? `${product.price_value} ${product.price_currency}`
              : "Prix N/A"}
          </span>
          {product.rating && (
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <Star size={12} className="fill-yellow-400 text-yellow-400" />
              {product.rating}
            </span>
          )}
        </div>
        {product.sales_count && (
          <p className="text-xs text-gray-400">{product.sales_count} ventes</p>
        )}
      </div>
    </Link>
  );
}
