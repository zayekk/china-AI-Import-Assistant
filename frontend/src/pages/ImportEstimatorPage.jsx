import React, { useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, Loader2, Calculator } from "lucide-react";
import clsx from "clsx";
import { estimateImport } from "../services/importEstimateService";

const RECOMMENDATION_CONFIG = {
  ACHETER: {
    icon: CheckCircle2,
    label: "Acheter",
    classes: "bg-green-50 text-green-800 border-green-300",
  },
  NE_PAS_ACHETER: {
    icon: XCircle,
    label: "Ne pas acheter",
    classes: "bg-red-50 text-red-800 border-red-300",
  },
  A_ETUDIER: {
    icon: AlertTriangle,
    label: "À étudier",
    classes: "bg-orange-50 text-orange-800 border-orange-300",
  },
};

const INITIAL_FORM = {
  product_price_cny: "",
  quantity: "1",
  weight_kg: "",
  transport_method: "air",
  user_shipping_cost_cny: "",
  target_selling_price_eur: "",
  customs_duty_rate_pct: "0",
};

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return Number(value).toLocaleString("fr-FR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export default function ImportEstimatorPage() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (!form.product_price_cny || Number(form.product_price_cny) <= 0) {
      setError("Veuillez indiquer un prix produit (CNY) supérieur à 0.");
      return;
    }
    if (!form.weight_kg || Number(form.weight_kg) <= 0) {
      setError("Veuillez indiquer un poids estimé (kg) supérieur à 0.");
      return;
    }

    const payload = {
      product_price_cny: Number(form.product_price_cny),
      quantity: form.quantity ? Number(form.quantity) : 1,
      weight_kg: Number(form.weight_kg),
      transport_method: form.transport_method,
      user_shipping_cost_cny:
        form.user_shipping_cost_cny !== "" ? Number(form.user_shipping_cost_cny) : null,
      target_selling_price_eur:
        form.target_selling_price_eur !== "" ? Number(form.target_selling_price_eur) : null,
      customs_duty_rate_pct: form.customs_duty_rate_pct !== "" ? Number(form.customs_duty_rate_pct) : 0,
    };

    setLoading(true);
    try {
      const data = await estimateImport(payload);
      setResult(data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Une erreur est survenue lors du calcul de l'estimation."
      );
    } finally {
      setLoading(false);
    }
  };

  const recoConfig = result ? RECOMMENDATION_CONFIG[result.recommendation] || RECOMMENDATION_CONFIG.A_ETUDIER : null;
  const RecoIcon = recoConfig?.icon;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Estimer le coût d'importation</h1>
        <p className="text-gray-500 mt-1">
          Calculez le coût total d'un produit importé de Chine (produit + transport + douane),
          votre marge potentielle et une recommandation d'achat.
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Prix produit en Chine (CNY)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.product_price_cny}
                onChange={handleChange("product_price_cny")}
                placeholder="Ex: 50"
                className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Quantité</label>
              <input
                type="number"
                min="1"
                step="1"
                value={form.quantity}
                onChange={handleChange("quantity")}
                placeholder="Ex: 100"
                className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Poids total estimé (kg)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.weight_kg}
                onChange={handleChange("weight_kg")}
                placeholder="Ex: 20"
                className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Méthode de transport
              </label>
              <select
                value={form.transport_method}
                onChange={handleChange("transport_method")}
                className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
              >
                <option value="air">Avion</option>
                <option value="sea">Bateau</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Coût transport réel connu (CNY, optionnel)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.user_shipping_cost_cny}
                onChange={handleChange("user_shipping_cost_cny")}
                placeholder="Laisser vide pour estimer automatiquement"
                className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Prix de revente cible (EUR, optionnel)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.target_selling_price_eur}
                onChange={handleChange("target_selling_price_eur")}
                placeholder="Ex: 15"
                className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Droits de douane (%, optionnel)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.1"
                value={form.customs_duty_rate_pct}
                onChange={handleChange("customs_duty_rate_pct")}
                placeholder="Ex: 0"
                className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-medium px-6 py-3 rounded-xl transition-colors"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Calculator size={16} />}
            {loading ? "Calcul en cours..." : "Calculer l'estimation"}
          </button>
        </form>

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
            {error}
          </div>
        )}
      </div>

      {result && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-6">
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-400 font-medium">
              Résultat de l'estimation
            </p>
            <h2 className="text-xl font-bold text-gray-900 mt-1">Détail du coût d'importation</h2>
          </div>

          <div
            className={clsx(
              "flex items-center gap-3 rounded-xl border px-4 py-3 font-semibold",
              recoConfig.classes
            )}
          >
            <RecoIcon size={22} />
            <span>{recoConfig.label}</span>
          </div>

          {result.recommendation_reasons?.length > 0 && (
            <ul className="space-y-1.5">
              {result.recommendation_reasons.map((reason, idx) => (
                <li key={idx} className="text-sm text-gray-700 flex gap-2">
                  <span className="text-gray-400">•</span> {reason}
                </li>
              ))}
            </ul>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="rounded-xl border border-gray-200 p-3">
              <p className="text-xs text-gray-400">Coût produit</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatNumber(result.product_cost_cny)} CNY
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 p-3">
              <p className="text-xs text-gray-400">Coût transport</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatNumber(result.transport_cost_cny)} CNY
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 p-3">
              <p className="text-xs text-gray-400">Coût douane</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatNumber(result.customs_cost_cny)} CNY
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 p-3">
              <p className="text-xs text-gray-400">Total (CNY)</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatNumber(result.total_cost_cny)} CNY
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 p-3">
              <p className="text-xs text-gray-400">Total estimé (EUR)</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatNumber(result.total_cost_eur_estimated)} EUR
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 p-3">
              <p className="text-xs text-gray-400">Coût / unité</p>
              <p className="text-sm font-semibold text-gray-900">
                {formatNumber(result.cost_per_unit_cny)} CNY /{" "}
                {formatNumber(result.cost_per_unit_eur_estimated)} EUR
              </p>
            </div>
          </div>

          {(result.margin_amount_eur !== null || result.margin_percentage !== null) && (
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-gray-200 p-3">
                <p className="text-xs text-gray-400">Marge estimée</p>
                <p className="text-sm font-semibold text-gray-900">
                  {formatNumber(result.margin_amount_eur)} EUR
                </p>
              </div>
              <div className="rounded-xl border border-gray-200 p-3">
                <p className="text-xs text-gray-400">Marge (%)</p>
                <p className="text-sm font-semibold text-gray-900">
                  {formatNumber(result.margin_percentage)} %
                </p>
              </div>
            </div>
          )}

          {result.assumptions?.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-800 mb-2">
                <AlertTriangle size={16} /> Hypothèses de calcul
              </h3>
              <ul className="space-y-1.5">
                {result.assumptions.map((item, idx) => (
                  <li key={idx} className="text-sm text-amber-800">
                    • {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-xs text-gray-400 border-t border-gray-100 pt-3">
            ⚠️ Estimation basée sur des tarifs et un taux de change indicatifs, non
            temps réel. Vérifiez toujours les coûts réels (transporteur, douane) avant
            de vous engager.
          </p>
        </div>
      )}
    </div>
  );
}
