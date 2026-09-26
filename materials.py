"""
Small reference database of common packaging materials.
Used to ground the AI's recommendation with real typical ranges
instead of letting it invent OTR/WVTR/cost numbers from scratch.

CHANGES IN THIS VERSION
------------------------
1. get_relevant_materials() now SCORES materials using moisture, fat and
   budget (previously it only keyword-matched on food_type + respiration),
   so the "best fit first" ordering handed to Gemini is actually reasoned,
   not just topic-matched.
2. NEW: validate_recommendation() runs AFTER Gemini responds. It checks the
   material Gemini named is actually in our filtered list, and clamps
   cost/MAP numbers that drift outside realistic bounds for that material's
   cost tier / food category. It never silently rewrites the AI's text --
   it only adjusts the numeric JSON fields and attaches a flag so the
   frontend can show the user whether a number was database-verified or
   just an AI estimate.
"""

import re

MATERIALS_DB = [
    {
        "name": "LDPE (Low-Density Polyethylene)",
        "otr_cc_m2_day": "150-300",
        "wvtr_g_m2_day": "10-20",
        "typical_thickness_micron": "25-100",
        "cost_tier": "Low",
        "mechanical_strength": "Medium — stretchy, resists punctures well",
        "sealability": "Heat-sealable at 120-160°C",
        "recyclable": True,
        "biodegradable": False,
        "best_for": ["dry snacks", "bread", "frozen food", "general pouches"],
    },
    {
        "name": "HDPE (High-Density Polyethylene)",
        "otr_cc_m2_day": "100-200",
        "wvtr_g_m2_day": "5-10",
        "typical_thickness_micron": "30-150",
        "cost_tier": "Low",
        "mechanical_strength": "High — stiff and impact-resistant",
        "sealability": "Heat-sealable at 130-170°C (rigid parts may need induction sealing)",
        "recyclable": True,
        "biodegradable": False,
        "best_for": ["milk pouches/bottles", "dry grains", "rigid containers"],
    },
    {
        "name": "PET (Polyethylene Terephthalate)",
        "otr_cc_m2_day": "3-8",
        "wvtr_g_m2_day": "1-3",
        "typical_thickness_micron": "12-50",
        "cost_tier": "Medium",
        "mechanical_strength": "High — stiff, good stacking strength",
        "sealability": "Not directly heat-sealable; usually sealed via a coated inner layer",
        "recyclable": True,
        "biodegradable": False,
        "best_for": ["beverages", "sauces", "premium/export snacks"],
    },
    {
        "name": "BOPP (Biaxially Oriented Polypropylene)",
        "otr_cc_m2_day": "1500-2000",
        "wvtr_g_m2_day": "5-8",
        "typical_thickness_micron": "15-40",
        "cost_tier": "Low",
        "mechanical_strength": "Medium — good tensile strength, crisp fold",
        "sealability": "Heat-sealable at 130-150°C",
        "recyclable": True,
        "biodegradable": False,
        "best_for": ["chips", "namkeen", "fried snacks"],
    },
    {
        "name": "Metalized BOPP/PET film",
        "otr_cc_m2_day": "0.5-2",
        "wvtr_g_m2_day": "0.2-1",
        "typical_thickness_micron": "18-30",
        "cost_tier": "Medium",
        "mechanical_strength": "Medium — similar to base film, slightly stiffer",
        "sealability": "Heat-sealable at 120-150°C",
        "recyclable": False,
        "biodegradable": False,
        "best_for": ["oily/fried snacks needing long shelf life", "coffee"],
    },
    {
        "name": "Aluminum foil laminate",
        "otr_cc_m2_day": "~0 (near-total barrier)",
        "wvtr_g_m2_day": "~0 (near-total barrier)",
        "typical_thickness_micron": "7-12 (foil layer)",
        "cost_tier": "High",
        "mechanical_strength": "High — rigid, puncture and crush resistant",
        "sealability": "Heat-sealable at 150-190°C (retort-grade seals)",
        "recyclable": False,
        "biodegradable": False,
        "best_for": ["retort pouches", "long-life dairy/meat", "premium export"],
    },
    {
        "name": "Micro-perforated PP/PE film",
        "otr_cc_m2_day": "Tunable via perforation density",
        "wvtr_g_m2_day": "Tunable via perforation density",
        "typical_thickness_micron": "20-40",
        "cost_tier": "Low-Medium",
        "mechanical_strength": "Medium — flexible, tears easily at perforations by design",
        "sealability": "Heat-sealable at 120-150°C",
        "recyclable": True,
        "biodegradable": False,
        "best_for": ["fresh fruits", "vegetables", "high-respiration produce"],
    },
    {
        "name": "Bagasse (sugarcane waste) trays/clamshells",
        "otr_cc_m2_day": "Not a gas barrier material",
        "wvtr_g_m2_day": "Moderate-high (porous)",
        "typical_thickness_micron": "N/A (molded, 1-3mm)",
        "cost_tier": "Low-Medium",
        "mechanical_strength": "Medium — rigid molded shape, can crack under heavy load",
        "sealability": "Not heat-sealable; closes with a lid, clip or paper band",
        "recyclable": True,
        "biodegradable": True,
        "best_for": ["fresh produce trays", "ready-to-eat", "eco-conscious brands"],
    },
    {
        "name": "Areca nut sheath plates/trays",
        "otr_cc_m2_day": "Not a gas barrier material",
        "wvtr_g_m2_day": "Moderate-high (porous)",
        "typical_thickness_micron": "N/A (natural sheath)",
        "cost_tier": "Low",
        "mechanical_strength": "Low-Medium — rigid but can crack under pressure",
        "sealability": "Not heat-sealable; used as open trays/plates",
        "recyclable": True,
        "biodegradable": True,
        "best_for": ["fresh produce", "snacks (short shelf life)", "local/rural sale"],
    },
    {
        "name": "Corn-starch / PLA-based film",
        "otr_cc_m2_day": "100-300",
        "wvtr_g_m2_day": "10-30",
        "typical_thickness_micron": "20-40",
        "cost_tier": "Medium-High",
        "mechanical_strength": "Medium — flexible but more brittle in cold conditions",
        "sealability": "Heat-sealable at 100-140°C (lower than regular plastic)",
        "recyclable": False,
        "biodegradable": True,
        "best_for": ["dry snacks", "bakery", "eco-positioned brands"],
    },
    {
        "name": "Jute or cotton pouches",
        "otr_cc_m2_day": "Not a gas barrier material",
        "wvtr_g_m2_day": "High (breathable)",
        "typical_thickness_micron": "N/A (woven)",
        "cost_tier": "Low-Medium",
        "mechanical_strength": "Medium — strong against tearing, no puncture resistance",
        "sealability": "Not heat-sealable; closed by stitching or drawstring",
        "recyclable": True,
        "biodegradable": True,
        "best_for": ["grains", "pulses", "onions/garlic (breathable storage)"],
    },
    {
        "name": "Paper/kraft laminate",
        "otr_cc_m2_day": "Varies with lamination",
        "wvtr_g_m2_day": "Moderate (depends on coating)",
        "typical_thickness_micron": "40-120 (gsm-based)",
        "cost_tier": "Low-Medium",
        "mechanical_strength": "Low-Medium — depends on gsm and lamination",
        "sealability": "Heat-sealable only if it has a poly/wax coating",
        "recyclable": True,
        "biodegradable": True,
        "best_for": ["dry snacks", "bakery", "eco-friendly retail packs"],
    },
]

