import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Loader2, RefreshCw, Star, Store } from "lucide-react";
import { getProduct, getProductScore } from "../services/productService";
import ScoreBadge from "../components/ScoreBadge";

export default function ProductDetailPage() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scoreLoading, setScoreLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchProduct = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProduct(id);
      setProduct(data);
    } catch (err) {
      setError("Produit introuvable.");
    } finally {
      setLoading(false);
    }
  };

  const fetchScore = async (forceRecompute = false) => {
    setScoreLoading(true);
    try {
      const data = await getProductScore(id, forceRecompute);
      setScore(data);
    } catch (err) {
      // le score peut ne pas encore exister, on ignore silencieusement la première fois
    } finally {
      setScoreLoading(false);
    }
  };

  useEffect(() => {
    fetchProduct();
    fetchScore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center py-20 text-gray-400">
        <Loader2 className="animate-spin" size={28} />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 gap-8">
        <div className="aspect-square bg-white rounded-2xl border border-gray-200 overflow-hidden">
          {product.images?.[0] ? (
            <img
              src={product.images[0]}
              alt={product.name_translated || product.name_original}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-300">
              Pas d'image
            </div>
          )}
        </div>

        <div className="space-y-4">
          <h1 className="text-2xl font-bold text-gray-900">
            {product.name_translated || product.name_original}
          </h1>

          <p className="text-3xl font-bold text-brand-600">
            {product.price_value ? `${product.price_value} ${product.price_currency}` : "Prix N/A"}
          </p>

          <div className="flex items-center gap-4 text-sm text-gray-500">
            {product.rating && (
              <span className="flex items-center gap-1">
                <Star size={14} className="fill-yellow-400 text-yellow-400" />
                {product.rating}
              </span>
            )}
            {product.sales_count && <span>{product.sales_count} ventes</span>}
            {product.platform && (
              <span className="uppercase font-medium text-gray-400">{product.platform}</span>
            )}
          </div>

          {product.supplier && (
            <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
              <Store size={20} className="text-gray-400" />
              <div>
                <p className="font-medium text-gray-800 text-sm">{product.supplier.name}</p>
                <p className="text-xs text-gray-400">
                  Score fournisseur : {product.supplier.supplier_score ?? "N/A"}/100
                </p>
              </div>
            </div>
          )}

          {product.description_translated || product.description_original ? (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">Description</h3>
              <p className="text-sm text-gray-600 whitespace-pre-line">
                {product.description_translated || product.description_original}
              </p>
            </div>
          ) : null}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">Score Produit Gagnant</h2>
          <button
            onClick={() => fetchScore(true)}
            disabled={scoreLoading}
            className="flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700"
          >
            <RefreshCw size={14} className={scoreLoading ? "animate-spin" : ""} />
            Recalculer
          </button>
        </div>

        {score ? (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-5">
              <ScoreBadge label="Demande (30%)" score={score.demand_score} />
              <ScoreBadge label="Marge (25%)" score={score.margin_score} />
              <ScoreBadge label="Qualité (20%)" score={score.quality_score} />
              <ScoreBadge label="Fournisseur (15%)" score={score.supplier_reliability_score} />
              <ScoreBadge label="Logistique (10%)" score={score.logistics_score} />
            </div>
            <div className="bg-brand-50 rounded-xl p-4 text-center mb-5">
              <p className="text-3xl font-bold text-brand-700">{score.final_score}/100</p>
              <p className="text-xs text-brand-600 mt-1">Score final pondéré</p>
            </div>

            <div className="grid sm:grid-cols-2 gap-5">
              {score.strengths?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-green-700 mb-2">Points forts</h3>
                  <ul className="space-y-1 text-sm text-gray-700">
                    {score.strengths.map((s, idx) => (
                      <li key={idx}>• {s}</li>
                    ))}
                  </ul>
                </div>
              )}
              {score.risks?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-red-700 mb-2">Risques</h3>
                  <ul className="space-y-1 text-sm text-gray-700">
                    {score.risks.map((r, idx) => (
                      <li key={idx}>• {r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </>
        ) : (
          <p className="text-sm text-gray-400">
            {scoreLoading ? "Calcul du score en cours..." : "Score non disponible."}
          </p>
        )}
      </div>
    </div>
  );
}
