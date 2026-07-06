import React from "react";
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  ShieldAlert,
  HelpCircle,
  Sparkles,
  FileSearch,
  Smartphone,
  Bot,
  TrendingUp,
} from "lucide-react";
import clsx from "clsx";
import RecommendationBanner from "./RecommendationBanner";
import ScoreBadge from "./ScoreBadge";
import QuickSummaryBar from "./QuickSummaryBar";
import CriticalAlertsBanner from "./CriticalAlertsBanner";

// Bandes de confiance : bornes STRICTEMENT alignées sur `_confidence_level()` côté serveur
// (backend/ai_engine/services/product_analysis_service.py) : 0-30 / 31-60 / 61-80 / 81-100.
const CONFIDENCE_BANDS = [
  { max: 30, label: "Données insuffisantes", classes: "bg-red-50 text-red-800 border-red-300" },
  { max: 60, label: "Analyse approximative", classes: "bg-orange-50 text-orange-800 border-orange-300" },
  { max: 80, label: "Analyse fiable", classes: "bg-blue-50 text-blue-800 border-blue-300" },
  { max: 100, label: "Forte confiance", classes: "bg-green-50 text-green-800 border-green-300" },
];

function getConfidenceBand(score) {
  const numericScore = Number(score) || 0;
  return (
    CONFIDENCE_BANDS.find((band) => numericScore <= band.max) ||
    CONFIDENCE_BANDS[CONFIDENCE_BANDS.length - 1]
  );
}

/**
 * Affiche le résultat complet d'une analyse IA, conforme au contrat de sortie :
 * { product_name, included, not_included, warnings, quality_score,
 *   supplier_score, profit_score, final_score, recommendation,
 *   detected_data, ai_estimations, missing_information,
 *   confidence_score, confidence_level, confidence_reasons, confidence_risks }
 *
 * Les nouveaux champs sont optionnels (résultats d'anciennes analyses) : toutes les
 * sections associées se dégradent gracieusement (listes/objets vides) s'ils sont absents.
 */
