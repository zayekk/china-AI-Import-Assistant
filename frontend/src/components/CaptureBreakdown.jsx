import React from "react";
import { Copy, ImageOff, Layers, CheckCircle2, AlertTriangle } from "lucide-react";
import clsx from "clsx";

// Métadonnées d'affichage par catégorie de capture, alignées sur `CAPTURE_CATEGORIES`
// côté serveur (ai_engine/services/multi_capture_service.py).
const CATEGORY_META = {
  main_page: { label: "Page principale", classes: "bg-blue-50 text-blue-700 border-blue-200" },
  product_info: { label: "Infos produit", classes: "bg-purple-50 text-purple-700 border-purple-200" },
  shop: { label: "Boutique", classes: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  reviews: { label: "Avis clients", classes: "bg-amber-50 text-amber-700 border-amber-200" },
  shipping: { label: "Livraison", classes: "bg-cyan-50 text-cyan-700 border-cyan-200" },
  other: { label: "Autre", classes: "bg-gray-100 text-gray-600 border-gray-200" },
};

const MISSING_CATEGORY_MESSAGES = {
  main_page: "Aucune capture de la page principale (prix, promotion) détectée — pensez à en ajouter une.",
  product_info: "Aucune capture des informations produit (matière, taille, couleur) détectée — pensez à en ajouter une.",
  shop: "Aucune capture de la boutique/vendeur détectée — pensez à en ajouter une pour évaluer la fiabilité du vendeur.",
  reviews: "Aucune capture des avis clients détectée — pensez à en ajouter une pour une analyse plus fiable.",
  shipping: "Aucune capture des conditions de livraison détectée — pensez à en ajouter une.",
};

function getCategoryMeta(category) {
  return CATEGORY_META[category] || CATEGORY_META.other;
}

/**
 * Affiche le détail d'une analyse multi-captures :
 * - la liste des captures envoyées, classées par catégorie, avec mention des doublons détectés
 * - un résumé des catégories couvertes / manquantes pour aider l'utilisateur à compléter son scan
 */
export default function CaptureBreakdown({ captures = [], categoriesCovered = [], categoriesMissing = [] }) {
  if (!captures || captures.length === 0) return null;

  const duplicateCount = captures.filter((c) => c.is_duplicate).length;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
          <Layers size={16} /> Détail des captures analysées ({captures.length})
        </h3>
        {duplicateCount > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-gray-300 bg-gray-50 px-3 py-1 text-xs font-medium text-gray-600">
            <Copy size={12} /> {duplicateCount} doublon{duplicateCount > 1 ? "s" : ""} détecté{duplicateCount > 1 ? "s" : ""}
          </span>
        )}
      </div>

      <ul className="divide-y divide-gray-100 border border-gray-100 rounded-xl overflow-hidden">
        {captures.map((capture) => {
          const meta = getCategoryMeta(capture.category);
          return (
            <li
              key={capture.index}
              className={clsx(
                "flex items-center justify-between gap-3 px-4 py-3 text-sm",
                capture.is_duplicate ? "bg-gray-50" : "bg-white"
              )}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="text-xs font-mono text-gray-400 w-6 shrink-0">#{capture.index + 1}</span>
                <span
                  className={clsx(
                    "truncate text-gray-700",
                    capture.is_duplicate && "line-through text-gray-400"
                  )}
                  title={capture.filename}
                >
                  {capture.filename}
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {capture.is_duplicate && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-500">
                    <Copy size={11} />
                    Doublon
                    {typeof capture.duplicate_of_index === "number" &&
                      ` de #${capture.duplicate_of_index + 1}`}
                  </span>
                )}
                {!capture.ocr_excerpt && (
                  <span
                    className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600"
                    title="Aucun texte détecté sur cette capture"
                  >
                    <ImageOff size={11} /> Illisible
                  </span>
                )}
                <span
                  className={clsx(
                    "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
                    meta.classes
                  )}
                >
                  {meta.label}
                </span>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <h4 className="flex items-center gap-2 text-sm font-semibold text-green-700 mb-2">
            <CheckCircle2 size={16} /> Catégories couvertes
          </h4>
          {categoriesCovered.length === 0 ? (
            <p className="text-sm text-gray-400 italic">Aucune catégorie identifiée</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {categoriesCovered.map((cat) => {
                const meta = getCategoryMeta(cat);
                return (
                  <span
                    key={cat}
                    className={clsx(
                      "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
                      meta.classes
                    )}
                  >
                    {meta.label}
                  </span>
                );
              })}
            </div>
          )}
        </div>

        <div>
          <h4 className="flex items-center gap-2 text-sm font-semibold text-orange-700 mb-2">
            <AlertTriangle size={16} /> Catégories manquantes
          </h4>
          {categoriesMissing.length === 0 ? (
            <p className="text-sm text-green-600 italic">Toutes les catégories clés sont couvertes 🎉</p>
          ) : (
            <ul className="space-y-1.5">
              {categoriesMissing.map((cat) => (
                <li key={cat} className="text-sm text-orange-800 flex gap-2">
                  <span>⚠️</span>
                  <span>{MISSING_CATEGORY_MESSAGES[cat] || `Aucune capture "${cat}" détectée.`}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
