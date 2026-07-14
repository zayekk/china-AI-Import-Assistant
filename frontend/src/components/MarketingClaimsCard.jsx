import React from "react";
import { Megaphone } from "lucide-react";
import clsx from "clsx";

/**
 * Vérifie la pertinence des arguments marketing détectés (ex: "Premium", "Qualité pro") en
 * indiquant si chacun est jugé justifié ou purement marketing par l'IA.
 */
export default function MarketingClaimsCard({ claims = [] }) {
  if (!claims || claims.length === 0) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Megaphone size={16} /> Analyse des arguments marketing
      </h3>
      <ul className="space-y-2.5">
        {claims.map((item, idx) => (
          <li key={idx} className="border border-gray-100 rounded-lg p-3 space-y-1">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <span className="text-sm font-semibold text-gray-800">{item.claim}</span>
              <span
                className={clsx(
                  "rounded-full border px-2.5 py-1 text-xs font-semibold",
                  item.justified
                    ? "bg-green-50 text-green-800 border-green-200"
                    : "bg-orange-50 text-orange-800 border-orange-200"
                )}
              >
                {item.justified ? "✅ Justifié" : "⚠️ Marketing"}
              </span>
            </div>
            {item.explanation && <p className="text-sm text-gray-600">{item.explanation}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