KEYWORD_MAP = {
    "fresh produce": ["fresh", "produce", "vegetable", "fruit"],
    "dry": ["dry", "grain", "pulse"],
    "snack": ["snack", "chips", "namkeen", "fried"],
    "dairy": ["dairy", "milk"],
    "meat": ["meat", "seafood", "retort"],
    "processed": ["ready-to-eat", "processed"],
}

# Typical realistic MAP gas-mix bounds by rough food category, used only to
# CLAMP whatever percentages Gemini returns, not to generate them from scratch.
MAP_BOUNDS = {
    "fresh produce": (1, 5, 3, 10),   # o2_low, o2_high, co2_low, co2_high
    "dry": (0, 2, 0, 5),
    "snack": (0, 2, 0, 5),
    "dairy": (0, 1, 20, 40),
    "meat": (60, 85, 15, 40),
    "processed": (0, 5, 10, 30),
}

# Indicative INR/unit bands per cost tier, used only to flag numbers that are
# wildly off (e.g. Gemini saying a "Low" tier film costs Rs 50/unit).
COST_TIER_BANDS_INR = {
    "low": (1, 3),
    "low-medium": (2, 4),
    "medium": (3, 6),
    "medium-high": (5, 8),
    "high": (7, 15),
}


def _detect_category(food_type: str) -> str:
    food_type = (food_type or "").lower()
    for category, keywords in KEYWORD_MAP.items():
        if any(kw in food_type for kw in keywords) or category in food_type:
            return category
    return "processed"  # generic fallback bucket


