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
  Award,
  Activity,
  Cpu,
  Repeat,
} from "lucide-react";
import clsx from "clsx";
import RecommendationBanner from "./RecommendationBanner";
import ScoreBadge from "./ScoreBadge";
import QuickSummaryBar from "./QuickSummaryBar";
import CriticalAlertsBanner from "./CriticalAlertsBanner";
import QuickReportBanner from "./QuickReportBanner";
import ImportDecisionCard from "./ImportDecisionCard";
import StarRating from "./StarRating";
import DecisionReasonsList from "./DecisionReasonsList";
import WinningProductBadge from "./WinningProductBadge";
import CompetitionCard from "./CompetitionCard";
import DataConfidenceCard from "./DataConfidenceCard";
import MarketPositionCard from "./MarketPositionCard";
import ImportCostCalculatorCard from "./ImportCostCalculatorCard";
import ReviewsInsightCard from "./ReviewsInsightCard";
import SupplierProfileCard from "./SupplierProfileCard";
import TargetAudienceCard from "./TargetAudienceCard";
import ImportStrategyCard from "./ImportStrategyCard";
import SeasonalityCard from "./SeasonalityCard";
import SaturationCard from "./SaturationCard";
import ComplementaryProductsCard from "./ComplementaryProductsCard";
import LogisticsCard from "./LogisticsCard";
import ImportDifficultyCard from "./ImportDifficultyCard";
import MarketingClaimsCard from "./MarketingClaimsCard";
import ImporterSummaryCard from "./ImporterSummaryCard";

// Bandes de confiance : bornes STRICTEMENT alignées sur `_confidence_level()` côté serveur
// (backend/ai_engine/services/product_analysis_service.py) : 0-30 / 31-60 / 61-80 / 81-100.
const CONFIDENCE_BANDS = [
  { max: 30, label: "Données insuffisantes", classes: "bg-red-50 text-red-800 border-red-300" },
  { max: 60, label: "Analyse approximative", classes: "bg-orange-50 text-orange-800 border-orange-300" },
  { max: 80, label: "Analyse fiable", classes: "bg-blue-50 text-blue-800 border-blue-300" },
  { max: 100, label: "Forte confiance", classes: "bg-green-50 text-green-800 border-green-300" },
];

