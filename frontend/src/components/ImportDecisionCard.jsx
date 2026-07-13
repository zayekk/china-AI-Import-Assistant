import React from "react";
import { PackageCheck, PackageSearch, PackageX } from "lucide-react";
import clsx from "clsx";

// Distinct de QuickSummaryBar/RecommendationBanner (sécurité de l'achat) : cette carte
// porte spécifiquement sur la viabilité commerciale d'IMPORTER ce produit pour le revendre.
// "decision" est toujours calculé côté serveur (voir _import_decision() dans
// ai_engine/services/product_analysis_service.py), jamais par l'IA.
const CONFIG = {
  import: {
    icon: PackageCheck,
    emoji: "✅",
    label: "À importer",
    classes: "bg-green-50 text-green-800 border-green-300",
  },
  study: {
    icon: PackageSearch,
    emoji: "🟡",
    label: "À étudier",
    classes: "bg-yellow-50 text-yellow-800 border-yellow-300",
  },
  avoid: {
    icon: PackageX,
    emoji: "🔴",
    label: "À éviter",
    classes: "bg-red-50 text-red-800 border-red-300",
  },
};

export default function ImportDecisionCard({ decision, explanation }) {
  const config = CONFIG[decision] || CONFIG.study;
  const Icon = config.icon;

  return (
    <div className={clsx("rounded-2xl border-2 p-4 sm:p-5", config.classes)}>
      <div className="flex items-center gap-3">
        <Icon size={22} className="shrink-0" />
        <div>
          <p className="text-xs uppercase tracking-wide font-medium opacity-70">Décision Import</p>
          <p className="text-lg font-bold">
            {config.emoji} {config.label}
          </p>
        </div>
      </div>
      {explanation && <p className="text-sm mt-2">{explanation}</p>}
    </div>
  );
}
