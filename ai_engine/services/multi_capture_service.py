"""
Service d'analyse multi-captures intelligente.

L'utilisateur envoie entre 5 et 12 captures d'écran d'une même fiche produit
(Pinduoduo / Taobao / 1688). Ce service :
1. Extrait le texte OCR de chaque capture (réutilise `ocr_service`).
2. Calcule un hash perceptuel (pHash) de chaque image pour détecter les doublons.
3. Classe chaque capture par catégorie (page principale, infos produit, boutique,
   avis, livraison) à partir de mots-clés locaux (FR/EN/中文简体).
4. Construit un texte structuré par catégorie (en excluant les doublons) et
   déclenche UNE analyse IA consolidée, en réutilisant le même contrat de sortie
   et le même filet de sécurité local que `analyze_product_text()`.
"""
import copy
import io
import logging

import imagehash
from PIL import Image

from ai_engine.prompts.product_prompts import (
    DEFAULT_LANGUAGE,
    build_system_prompt,
    build_user_prompt_for_multi_capture_analysis,
)
from ai_engine.services.mistral_client import MistralAPIError, mistral_client
from ai_engine.services.ocr_service import OCRError, extract_text_from_image_bytes
from ai_engine.services.product_analysis_service import (
    _apply_local_safety_net,
    _fallback_result,
    _normalize_ai_result,
)
from ai_engine.services.timing import StepTimer, log_step

logger = logging.getLogger(__name__)

# Catégories canoniques de captures. Toute capture ne correspondant à aucun mot-clé
# connu retombe sur la catégorie de repli "other" (volontairement absente de cette liste,
# car "other" n'est jamais considérée comme une catégorie "couverte" attendue par l'utilisateur).
CAPTURE_CATEGORIES = ["main_page", "product_info", "shop", "reviews", "shipping"]

# Distance de Hamming maximale (pHash) en-dessous de laquelle deux captures sont
# considérées comme des doublons (quasi-)identiques.
DUPLICATE_HAMMING_THRESHOLD = 8

# Longueur de l'extrait OCR conservé par capture (audit / debug).
OCR_EXCERPT_LENGTH = 200

# Mots-clés par catégorie (français / anglais / chinois simplifié).
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "main_page": [
        "prix", "price", "¥", "promotion", "vente", "ventes", "sales", "sold",
        "已售", "价格", "折扣", "券后价",
    ],
    "product_info": [
        "matière", "material", "taille", "size", "couleur", "color", "poids", "weight",
        "variante", "variant", "材质", "尺码", "颜色", "重量", "规格",
    ],
    "shop": [
        "vendeur", "seller", "boutique", "shop", "store", "ancienneté", "badge",
        "店铺", "掌柜", "信誉", "卖家",
    ],
    "reviews": [
        "avis", "review", "reviews", "comment", "commentaire", "note client", "rating",
        "评价", "评论", "买家秀", "好评",
    ],
    "shipping": [
        "livraison", "shipping", "delivery", "frais de port", "délai", "expédition",
        "发货", "运费", "快递", "包邮",
    ],
}


def classify_capture_category(ocr_text: str) -> str:
    """
    Classe un texte OCR dans l'une des catégories canoniques (`CAPTURE_CATEGORIES`)
    en comptant les occurrences de mots-clés (insensible à la casse pour le latin).
    Retourne "other" si aucune catégorie n'obtient de correspondance.
    """
    if not ocr_text:
        return "other"

    text_lower = ocr_text.lower()
    best_category = "other"
    best_count = 0

    for category in CAPTURE_CATEGORIES:
        count = sum(text_lower.count(keyword.lower()) for keyword in CATEGORY_KEYWORDS[category])
        if count > best_count:
            best_count = count
            best_category = category

    return best_category


def compute_phash(image_bytes: bytes) -> str:
    """Calcule le hash perceptuel (pHash) d'une image et le retourne sous forme de string hexadécimale."""
    image = Image.open(io.BytesIO(image_bytes))
    return str(imagehash.phash(image))