// Niveaux de demande marché : clés STRICTEMENT alignées sur _normalize_demand_level()
// côté serveur (ai_engine/services/product_analysis_service.py).
const DEMAND_META = {
  very_high: { label: "Très forte", classes: "bg-green-50 text-green-700 border-green-200" },
  high: { label: "Forte", classes: "bg-lime-50 text-lime-700 border-lime-200" },
  medium: { label: "Moyenne", classes: "bg-yellow-50 text-yellow-700 border-yellow-200" },
  low: { label: "Faible", classes: "bg-orange-50 text-orange-700 border-orange-200" },
  very_low: { label: "Très faible", classes: "bg-red-50 text-red-700 border-red-200" },
};

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
    commercial_potential_rating,
    commercial_potential_explanation,
    import_decision,
    import_decision_explanation,
    market_comparisons = [],
    demand_level,
    demand_explanation,
    quick_report = [],
    decision_reasons = [],
    winning_product_score,
    winning_product_explanation,
    competition_level,
    competition_explanation,
    data_confidence,
    average_market_price,
    market_positioning,
    market_positioning_explanation,
    resale_ease_rating,
    resale_ease_explanation,
    reviews_available,
    review_highlights = [],
    review_complaints = [],
    review_satisfaction,
    review_recurring_defects = [],
    supplier_profile,
    target_audiences = [],
    target_audience_explanation,
    import_strategy,
    seasonality,
    saturation_level,
    saturation_explanation,
    complementary_products = [],
    logistics_profile,
    recommended_transport,
    transport_explanation,
    import_difficulty,
    import_difficulty_explanation,
    marketing_claims = [],
    importer_summary = [],
  } = result;

  const confidenceBand = getConfidenceBand(confidence_score);
  const detectedEntries = Object.entries(detected_data || {});
  const estimationEntries = Object.entries(ai_estimations || {});
  const demandMeta = DEMAND_META[demand_level] || DEMAND_META.medium;

  return (
    <div className="space-y-6">
      <QuickSummaryBar
        decisionBadge={decision_badge}
        finalScore={final_score}
        riskLevel={risk_level}
        supplierReliability={supplier_reliability}
        marginPotential={margin_potential}
      />

      <QuickReportBanner items={quick_report} />

      <CriticalAlertsBanner alerts={critical_alerts} />

      {import_decision && (
        <ImportDecisionCard decision={import_decision} explanation={import_decision_explanation} />
      )}

      <DecisionReasonsList reasons={decision_reasons} />

      {(winning_product_score != null || competition_level) && (
        <div className="grid sm:grid-cols-2 gap-4">
          {winning_product_score != null && (
            <WinningProductBadge score={winning_product_score} explanation={winning_product_explanation} />
          )}
          {competition_level && (
            <CompetitionCard level={competition_level} explanation={competition_explanation} />
          )}
        </div>
      )}

      <SupplierProfileCard profile={supplier_profile} />

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

      {(commercial_potential_rating || demand_level || resale_ease_rating) && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {commercial_potential_rating != null && (
            <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-2">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                <Award size={16} /> Potentiel commercial
              </h3>
              <StarRating rating={commercial_potential_rating} />
              {commercial_potential_explanation && (
                <p className="text-sm text-gray-600">{commercial_potential_explanation}</p>
              )}
            </div>
          )}

          {demand_level && (
            <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                  <Activity size={16} /> Demande du marché
                </h3>
                <span className={clsx("rounded-full border px-3 py-1 text-xs font-semibold", demandMeta.classes)}>
                  {demandMeta.label}
                </span>
              </div>
              {demand_explanation && <p className="text-sm text-gray-600">{demand_explanation}</p>}
            </div>
          )}

          {resale_ease_rating != null && (
            <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-2">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                <Repeat size={16} /> Facilité de revente
              </h3>
              <StarRating rating={resale_ease_rating} />
              {resale_ease_explanation && (
                <p className="text-sm text-gray-600">{resale_ease_explanation}</p>
              )}
            </div>
          )}
        </div>
      )}

      <TargetAudienceCard audiences={target_audiences} explanation={target_audience_explanation} />

      <ImportCostCalculatorCard estimate={commercial_estimate} />

      <ImportStrategyCard
        suggestedQuantity={import_strategy?.suggested_initial_quantity}
        quantityReason={import_strategy?.quantity_reason}
        salesTips={import_strategy?.sales_tips}
        launchStrategy={import_strategy?.launch_strategy}
      />

      <ComplementaryProductsCard products={complementary_products} />

      {market_comparisons.length > 0 && (
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800 mb-2">
            <Cpu size={16} /> Comparaison technique
          </h3>
          <ul className="space-y-2">
            {market_comparisons.map((item, idx) => (
              <li key={idx} className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
                <p className="text-sm">
                  <span className="font-semibold text-gray-800">{item.component}</span>
                  <span className="text-gray-400"> · </span>
                  <span className="text-gray-600">{item.detected_value}</span>
                </p>
                <p className="text-sm text-gray-700 mt-0.5">{item.comparison}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(competition_level || average_market_price || market_positioning) && (
        <MarketPositionCard
          competitionLevel={competition_level}
          averageMarketPrice={average_market_price}
          positioning={market_positioning}
          positioningExplanation={market_positioning_explanation}
        />
      )}

      {(seasonality || saturation_level) && (
        <div className="grid sm:grid-cols-2 gap-4">
          {seasonality && (
            <SeasonalityCard
              isSeasonal={seasonality?.is_seasonal}
              idealPeriod={seasonality?.ideal_period}
              favorableMonths={seasonality?.favorable_months}
              unfavorableMonths={seasonality?.unfavorable_months}
            />
          )}
          {saturation_level && (
            <SaturationCard level={saturation_level} explanation={saturation_explanation} />
          )}
        </div>
      )}

      {(logistics_profile || recommended_transport || import_difficulty) && (
        <div className="grid sm:grid-cols-2 gap-4">
          {(logistics_profile || recommended_transport) && (
            <LogisticsCard
              profile={logistics_profile}
              recommendedTransport={recommended_transport}
              transportExplanation={transport_explanation}
            />
          )}
          {import_difficulty && (
            <ImportDifficultyCard level={import_difficulty} explanation={import_difficulty_explanation} />
          )}
        </div>
      )}

      <ReviewsInsightCard
        highlights={review_highlights}
        complaints={review_complaints}
        satisfaction={review_satisfaction}
        recurringDefects={review_recurring_defects}
        available={reviews_available}
      />

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

      <DataConfidenceCard confidence={data_confidence} />

      <MarketingClaimsCard claims={marketing_claims} />

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

      <ImporterSummaryCard lines={importer_summary} />

      <p className="text-xs text-gray-400 border-t border-gray-100 pt-3">
        ⚠️ Cette analyse est générée par IA et ne garantit jamais un produit à 100%.
        Vérifiez toujours les informations directement auprès du vendeur avant achat.
      </p>
      </div>
    </div>
  );
}
