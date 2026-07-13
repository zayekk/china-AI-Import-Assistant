import React from "react";
import { Calculator } from "lucide-react";
import clsx from "clsx";
import { formatCnyWithFcfa, formatFcfa, formatPercent } from "../utils/currency";

/**
 * "Coût d'import" : remplace l'ancienne section "Estimation commerciale" (v1.1, centrée euro)
 * — même objet `commercial_estimate` sous-jacent, réaffiché en FCFA (public cible : importateurs
 * africains). Les totaux (coût rendu, bénéfice, marge, ROI) viennent TOUJOURS du backend, jamais
 * recalculés ici ; seule l'équivalence FCFA ligne par ligne pour les montants en yuan est un
 * raccourci d'affichage (voir utils/currency.js).
 */
export default function ImportCostCalculatorCard({ estimate }) {
  if (!estimate) return null;

  if (!estimate.possible) {
    return (
      <div className="bg-white border border-gray-200 rounded-2xl p-4 sm:p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800 mb-1">
          <Calculator size={16} /> Coût d'import
        </h3>
        <p className="text-sm text-gray-500 italic">
          Estimation non disponible : {estimate.reason_if_not_possible || "données insuffisantes."}
        </p>
      </div>
    );
  }

  const supplierPrice = formatCnyWithFcfa(estimate.purchase_price_cny);
  const transport = formatCnyWithFcfa(estimate.estimated_transport_cny);
  const customs = formatCnyWithFcfa(estimate.estimated_customs_cny);
  const miscFees = formatCnyWithFcfa(estimate.misc_fees_cny);
  const profitPositive = estimate.estimated_profit_fcfa != null ? estimate.estimated_profit_fcfa >= 0 : null;

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-4 sm:p-5 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Calculator size={16} /> Coût d'import
      </h3>
      <p className="text-xs text-gray-400 italic">
        Estimation générée par IA — équivalence FCFA indicative (1 ¥ ≈ 100 FCFA)
      </p>

      <div className="divide-y divide-gray-100 border border-gray-100 rounded-xl overflow-hidden">
        <Row label="Prix fournisseur" primary={supplierPrice.cny} secondary={supplierPrice.fcfa} />
        <Row label="Transport" primary={transport.cny} secondary={transport.fcfa} />
        <Row label="Douane" primary={customs.cny} secondary={customs.fcfa} />
        <Row label="Frais divers" primary={miscFees.cny} secondary={miscFees.fcfa} />
        <Row label="Coût rendu" primary={formatFcfa(estimate.landed_cost_fcfa)} highlight />
        <Row label="Prix conseillé" primary={formatFcfa(estimate.suggested_resale_price_fcfa)} />
        <Row
          label="Bénéfice"
          primary={formatFcfa(estimate.estimated_profit_fcfa)}
          highlight
          positive={profitPositive}
        />
        <Row label="Marge" primary={formatPercent(estimate.margin_percentage)} />
        <Row label="ROI" primary={formatPercent(estimate.roi_percentage)} />
      </div>
    </div>
  );
}

function Row({ label, primary, secondary, highlight, positive }) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5 text-sm gap-3">
      <span className="text-gray-500 shrink-0">{label}</span>
      <span
        className={clsx(
          "text-right",
          highlight && "font-semibold",
          positive === true && "text-green-600",
          positive === false && "text-red-600",
          positive == null && !highlight && "text-gray-800"
        )}
      >
        {primary}
        {secondary && <span className="text-gray-400 font-normal"> · {secondary}</span>}
      </span>
    </div>
  );
}
