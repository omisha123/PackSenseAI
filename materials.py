"""
Small reference database of common packaging materials.
Used to ground the AI's recommendation with real typical ranges
instead of letting it invent OTR/WVTR/cost numbers from scratch.
"""

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


def get_relevant_materials(food_type: str, respiration: str = "") -> list:
    """
    Very lightweight relevance filter: returns materials whose 'best_for'
    tags loosely match the food type / respiration profile, plus a couple
    of generic fallbacks so the context list is never empty.
    """
    food_type = (food_type or "").lower()
    respiration = (respiration or "").lower()

    keyword_map = {
        "fresh produce": ["fresh", "produce", "vegetable", "fruit"],
        "dry": ["dry", "grain", "pulse"],
        "snack": ["snack", "chips", "namkeen", "fried"],
        "dairy": ["dairy", "milk"],
        "meat": ["meat", "seafood", "retort"],
        "processed": ["ready-to-eat", "processed"],
    }

    matched_keywords = []
    for key, kws in keyword_map.items():
        if key in food_type:
            matched_keywords.extend(kws)

    if "high" in respiration:
        matched_keywords.append("high-respiration")

    if not matched_keywords:
        # Generic fallback set covering common cases
        matched_keywords = ["snack", "dry", "fresh"]

    relevant = []
    for material in MATERIALS_DB:
        tags = " ".join(material["best_for"]).lower()
        if any(kw in tags for kw in matched_keywords):
            relevant.append(material)

    # Always ensure at least a small generic fallback set
    if not relevant:
        relevant = MATERIALS_DB[:5]

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