def _parse_range(value_str: str):
    """
    Pulls up to two numbers out of strings like "150-300", "~0 (near-total
    barrier)" or "Tunable via perforation density". Returns (low, high) as
    floats, or None if the field is descriptive text with no real numbers
    (e.g. "Not a gas barrier material") -- those materials are simply left
    out of the barrier-based part of the scoring, not penalized for it.
    """
    numbers = re.findall(r"\d+\.?\d*", value_str or "")
    if not numbers:
        return None
    nums = [float(n) for n in numbers[:2]]
    if len(nums) == 1:
        return (nums[0], nums[0])
    return (min(nums), max(nums))


_COST_TIER_ORDER = ["low", "low-medium", "medium", "medium-high", "high"]


def _cost_tier_index(cost_tier: str) -> int:
    key = (cost_tier or "").strip().lower()
    return _COST_TIER_ORDER.index(key) if key in _COST_TIER_ORDER else 2  # default "medium"


def _budget_tier_index(budget: str) -> int:
    b = (budget or "").lower()
    if "low" in b or "econom" in b:
        return 0
    if "premium" in b or "high" in b:
        return 4
    return 2  # standard


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _score_material(material: dict, moisture, fat, budget_tier_idx: int) -> float:
    """
    Lower score = better fit. Simple, explainable, no black box.
    IMPORTANT: a material with no parseable barrier number (e.g. "Not a gas
    barrier material") must NOT score as 0 / "perfect" when that barrier
    actually matters -- that would make data-less materials falsely win over
    materials that are known to be good. Missing-but-needed data gets a fixed
    uncertainty penalty instead of a free pass.
    """
    score = 0.0
    high_moisture = moisture is not None and moisture >= 50
    high_fat = fat is not None and fat >= 10

    wvtr_range = _parse_range(material["wvtr_g_m2_day"])
    if wvtr_range:
        avg_wvtr = sum(wvtr_range) / 2
        score += avg_wvtr * (2.0 if high_moisture else 0.3)
    elif high_moisture:
        score += 150  # unknown moisture barrier is a real risk for a wet food

    otr_range = _parse_range(material["otr_cc_m2_day"])
    if otr_range:
        avg_otr = sum(otr_range) / 2
        score += avg_otr * (2.0 if high_fat else 0.3)
    elif high_fat:
        score += 150  # unknown oxygen barrier is a real risk for a fatty food

    tier_idx = _cost_tier_index(material["cost_tier"])
    score += max(0, tier_idx - budget_tier_idx) * 400  # penalize going over budget
    score += max(0, budget_tier_idx - tier_idx) * 40    # small nudge against under-spec for the budget given

    return score


def get_relevant_materials(food_type: str = "", respiration: str = "",
                            moisture=None, fat=None, budget: str = "") -> list:
    """
    Step 1 (as before): keyword-filter by food_type/respiration so the pool
    is topically relevant.
    Step 2 (NEW): score that pool by moisture/fat/budget fit and return it
    BEST-FIRST, so "the top of this list" is a reasoned answer, not just
    "the first topical match".
    """
    food_type_l = (food_type or "").lower()
    respiration_l = (respiration or "").lower()

    matched_keywords = []
    for key, kws in KEYWORD_MAP.items():
        # Match if the category name appears in what the user typed OR any of
        # its own keywords do (e.g. food_type "Grain" must match category
        # "dry" via its keyword "grain" -- checking only `key in food_type_l`
        # missed this, since the literal word "dry" never appears in "Grain").
        if key in food_type_l or any(kw in food_type_l for kw in kws):
            matched_keywords.extend(kws)
    if "high" in respiration_l:
        matched_keywords.append("high-respiration")
    if not matched_keywords:
        matched_keywords = ["snack", "dry", "fresh"]

    relevant = [
        m for m in MATERIALS_DB
        if any(kw in " ".join(m["best_for"]).lower() for kw in matched_keywords)
    ]
    if not relevant:
        relevant = MATERIALS_DB[:5]

    moisture_f = _to_float(moisture)
    fat_f = _to_float(fat)
    budget_tier_idx = _budget_tier_index(budget)

    relevant.sort(key=lambda m: _score_material(m, moisture_f, fat_f, budget_tier_idx))
    return relevant


