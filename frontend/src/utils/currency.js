/**
 * Formatage des montants du rapport d'analyse (yuan, FCFA, euro).
 *
 * Les totaux dérivés (coût rendu, bénéfice, marge, ROI) viennent TOUJOURS du backend
 * (ai_engine/services/product_analysis_service.py::_normalize_commercial_estimate) — jamais
 * recalculés ici. Seule l'équivalence FCFA affichée ligne par ligne pour un montant en yuan
 * (ex: "58 ¥ ≈ 5 800 FCFA") utilise CNY_XOF_DISPLAY_RATE, qui reflète la valeur par défaut de
 * settings.IMPORT_CNY_XOF_RATE côté serveur (1 ¥ = 100 FCFA, taux volontairement heuristique —
 * voir sa docstring) : un pur raccourci d'affichage, sans impact sur les montants faisant foi.
 */
export const CNY_XOF_DISPLAY_RATE = 100;

export function formatCny(value) {
  return value === null || value === undefined ? "—" : `${Number(value).toFixed(2)} ¥`;
}

export function formatFcfa(value) {
  return value === null || value === undefined
    ? "—"
    : `${Math.round(Number(value)).toLocaleString("fr-FR")} FCFA`;
}

export function formatEur(value) {
  return value === null || value === undefined ? "—" : `${Number(value).toFixed(2)} €`;
}

export function formatPercent(value) {
  return value === null || value === undefined ? "—" : `${Number(value).toFixed(1)}%`;
}

export function formatCnyWithFcfa(cny) {
  if (cny === null || cny === undefined) return { cny: "—", fcfa: null };
  return { cny: formatCny(cny), fcfa: `≈ ${formatFcfa(cny * CNY_XOF_DISPLAY_RATE)}` };
}
