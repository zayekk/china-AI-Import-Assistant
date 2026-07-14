import React from "react";
import { Calendar } from "lucide-react";

/**
 * Analyse de saisonnalité du produit : période idéale de vente et mois favorables /
 * défavorables. Affiche toujours un message informatif, même si le produit n'est pas
 * saisonnier (information utile en soi).
 */
export default function SeasonalityCard({
  isSeasonal = false,
  idealPeriod,
  favorableMonths = [],
  unfavorableMonths = [],
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Calendar size={16} /> Analyse saisonnière
      </h3>

      {!isSeasonal ? (
        <p className="text-sm text-gray-600">Produit non saisonnier — vendable toute l'année.</p>
      ) : (
        <div className="space-y-3">
          {idealPeriod && (
            <p className="text-sm text-gray-700">
              <span className="font-medium text-gray-500">Période idéale : </span>
              {idealPeriod}
            </p>
          )}
          {(favorableMonths.length > 0 || unfavorableMonths.length > 0) && (
            <div className="grid sm:grid-cols-2 gap-4">
              {favorableMonths.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-green-700 mb-1.5">Mois favorables</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {favorableMonths.map((month) => (
                      <span
                        key={month}
                        className="inline-flex items-center rounded-full border border-green-200 bg-green-50 px-2.5 py-1 text-xs font-medium text-green-800"
                      >
                        {month}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {unfavorableMonths.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-red-700 mb-1.5">Mois défavorables</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {unfavorableMonths.map((month) => (
                      <span
                        key={month}
                        className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600"
                      >
                        {month}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
