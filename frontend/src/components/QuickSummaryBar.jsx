import React from "react";
import clsx from "clsx";

// Mapping strictement aligné sur les valeurs calculées côté serveur
// (ai_engine/services/product_analysis_service.py : _decision_badge, _risk_level,
// _supplier_reliability, _margin_potential). Le frontend ne fait qu'afficher ces clés.
const BADGE_META = {
  recommended: { emoji: "🟢", label: "Achat recommandé", classes: "bg-green-50 text-green-800 border-green-300" },
  verify: { emoji: "🟡", label: "Vérifications recommandées", classes: "bg-yellow-50 text-yellow-800 border-yellow-300" },
  caution: { emoji: "🟠", label: "Prudence", classes: "bg-orange-50 text-orange-800 border-orange-300" },
  avoid: { emoji: "🔴", label: "À éviter", classes: "bg-red-50 text-red-800 border-red-300" },
};

const RISK_LABELS = { low: "Faible", medium: "Modéré", high: "Élevé" };
const RELIABILITY_LABELS = { yes: "Oui", medium: "Moyen", no: "Non" };
const MARGIN_LABELS = { low: "Faible", medium: "Moyenne", high: "Forte" };

function statClass(kind, value) {
  if (kind === "risk") {
    return value === "high" ? "text-red-700" : value === "medium" ? "text-orange-600" : "text-green-700";
  }
  if (kind === "reliability") {
    return value === "no" ? "text-red-700" : value === "medium" ? "text-orange-600" : "text-green-700";
  }
  if (kind === "margin") {
    return value === "low" ? "text-red-700" : value === "medium" ? "text-orange-600" : "text-green-700";
  }
  return "text-gray-800";
}

/**
 * Encart "Résumé ultra rapide" affiché tout en haut du rapport : permet à un
 * importateur de comprendre la situation en moins de 5 secondes (décision, score,
 * risque, fiabilité fournisseur, marge potentielle).
 */
export default function QuickSummaryBar({
  decisionBadge,
  finalScore,
  riskLevel,
  supplierReliability,
  marginPotential,
}) {
  const badge = BADGE_META[decisionBadge] || BADGE_META.caution;

  return (
    <div className={clsx("rounded-2xl border-2 p-4 sm:p-5", badge.classes)}>
      <div className="flex items-center gap-3">
        <span className="text-3xl leading-none">{badge.emoji}</span>
        <div>
          <p className="text-xs uppercase tracking-wide font-medium opacity-70">Décision IA</p>
          <p className="text-lg font-bold">{badge.label}</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl bg-white/70 border border-black/5 px-3 py-2 text-center">
          <p className="text-xl font-bold text-gray-900">{Number(finalScore) || 0}<span className="text-xs font-normal text-gray-400">/100</span></p>
          <p className="text-[11px] uppercase tracking-wide text-gray-500 mt-0.5">Score global</p>
        </div>
        <div className="rounded-xl bg-white/70 border border-black/5 px-3 py-2 text-center">
          <p className={clsx("text-xl font-bold", statClass("risk", riskLevel))}>
            {RISK_LABELS[riskLevel] || "—"}
          </p>
          <p className="text-[11px] uppercase tracking-wide text-gray-500 mt-0.5">Niveau de risque</p>
        </div>
        <div className="rounded-xl bg-white/70 border border-black/5 px-3 py-2 text-center">
          <p className={clsx("text-xl font-bold", statClass("reliability", supplierReliability))}>
            {RELIABILITY_LABELS[supplierReliability] || "—"}
          </p>
          <p className="text-[11px] uppercase tracking-wide text-gray-500 mt-0.5">Fournisseur fiable</p>
        </div>
        <div className="rounded-xl bg-white/70 border border-black/5 px-3 py-2 text-center">
          <p className={clsx("text-xl font-bold", statClass("margin", marginPotential))}>
            {MARGIN_LABELS[marginPotential] || "—"}
          </p>
          <p className="text-[11px] uppercase tracking-wide text-gray-500 mt-0.5">Marge potentielle</p>
        </div>
      </div>
    </div>
  );
}