def detect_duplicates(hashes: list[str]) -> dict[int, int]:
    """
    Détecte les captures dupliquées à partir de leurs hashes perceptuels.

    Pour chaque capture (par index, dans l'ordre d'envoi), compare son hash à ceux des
    captures précédentes NON dupliquées déjà vues. Si la distance de Hamming est
    <= DUPLICATE_HAMMING_THRESHOLD, la capture courante est marquée comme doublon de
    la première occurrence rencontrée.

    Retourne un dict {index_doublon: index_original} (n'inclut que les doublons).
    """
    duplicates: dict[int, int] = {}
    seen_originals: list[tuple[int, "imagehash.ImageHash"]] = []

    for idx, hex_hash in enumerate(hashes):
        current_hash = imagehash.hex_to_hash(hex_hash)

        original_idx = None
        for seen_idx, seen_hash in seen_originals:
            if current_hash - seen_hash <= DUPLICATE_HAMMING_THRESHOLD:
                original_idx = seen_idx
                break

        if original_idx is not None:
            duplicates[idx] = original_idx
        else:
            seen_originals.append((idx, current_hash))

    return duplicates


def analyze_multi_capture(
    captures: list[tuple[str, bytes]],
    category_hints: list[str] | None = None,
    language: str = DEFAULT_LANGUAGE,
) -> dict:
    """
    Pipeline complet d'analyse multi-captures.

    `captures` : liste de (filename, image_bytes) dans l'ordre d'envoi, déjà validée
    (5 à 12 éléments) par l'endpoint appelant — cette fonction ne revalide pas la taille du lot.

    `category_hints` : catégorie déjà connue pour chaque capture, alignée par index avec
    `captures` (ex: scan guidé, où l'utilisateur a suivi une instruction précise par étape).
    Plus fiable que la classification automatique par mots-clés. Optionnel : si absent, ou
    si sa longueur ne correspond pas à celle de `captures`, la classification automatique
    est utilisée pour toutes les captures (comportement inchangé). Si un hint individuel
    n'est pas une catégorie canonique valide, on retombe sur la classification automatique
    pour CETTE capture uniquement.

    `language` : langue cible du rapport ("fr"/"en", choisie par l'utilisateur) — voir
    `analyze_product_text()` dans product_analysis_service.py pour le détail du mécanisme.

    Retourne un dict respectant le contrat `AIAnalysisResult` complet, plus les clés
    "captures", "categories_covered" et "categories_missing".
    """
    # a. OCR de chaque capture (tolérant : une capture en échec ne fait pas échouer le lot).
    ocr_timer = StepTimer()
    ocr_texts: list[str] = []
    ocr_failed_flags: list[bool] = []
    for filename, image_bytes in captures:
        try:
            text = extract_text_from_image_bytes(image_bytes)
            ocr_failed_flags.append(False)
        except OCRError as exc:
            logger.warning("Échec OCR pour la capture '%s': %s", filename, exc)
            text = ""
            ocr_failed_flags.append(True)
        ocr_texts.append(text)
    log_step(
        "ocr",
        ocr_timer.elapsed(),
        captures_count=len(captures),
        failed_count=sum(ocr_failed_flags),
    )

    # b. Hash perceptuel + détection des doublons.
    fusion_timer = StepTimer()
    hashes = [compute_phash(image_bytes) for _, image_bytes in captures]
    duplicates_map = detect_duplicates(hashes)  # {index_doublon: index_original}

    # c. Classification de chaque capture (y compris les doublons).
    if category_hints is not None and len(category_hints) == len(captures):
        categories = [
            hint if hint in CAPTURE_CATEGORIES else classify_capture_category(text)
            for hint, text in zip(category_hints, ocr_texts)
        ]
    else:
        categories = [classify_capture_category(text) for text in ocr_texts]

    # d. Texte structuré par catégorie, uniquement à partir des captures NON dupliquées,
    #    triées par catégorie canonique puis par ordre d'arrivée.
    categorized_sections: dict[str, list[str]] = {cat: [] for cat in CAPTURE_CATEGORIES}
    categorized_sections["other"] = []

    for idx, text in enumerate(ocr_texts):
        if idx in duplicates_map:
            continue  # exclu de l'agrégation pour ne pas fausser l'analyse IA
        if not text:
            continue
        categorized_sections[categories[idx]].append(text)

    # Nettoie les catégories vides (le prompt builder les ignore de toute façon).
    categorized_sections = {cat: texts for cat, texts in categorized_sections.items() if texts}

    # e. Filet de sécurité local : mots-clés pièges sur le texte agrégé complet.
    aggregated_text = "\n".join(
        text for texts in categorized_sections.values() for text in texts
    )
    log_step(
        "fusion",
        fusion_timer.elapsed(),
        duplicates_count=len(duplicates_map),
        categories_count=len(categorized_sections),
        aggregated_chars=len(aggregated_text),
    )

    # f. Appel IA consolidé (même contrat que analyze_product_text), avec fallback gracieux.
    language = language if language in ("fr", "en") else DEFAULT_LANGUAGE
    try:
        prompt_timer = StepTimer()
        user_prompt = build_user_prompt_for_multi_capture_analysis(categorized_sections)
        system_prompt = build_system_prompt(language)
        log_step(
            "prompt_build",
            prompt_timer.elapsed(),
            system_chars=len(system_prompt),
            user_chars=len(user_prompt),
        )
        raw_result = mistral_client.chat_completion_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        normalize_timer = StepTimer()
        result = _normalize_ai_result(raw_result, language)
        log_step("normalize", normalize_timer.elapsed())
    except MistralAPIError as exc:
        # Log explicite AVANT le repli, avec le type d'exception d'origine — voir la note
        # équivalente dans product_analysis_service.py::analyze_product_text().
        logger.error(
            "Échec de l'appel Mistral (analyse multi-captures) — repli local activé. Cause : [%s] %s",
            type(exc).__name__,
            exc,
        )
        # deepcopy : voir la note équivalente dans product_analysis_service.py.
        result = copy.deepcopy(_fallback_result(language))
        result["product_name"] = aggregated_text[:120]

    result = _apply_local_safety_net(result, aggregated_text, language)

    # f-bis. Confiance OCR : écrase l'estimation IA (qui ne peut que deviner) par le taux réel de
    # captures exploitées avec succès par l'OCR — donnée déterministe déjà calculée ci-dessus,
    # bien plus fiable qu'un jugement IA sur ce point précis pour une analyse multi-captures.
    if ocr_failed_flags:
        successful_ratio = sum(1 for failed in ocr_failed_flags if not failed) / len(ocr_failed_flags)
        result["data_confidence"]["ocr"] = round(successful_ratio * 100)

    # g. Détail de classification par capture + couverture des catégories.
    captures_detail = []
    for idx, (filename, _) in enumerate(captures):
        is_duplicate = idx in duplicates_map
        capture_info = {
            "index": idx,
            "filename": filename,
            "category": categories[idx],
            "is_duplicate": is_duplicate,
            "duplicate_of_index": duplicates_map.get(idx),
            "ocr_excerpt": ocr_texts[idx][:OCR_EXCERPT_LENGTH],
            "ocr_failed": ocr_failed_flags[idx],
        }
        captures_detail.append(capture_info)

    categories_covered = [cat for cat in CAPTURE_CATEGORIES if categorized_sections.get(cat)]
    categories_missing = [cat for cat in CAPTURE_CATEGORIES if cat not in categories_covered]

    result["captures"] = captures_detail
    result["categories_covered"] = categories_covered
    result["categories_missing"] = categories_missing

    return result
