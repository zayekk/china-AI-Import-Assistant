import React from "react";
import { Truck } from "lucide-react";

// Libellés (avec emoji) des caractéristiques logistiques actives : 7 clés booléennes du
// contrat IA (logistics_profile).
const TRAIT_LABELS = {
  fragile: "🔍 Fragile",
  heavy: "⚖️ Lourd",
  bulky: "📦 Volumineux",
  liquid: "💧 Liquide",
  has_battery: "🔋 Batterie",
  textile: "🧵 Textile",
  electronic: "⚡ Électronique",
};

const TRANSPORT_LABELS = {
  air: "✈️ Avion",
  sea: "🚢 Bateau",
  mixed: "⚖️ Mixte",
};

/**
 * Profil logistique du produit (fragilité, poids, batterie, etc.) et mode de transport
 * recommandé par l'IA pour l'import.
 */
export default function LogisticsCard({ profile, recommendedTransport, transportExplanation }) {
  const activeTraits = profile ? Object.keys(TRAIT_LABELS).filter((key) => profile[key]) : [];

  if (activeTraits.length === 0 && !recommendedTransport) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Truck size={16} /> Analyse logistique
      </h3>

      {activeTraits.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {activeTraits.map((key) => (
            <span
              key={key}
              className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-medium text-gray-700"
            >
              {TRAIT_LABELS[key]}
            </span>
          ))}
        </div>
      )}

      {recommendedTransport && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-lg font-bold text-blue-900">
            {TRANSPORT_LABELS[recommendedTransport] || recommendedTransport}
          </p>
          {transportExplanation && <p className="text-sm text-blue-800 mt-1">{transportExplanation}</p>}
        </div>
      )}
    </div>
  );
}