export default function AnalysisResultCard({ result }) {
  if (!result) return null;

  const {
    product_name,
    included = [],
    not_included = [],
    warnings = [],
    quality_score,
    supplier_score,
    profit_score,
    final_score,
    recommendation,
    detected_data = {},
    ai_estimations = {},
    missing_information = [],
    confidence_score,
    confidence_reasons = [],
    confidence_risks = [],
    mobile_summary,
    critical_alerts = [],
    ai_recommendation_summary,
    commercial_estimate,
    decision_badge,
    risk_level,
    supplier_reliability,
    margin_potential,
  } = result;

  const confidenceBand = getConfidenceBand(confidence_score);
  const detectedEntries = Object.entries(detected_data || {});
  const estimationEntries = Object.entries(ai_estimations || {});

  return (
    <div className="space-y-6">
      <QuickSummaryBar
        decisionBadge={decision_badge}
        finalScore={final_score}
        riskLevel={risk_level}
        supplierReliability={supplier_reliability}
        marginPotential={margin_potential}
      />

      <CriticalAlertsBanner alerts={critical_alerts} />

      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-6">
      {mobile_summary && (
        <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
          <Smartphone size={14} className="shrink-0 text-gray-400" />
          <span className="uppercase tracking-wide font-medium text-gray-400">
            Résumé compact (aperçu mobile)
          </span>
          <span className="text-gray-600 truncate">{mobile_summary}</span>
        </div>
      )}

      <div>
        <p className="text-xs uppercase tracking-wide text-gray-400 font-medium">
          Produit détecté
        </p>
        <h2 className="text-xl font-bold text-gray-900 mt-1">
          {product_name || "Nom non détecté"}
        </h2>
      </div>

      <RecommendationBanner recommendation={recommendation} />

      {ai_recommendation_summary && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-indigo-800 mb-2">
            <Bot size={16} /> Recommandation IA
          </h3>
          <p className="text-sm text-indigo-900">{ai_recommendation_summary}</p>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <ScoreBadge label="Qualité" score={quality_score} />
        <ScoreBadge label="Fournisseur" score={supplier_score} />
        <ScoreBadge label="Marge" score={profit_score} />
        <ScoreBadge label="Score final" score={final_score} />
      </div>

      {commercial_estimate && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-2">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
            <TrendingUp size={16} /> Estimation commerciale
          </h3>
          <p className="text-xs text-emerald-600 italic">Estimation générée par IA, pas une donnée confirmée</p>
          {commercial_estimate.possible ? (
            <dl className="grid sm:grid-cols-3 gap-3 mt-1">
              <div className="text-sm text-emerald-900">
                <dt className="text-xs font-medium text-emerald-600">Coût d'achat estimé</dt>
                <dd>{commercial_estimate.estimated_purchase_cost || "—"}</dd>
              </div>
              <div className="text-sm text-emerald-900">
                <dt className="text-xs font-medium text-emerald-600">Prix de revente conseillé</dt>
                <dd>{commercial_estimate.suggested_resale_price || "—"}</dd>
              </div>
              <div className="text-sm text-emerald-900">
                <dt className="text-xs font-medium text-emerald-600">Marge brute estimée</dt>
                <dd>{commercial_estimate.estimated_gross_margin || "—"}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-emerald-800 italic">
              Estimation non disponible : {commercial_estimate.reason_if_not_possible || "données insuffisantes."}
            </p>
          )}
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-6">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-green-700 mb-2">
            <CheckCircle size={16} /> Inclus dans la vente
          </h3>
          {included.length === 0 ? (
            <p className="text-sm text-gray-400 italic">Aucune information disponible</p>
          ) : (
            <ul className="space-y-1.5">
              {included.map((item, idx) => (
                <li key={idx} className="text-sm text-gray-700 flex gap-2">
                  <span className="text-green-600">✔</span> {item}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-red-700 mb-2">
            <XCircle size={16} /> Non inclus
          </h3>
          {not_included.length === 0 ? (
            <p className="text-sm text-gray-400 italic">Aucune information disponible</p>
          ) : (
            <ul className="space-y-1.5">
              {not_included.map((item, idx) => (
                <li key={idx} className="text-sm text-gray-700 flex gap-2">
                  <span className="text-red-600">❌</span> {item}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
            <ShieldAlert size={16} /> Score de confiance
          </h3>
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold text-gray-900">
              {Number(confidence_score) || 0}
              <span className="text-sm font-normal text-gray-400">/100</span>
            </span>
            <span
              className={clsx(
                "rounded-full border px-3 py-1 text-xs font-semibold",
                confidenceBand.classes
              )}
            >
              {confidenceBand.label}
            </span>
          </div>
        </div>
        {confidence_reasons.length > 0 && (
          <ul className="space-y-1.5">
            {confidence_reasons.map((item, idx) => (
              <li key={idx} className="text-sm text-gray-600 flex gap-2">
                <span className="text-gray-400">•</span> {item}
              </li>
            ))}
          </ul>
        )}
      </div>

      {confidence_risks.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-orange-800 mb-2">
            <AlertTriangle size={16} /> Risques identifiés
          </h3>
          <ul className="space-y-1.5">
            {confidence_risks.map((item, idx) => (
              <li key={idx} className="text-sm text-orange-800">
                • {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-6">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800 mb-2">
            <FileSearch size={16} /> Données détectées
          </h3>
          {detectedEntries.length === 0 ? (
            <p className="text-sm text-gray-400 italic">Aucune donnée détectée dans le texte source</p>
          ) : (
            <dl className="space-y-1.5">
              {detectedEntries.map(([key, value]) => (
                <div key={key} className="text-sm text-gray-700 flex gap-2">
                  <dt className="font-medium text-gray-500">{key} :</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>

        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-purple-700 mb-2">
            <Sparkles size={16} /> Estimations IA
          </h3>
          <p className="text-xs text-purple-500 italic mb-2">
            Estimation, pas une donnée confirmée
          </p>
          {estimationEntries.length === 0 ? (
            <p className="text-sm text-gray-400 italic">Aucune estimation IA disponible</p>
          ) : (
            <dl className="space-y-1.5">
              {estimationEntries.map(([key, value]) => (
                <div key={key} className="text-sm text-gray-700 flex gap-2">
                  <dt className="font-medium text-purple-500">{key} :</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>

      {missing_information.length > 0 && (
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-2">
            <HelpCircle size={16} /> Informations manquantes
          </h3>
          <ul className="space-y-1.5">
            {missing_information.map((item, idx) => (
              <li key={idx} className="text-sm text-gray-600 flex gap-2">
                <span className="text-gray-400">?</span> {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-800 mb-2">
            <AlertTriangle size={16} /> Risques et incertitudes
          </h3>
          <ul className="space-y-1.5">
            {warnings.map((item, idx) => (
              <li key={idx} className="text-sm text-amber-800">
                • {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-gray-400 border-t border-gray-100 pt-3">
        ⚠️ Cette analyse est générée par IA et ne garantit jamais un produit à 100%.
        Vérifiez toujours les informations directement auprès du vendeur avant achat.
      </p>
      </div>
    </div>
  );
}
