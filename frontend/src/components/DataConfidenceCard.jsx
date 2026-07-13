import React from "react";
import { Gauge } from "lucide-react";
import clsx from "clsx";

const LABELS = {
  price: "Prix",
  specifications: "Spécifications",
  photos: "Photos",
  reviews: "Avis",
  ocr: "OCR",
};

function barColor(value) {
  if (value >= 70) return "bg-green-500";
  if (value >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

/**
 * "Confiance des données" : confiance de l'IA par catégorie (distincte de confidence_score,
 * qui reflète la confiance globale), pour que l'utilisateur sache quelles informations sont
 * les plus fiables. La catégorie "ocr" est écrasée côté serveur par le taux réel de captures
 * exploitées avec succès en analyse multi-captures (voir multi_capture_service.py).
 */
export default function DataConfidenceCard({ confidence }) {
  if (!confidence) return null;
  const entries = Object.keys(LABELS).filter((key) => confidence[key] !== undefined);
  if (entries.length === 0) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Gauge size={16} /> Confiance des données
      </h3>
      <div className="space-y-2">
        {entries.map((key) => {
          const value = Number(confidence[key]) || 0;
          return (
            <div key={key}>
              <div className="flex items-center justify-between text-xs text-gray-500 mb-0.5">
                <span>{LABELS[key]}</span>
                <span className="font-semibold text-gray-700">{value}%</span>
              </div>
              <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={clsx("h-full rounded-full", barColor(value))}
                  style={{ width: `${value}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
