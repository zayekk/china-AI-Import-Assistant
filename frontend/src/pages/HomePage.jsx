import React from "react";
import { Link } from "react-router-dom";
import { Search, ShoppingBag, ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Bienvenue sur China AI Import Assistant
        </h1>
        <p className="text-gray-500 mt-1">
          Analysez vos produits avant achat et découvrez des opportunités gagnantes.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 gap-5">
        <Link
          to="/analyze"
          className="bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-md transition-shadow group"
        >
          <div className="w-12 h-12 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center mb-4">
            <Search size={22} />
          </div>
          <h2 className="font-semibold text-lg text-gray-900">Analyser un produit</h2>
          <p className="text-sm text-gray-500 mt-1.5">
            Collez un lien, envoyez une capture d'écran ou du texte chinois pour détecter
            les pièges avant achat.
          </p>
          <span className="inline-flex items-center gap-1 text-brand-600 text-sm font-medium mt-4 group-hover:gap-2 transition-all">
            Commencer <ArrowRight size={14} />
          </span>
        </Link>

        <Link
          to="/scrape"
          className="bg-white rounded-2xl border border-gray-200 p-6 hover:shadow-md transition-shadow group"
        >
          <div className="w-12 h-12 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center mb-4">
            <ShoppingBag size={22} />
          </div>
          <h2 className="font-semibold text-lg text-gray-900">Scanner des produits</h2>
          <p className="text-sm text-gray-500 mt-1.5">
            Lancez le scraper sur une fiche produit pour récupérer toutes ses données et
            évaluer le fournisseur.
          </p>
          <span className="inline-flex items-center gap-1 text-brand-600 text-sm font-medium mt-4 group-hover:gap-2 transition-all">
            Scanner <ArrowRight size={14} />
          </span>
        </Link>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
        ⚠️ China AI Import Assistant aide à repérer les risques courants, mais ne garantit
        jamais un produit à 100%. Vérifiez toujours les informations auprès du vendeur.
      </div>
    </div>
  );
}