def format_materials_context(materials: list) -> str:
    """Render the material list as compact text to inject into the LLM prompt."""
    lines = []
    for m in materials:
        lines.append(
            f"- {m['name']}: OTR {m['otr_cc_m2_day']} cc/m2/day, "
            f"WVTR {m['wvtr_g_m2_day']} g/m2/day, "
            f"typical thickness {m['typical_thickness_micron']}, "
            f"cost tier: {m['cost_tier']}, "
            f"mechanical strength: {m['mechanical_strength']}, "
            f"sealability: {m['sealability']}, "
            f"recyclable: {'Yes' if m['recyclable'] else 'No'}, "
            f"biodegradable: {'Yes' if m['biodegradable'] else 'No'}, "
            f"best for: {', '.join(m['best_for'])}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# NEW: post-hoc validation of Gemini's JSON block against the database.
# This never rewrites the AI's prose explanation -- it only checks/clamps
# the numeric fields in extra_data (the trailing ```json block) and adds a
# "grounding" report so the frontend/judges can see what was verified.
# ---------------------------------------------------------------------------
def validate_recommendation(extra_data: dict, relevant_materials: list,
                             food_type: str = "") -> dict:
    if not extra_data:
        return extra_data

    grounding = {"material_matched": False, "adjustments": []}

    named_material = (extra_data.get("recommended_material") or "").lower()
    matched = None
    for m in relevant_materials:
        db_name = m["name"].lower()
        # loose match: DB name words appear in what Gemini said, or vice versa
        if db_name in named_material or any(
            word in named_material for word in db_name.split("(")[0].strip().split() if len(word) > 3
        ):
            matched = m
            break

    if matched:
        grounding["material_matched"] = True
        grounding["matched_db_name"] = matched["name"]

        # Clamp cost_per_unit to that material's cost-tier band if it's wildly off
        band = COST_TIER_BANDS_INR.get(matched["cost_tier"].lower())
        if band:
            for cost_key in ("recommended_cost_per_unit",):
                val = _to_float(extra_data.get(cost_key))
                if val is not None and not (band[0] * 0.5 <= val <= band[1] * 1.5):
                    clamped = min(max(val, band[0]), band[1])
                    extra_data[cost_key] = clamped
                    grounding["adjustments"].append(
                        f"{cost_key} adjusted to Rs {clamped} to match {matched['cost_tier']}-tier material range"
                    )
    else:
        grounding["adjustments"].append(
            "Recommended material name was not found in the reference database -- "
            "treat this recommendation's numbers as an AI estimate, not database-verified."
        )

    # NEW: also clamp each entry in packaging_comparison, not just the
    # top-line recommended_cost_per_unit. This is the list now shown in the
    # Cost tab's "Predicted shelf life by material" cards, so it needs the
    # same grounding as the headline number, or it can drift between runs
    # even when the headline number is correctly clamped.
    comparison = extra_data.get("packaging_comparison")
    if isinstance(comparison, list):
        for item in comparison:
            if not isinstance(item, dict):
                continue
            item_name = (item.get("name") or "").lower()
            item_match = None
            for m in relevant_materials:
                db_name = m["name"].lower()
                if db_name in item_name or any(
                    word in item_name for word in db_name.split("(")[0].strip().split() if len(word) > 3
                ):
                    item_match = m
                    break
            if not item_match:
                grounding["adjustments"].append(
                    f"packaging_comparison entry '{item.get('name')}' was not found in the reference "
                    "database -- treat its cost/shelf-life numbers as an AI estimate, not verified."
                )
                continue
            band = COST_TIER_BANDS_INR.get(item_match["cost_tier"].lower())
            if band:
                val = _to_float(item.get("cost_per_unit"))
                if val is not None and not (band[0] * 0.5 <= val <= band[1] * 1.5):
                    clamped = min(max(val, band[0]), band[1])
                    item["cost_per_unit"] = clamped
                    grounding["adjustments"].append(
                        f"packaging_comparison '{item_match['name']}' cost_per_unit adjusted to "
                        f"Rs {clamped} to match {item_match['cost_tier']}-tier range"
                    )

    # Clamp MAP percentages to the food category's realistic bounds
    if extra_data.get("map_relevant"):
        category = _detect_category(food_type)
        bounds = MAP_BOUNDS.get(category)
        if bounds:
            o2_low, o2_high, co2_low, co2_high = bounds
            o2 = _to_float(extra_data.get("map_o2_percent"))
            co2 = _to_float(extra_data.get("map_co2_percent"))
            if o2 is not None and not (o2_low <= o2 <= o2_high):
                clamped_o2 = min(max(o2, o2_low), o2_high)
                extra_data["map_o2_percent"] = clamped_o2
                grounding["adjustments"].append(
                    f"map_o2_percent adjusted to {clamped_o2}% to match published range for '{category}'"
                )
                o2 = clamped_o2
            if co2 is not None and not (co2_low <= co2 <= co2_high):
                clamped_co2 = min(max(co2, co2_low), co2_high)
                extra_data["map_co2_percent"] = clamped_co2
                grounding["adjustments"].append(
                    f"map_co2_percent adjusted to {clamped_co2}% to match published range for '{category}'"
                )
                co2 = clamped_co2
            if o2 is not None and co2 is not None:
                extra_data["map_n2_percent"] = round(100 - o2 - co2, 1)

    extra_data["grounding"] = grounding
    return extra_data