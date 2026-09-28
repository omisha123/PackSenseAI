from flask import Flask, render_template, request, jsonify, session, send_file
import database as db
import materials
import spec_sheet
from google import genai
from google.genai import types
import os
import re
import json
import time
import uuid
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = "super_secret_key_for_mofpi_packaging_app"

db.init_db()

MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

# Section headings are supplied to the model pre-translated instead of asking
# it to translate them itself — headings are short, fixed strings, and the
# model was inconsistent about translating them while leaving the rest of
# the answer in the selected language. Body text is still written by the model.
HEADINGS = {
    "English": {
        "recommended": "## 📦 Recommended packaging",
        "structure": "## 📐 Packaging structure",
        "why": "## 💡 Why this works",
        "look_for": "## 🛒 What to look for",
        "lower_cost": "## 💰 Lower-cost option",
        "sustainable": "## 🌱 More sustainable option",
        "fssai": "## ✅ FSSAI compliance notes",
        "watch": "## ⚠️ One thing to watch",
        "technical": "## 🔬 Technical details",
    },
    "Hindi": {
        "recommended": "## 📦 अनुशंसित पैकेजिंग",
        "structure": "## 📐 पैकेजिंग संरचना",
        "why": "## 💡 यह कैसे काम करता है",
        "look_for": "## 🛒 किन बातों का ध्यान रखें",
        "lower_cost": "## 💰 कम लागत वाला विकल्प",
        "sustainable": "## 🌱 अधिक टिकाऊ विकल्प",
        "fssai": "## ✅ FSSAI अनुपालन नोट्स",
        "watch": "## ⚠️ एक बात का ध्यान रखें",
        "technical": "## 🔬 तकनीकी विवरण",
    },
    "Marathi": {
        "recommended": "## 📦 शिफारस केलेले पॅकेजिंग",
        "structure": "## 📐 पॅकेजिंग रचना",
        "why": "## 💡 हे असे का काम करते",
        "look_for": "## 🛒 कशाकडे लक्ष द्यावे",
        "lower_cost": "## 💰 कमी किमतीचा पर्याय",
        "sustainable": "## 🌱 अधिक शाश्वत पर्याय",
        "fssai": "## ✅ FSSAI अनुपालन टिपा",
        "watch": "## ⚠️ एका गोष्टीकडे लक्ष द्या",
        "technical": "## 🔬 तांत्रिक तपशील",
    },
}

# Optional fields that meaningfully sharpen the recommendation when filled.
# Used only to compute a plain confidence indicator — no AI call involved.
OPTIONAL_FIELD_KEYS = ["moisture", "fat", "ph", "extra_notes"]
EMPTY_MARKERS = {"", "not provided", "none", "not sure"}

CONFIDENCE_COPY = {
    # NOTE: the frontend already prepends the level label itself (e.g. shows
    # "Medium confidence — " before this text) -- these strings previously
    # repeated that label, producing "Medium confidence — Medium confidence —
    # ...". Prefix removed here; only the actionable note remains.
    "English": {
        "high": "Enough details were provided for a sharper estimate.",
        "medium": "This is a rough estimate; fill in moisture, fat or pH for a sharper answer.",
        "low": "Add moisture, fat, pH or notes above for a sharper answer.",
    },
    "Hindi": {
        "high": "बेहतर अनुमान के लिए पर्याप्त जानकारी दी गई है।",
        "medium": "यह एक मोटा अनुमान है; बेहतर उत्तर के लिए नमी, वसा या pH भरें।",
        "low": "बेहतर उत्तर के लिए ऊपर नमी, वसा, pH या टिप्पणी जोड़ें।",
    },
    "Marathi": {
        "high": "अधिक अचूक अंदाजासाठी पुरेशी माहिती दिली आहे.",
        "medium": "हा एक ढोबळ अंदाज आहे; अधिक चांगल्या उत्तरासाठी आर्द्रता, चरबी किंवा pH भरा.",
        "low": "अधिक चांगल्या उत्तरासाठी वर आर्द्रता, चरबी, pH किंवा टीप जोडा.",
    },
}


def compute_confidence(data):
    """
    Counts how many optional-but-useful fields the user actually filled in
    and returns a plain confidence label + note. Pure arithmetic on the
    submitted form — not an AI judgment, so it can't drift or hallucinate.
    """
    filled = 0
    for key in OPTIONAL_FIELD_KEYS:
        value = str(data.get(key, "")).strip().lower()
        if value not in EMPTY_MARKERS:
            filled += 1

    if filled >= 3:
        level = "high"
    elif filled >= 1:
        level = "medium"
    else:
        level = "low"

    language = data.get("language", "English")
    copy = CONFIDENCE_COPY.get(language, CONFIDENCE_COPY["English"])
    return {
        "confidence_level": level,
        "confidence_note": copy[level],
        "fields_filled": filled,
        "fields_total": len(OPTIONAL_FIELD_KEYS),
    }


def compute_break_even(extra_data, value_per_unit=None):
    """
    Pure arithmetic (no AI call) turning the cheap-vs-recommended cost and
    loss percentages into a simple "net saving at volume X" table, so a
    small business can see where the pricier packaging starts paying for
    itself. If the user didn't give a per-unit product value, we fall back
    to a rough multiple of packaging cost, same as the existing waste-estimate
    fallback, so the table still renders something sensible.
    """
    if not extra_data:
        return None
    try:
        cheap_cost = float(extra_data.get("cheap_cost_per_unit"))
        rec_cost = float(extra_data.get("recommended_cost_per_unit"))
        cheap_loss = float(extra_data.get("cheap_loss_percent"))
        rec_loss = float(extra_data.get("recommended_loss_percent"))
    except (TypeError, ValueError):
        return None

    try:
        assumed_value = float(value_per_unit) if value_per_unit not in (None, "", "Not provided") else None
    except (TypeError, ValueError):
        assumed_value = None
    if not assumed_value or assumed_value <= 0:
        assumed_value = max(cheap_cost, rec_cost) * 4  # same rough fallback used elsewhere

    rows = []
    for volume in (500, 1000, 5000):
        packaging_cost_diff = (rec_cost - cheap_cost) * volume
        cheap_loss_cost = (cheap_loss / 100) * assumed_value * volume
        rec_loss_cost = (rec_loss / 100) * assumed_value * volume
        net_saving = (cheap_loss_cost - rec_loss_cost) - packaging_cost_diff
        rows.append({"units": volume, "net_saving": round(net_saving, 0)})

    return {"assumed_value_per_unit": round(assumed_value, 2), "rows": rows}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    if db.add_user(data['username'], data['password']):
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Username already exists!"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if db.login_user(data['username'], data['password']):
        session['username'] = data['username']
        return jsonify({"status": "success", "username": data['username']})
    return jsonify({"status": "error", "message": "Invalid credentials!"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({"status": "success"})


def extract_roi_block(text):
    """
    Pulls the trailing ```json data block out of the AI response, if present.
    This block now carries ROI, MAP gas composition and sustainability data
    together under one JSON payload. Returns (cleaned_text, data_dict_or_None).
    """
    match = None
    for m in re.finditer(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL):
        match = m  # keep the last one (block is instructed to be at the end)
    if not match:
        return text, None
    try:
        parsed = json.loads(match.group(1))
    except Exception:
        return text, None
    cleaned_text = (text[:match.start()] + text[match.end():]).rstrip()
    return cleaned_text, parsed


def attach_waste_estimate(extra_data):
    """
    Turn the cheap-vs-recommended loss percentages the model already returns
    into a tangible, demo-friendly absolute number: how many fewer units
    spoil per 1000 units packed if the recommended packaging is used instead
    of the cheap option. Pure arithmetic on numbers the model already gave us,
    so it can't drift from the ROI card it sits next to.
    """
    if not extra_data:
        return extra_data
    try:
        cheap_loss = float(extra_data.get("cheap_loss_percent"))
        rec_loss = float(extra_data.get("recommended_loss_percent"))
        saved_percent_points = max(cheap_loss - rec_loss, 0)
        extra_data["waste_units_saved_per_1000"] = round(saved_percent_points * 10, 1)
    except (TypeError, ValueError):
        pass
    return extra_data


def build_trace_payload(username, commodity, shelf_life_days):
    """Generate a batch number, pack/expiry dates, and a scannable trace string."""
    pack_date = datetime.now()
    try:
        shelf_days = int(shelf_life_days)
    except (TypeError, ValueError):
        shelf_days = 7
    expiry_date = pack_date + timedelta(days=shelf_days)

    batch_no = f"PS-{pack_date.strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    trace_string = (
        f"PackSense|batch={batch_no}|product={commodity}|"
        f"packed={pack_date.strftime('%Y-%m-%d')}|"
        f"best_before={expiry_date.strftime('%Y-%m-%d')}|by={username}"
    )

    return {
        "batch_no": batch_no,
        "pack_date": pack_date.strftime("%d %b %Y"),
        "expiry_date": expiry_date.strftime("%d %b %Y"),
        "trace_string": trace_string,
    }


@app.route('/api/generate', methods=['POST'])
def generate():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Server configuration error: Gemini API Key is missing!"}), 500

    # --- CHANGE 1 OF 2: pass moisture/fat/budget so materials.py can actually
    # score candidates instead of only keyword-matching on food_type. ---
    relevant_materials = materials.get_relevant_materials(
        data.get('food_type', ''),
        data.get('respiration', ''),
        moisture=data.get('moisture'),
        fat=data.get('fat'),
        budget=data.get('budget', ''),
    )
    materials_context = materials.format_materials_context(relevant_materials)

    language = data.get('language', 'English')
    h = HEADINGS.get(language, HEADINGS["English"])

    prompt = f"""
You are PackSense AI, a friendly food-packaging advisor.

The user may be a farmer, small food business owner, student, startup, or manufacturer with NO technical
background. Write for someone who has never heard the words "barrier property", "permeability" or
"transmission rate" before. Use short sentences and everyday words and comparisons (e.g. "keeps moisture
out, like a raincoat" instead of "low WVTR"). Do not sound like a research paper.

Food: {data['commodity']}
Food type: {data.get('food_type', 'Not provided')}
Moisture: {data['moisture']}%
Fat: {data['fat']}%
pH: {data['ph']}
Respiration: {data['respiration']}
Storage: {data['storage_type']}
Temperature: {data['temp']}°C
Humidity: {data['humidity']}% RH
Target shelf life: {data['shelf_life']} days
Transport: {data['transport']}
Budget: {data['budget']}
Extra user notes: {data.get('extra_notes', 'None')}

Reference packaging materials you may draw from (real-world typical ranges,
use these to ground your numbers rather than inventing your own):
{materials_context}

Write the entire answer in {language}. Use EXACTLY the section headings given below, character for
character — they are already translated into {language}, so copy them as-is rather than translating
or rewording them yourself. Only the text underneath each heading is yours to write.

{h['recommended']}
State the main packaging material first, in plain words (e.g. "a printed plastic pouch" rather than just
a chemical name). Prefer materials from the reference list above when they genuinely fit; you may propose
a different material if none of them fit well, but say so.

{h['structure']}
Describe the actual physical structure in one or two plain sentences — not just the material name. For
example: a single film pouch, a laminate of two films, a rigid tray with a lidding film, a pouch inside a
carton, or a film with small holes for breathing fruit. Say this the way you'd describe it to someone who
has never packed food before (e.g. "a plastic pouch with a paper label wrapped around it, with tiny holes
so the fruit can breathe") rather than using engineering terms.

{h['why']}
Explain it in simple language for a non-expert. No acronyms here (no OTR, WVTR, MAP) — describe what the
packaging actually does for the food (keeps air out, stops it going soggy, blocks light, etc).

{h['look_for']}
Give practical buying guidance in plain words: how thick it should feel, whether it should seal shut with
heat or a clip/tie, and how sturdy it needs to be for stacking or transport. Avoid raw numbers or acronyms
here — save exact OTR/WVTR/thickness figures for the Technical details section below.

{h['lower_cost']}
Suggest a sensible lower-cost alternative when possible, in the same plain style.

{h['sustainable']}
When suggesting a sustainable/eco-friendly alternative, prefer realistic Indian agricultural-waste and
indigenous materials where they genuinely fit the food type and use case, for example: areca nut sheath
plates/trays, banana leaf laminate, sal leaf packaging, bagasse (sugarcane waste) trays and clamshells,
corn-starch or PLA-based films, jute or cotton pouches, and paper/kraft-based laminates. Only suggest these
when they are actually appropriate for the food's moisture, fat and shelf-life needs — do not force an
unsuitable material just because it is eco-friendly. Briefly mention why it fits India's agricultural
context (local availability, circular economy angle) when relevant.

{h['fssai']}
Give general, practical compliance reminders relevant to the recommended packaging (for example: use only
food-grade/FSSAI-approved plastics and inks, check migration limits for fatty foods, ensure proper labeling
with manufacturing/expiry details, avoid recycled plastic in direct food contact unless certified). Do NOT
invent or cite specific FSSAI regulation numbers, section numbers, or dates — keep this as general practical
guidance and clearly state that the business should verify exact requirements with FSSAI/a compliance
professional before production.

{h['watch']}
Give one important practical warning, in plain language.

{h['technical']}
This is the ONLY section where acronyms, exact numbers and engineering terms belong. Put OTR, WVTR,
thickness, mechanical strength and sealability temperature here, each with a one-line plain-language
translation in brackets so a non-expert can still follow along (e.g. "WVTR: 10-20 g/m2/day (a measure of
how much moisture can pass through — lower is drier)").
Do NOT state MAP gas percentages (O2/CO2/N2 numbers) in this section's text. The exact MAP percentages are
shown separately in a dedicated MAP card elsewhere on the page, generated from the map_o2_percent/
map_co2_percent/map_n2_percent values you give at the end -- restating different numbers here would
contradict that card. If MAP is relevant, just write one sentence noting that a modified-atmosphere gas
flush is recommended and to see the MAP card above for the exact mix; do not give your own percentages here.

End with a short "Why this choice?" sentence that a non-expert can understand.

IMPORTANT FORMATTING RULES:
- NEVER use LaTeX or mathematical formatting.
- NEVER use $, backslashes, \\mathbf{{}}, \\mathrm{{}}, \\text{{}}, ^{{}}, _{{}}, or other LaTeX commands.
- Write O2, CO2 and N2 as normal plain text.
- Write percentages as normal text, for example 3% - 5%.
- Use normal Markdown headings (exactly as given above) and bullet points if useful.
- Outside the Technical details section, do not use the acronyms OTR, WVTR or MAP at all — describe the
  effect in plain words instead.
- Keep the answer concise, visual, practical and easy for a non-expert to understand.
- If a value is uncertain because the user did not provide enough information, say that clearly instead of inventing precision.

After ALL of the above sections, append ONE final fenced json code block (```json ... ```) with your best
realistic estimates, using exactly these keys:
{{
  "recommended_material": <short name of the main recommended material only, in {language}, e.g. "Micro-perforated LDPE film">,
  "recommended_structure": <one short phrase, in {language}, naming the physical structure, e.g. "Pouch with a lidding film">,
  "mechanical_strength": <one short phrase, in {language}, plain language, e.g. "Sturdy enough to stack 5 high">,
  "sealability": <one short phrase, in {language}, plain language, e.g. "Seals shut with heat, no special machine needed">,
  "cheap_cost_per_unit": <number, cost in INR per packaging unit for the cheapest common option>,
  "cheap_shelf_life_days": <number, realistic shelf life in days with that cheap option>,
  "cheap_loss_percent": <number, estimated spoilage/loss percent in transit+storage with that cheap option>,
  "recommended_cost_per_unit": <number, cost in INR per packaging unit for your main recommended option>,
  "recommended_shelf_life_days": <number, realistic shelf life in days with the recommended option>,
  "recommended_loss_percent": <number, estimated spoilage/loss percent in transit+storage with the recommended option>,
  "map_relevant": <true or false, whether Modified Atmosphere Packaging is relevant for this product>,
  "map_o2_percent": <number or null, recommended O2 percent in the MAP gas mix, null if map_relevant is false>,
  "map_co2_percent": <number or null, recommended CO2 percent in the MAP gas mix, null if map_relevant is false>,
  "map_n2_percent": <number or null, recommended N2 percent in the MAP gas mix, null if map_relevant is false>,
  "recyclability": <one of "High", "Medium", "Low", for the main recommended packaging>,
  "biodegradable": <true or false, whether the main recommended packaging is biodegradable>,
  "sustainability_note": <one short sentence, in {language}, explaining the sustainability tradeoff>,
  "packaging_comparison": [
    {{
      "name": <material name, prefer one from the reference list above>,
      "predicted_shelf_life_days": <number, realistic shelf life in days for THIS food under the given storage/temp/humidity conditions with THIS material>,
      "cost_per_unit": <number, cost in INR per packaging unit for this material>,
      "suitability": <one of "Best fit", "Good option", "Budget option", "Not ideal">,
      "note": <one short sentence, in {language}, on why this material gets this predicted shelf life>
    }}
  ]
}}
For "packaging_comparison", give exactly 2 or 3 candidate materials (including your main recommendation),
each with its own independently reasoned predicted shelf life for this specific food and these specific
conditions - this is a separate shelf-life estimate per material, not just a repeat of the cheap/recommended
numbers above.
Use plain numbers only (no currency symbols, no ranges, no text) for numeric fields. Base the estimates
on the food type and conditions given; state clearly in the main text above if these are rough estimates.
"""

    last_error = None
    for model in MODELS:
        for attempt in range(3):
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model=model, contents=prompt)
                raw_text = response.text
                cleaned_text, extra_data = extract_roi_block(raw_text)
                extra_data = attach_waste_estimate(extra_data)
                if extra_data is not None:
                    # --- CHANGE 2 OF 2: validate/clamp Gemini's numbers against
                    # the materials database before anything else touches them. ---
                    extra_data = materials.validate_recommendation(
                        extra_data, relevant_materials,
                        food_type=data.get('food_type', ''),
                        respiration=data.get('respiration', ''),
                        fat=data.get('fat'),
                    )
                    extra_data["confidence"] = compute_confidence(data)

                    # Q10 shelf-life model data for the frontend curve.
                    # The AI's recommended shelf life is treated as the baseline
                    # at the temperature entered by the user. Q10=2 means the
                    # deterioration rate doubles for every 10°C increase.
                    try:
                        reference_temperature_c = float(data.get("temp"))
                    except (TypeError, ValueError):
                        reference_temperature_c = 25.0

                    extra_data["reference_temperature_c"] = reference_temperature_c
                    extra_data["q10"] = 2.0

                    break_even = compute_break_even(extra_data, data.get("value_per_unit"))
                    if break_even:
                        extra_data["break_even"] = break_even
                trace_data = build_trace_payload(
                    session['username'], data['commodity'], data['shelf_life']
                )
                db.save_recommendation(
                    session['username'],
                    data['commodity'],
                    data['language'],
                    cleaned_text,
                    roi_data=extra_data,
                    trace_data=trace_data
                )
                return jsonify({
                    "recommendation": cleaned_text,
                    "roi_data": extra_data,
                    "trace": trace_data,
                    "model": model
                })
            except Exception as e:
                last_error = str(e)
                error_text = last_error.lower()
                retryable = any(x in error_text for x in [
                    "503", "unavailable", "overloaded", "429", "resource_exhausted", "too many requests"
                ])
                if retryable and attempt < 2:
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                break

    return jsonify({
        "error": "The AI service is temporarily busy. Please try again in a few seconds.",
        "details": last_error
    }), 503

@app.route('/api/history', methods=['GET'])
def history():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    hist = db.get_history(session['username'])
    result = [
        {
            "commodity": h[0],
            "language": h[1],
            "recommendation": h[2],
            "timestamp": h[3],
            "roi_data": h[4],
            "trace": h[5],
        }
        for h in hist
    ]
    return jsonify(result)

@app.route('/api/upcoming-expiry', methods=['GET'])
def upcoming_expiry():
    """
    Pure arithmetic over history the app already stores: for every past
    recommendation that carries a trace (batch/expiry) payload, work out how
    many days are left until "best before" and surface the ones expiring
    soon. No new AI call - this is just re-reading dates already generated
    by build_trace_payload().
    """
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    hist = db.get_history(session['username'])
    today = datetime.now().date()
    upcoming = []

    for commodity, language, recommendation, timestamp, roi_data, trace_data in hist:
        if not trace_data or not trace_data.get("expiry_date"):
            continue
        try:
            expiry = datetime.strptime(trace_data["expiry_date"], "%d %b %Y").date()
        except ValueError:
            continue
        days_left = (expiry - today).days
        if 0 <= days_left <= 14:
            upcoming.append({
                "commodity": commodity,
                "batch_no": trace_data.get("batch_no"),
                "expiry_date": trace_data.get("expiry_date"),
                "days_left": days_left,
            })

    upcoming.sort(key=lambda item: item["days_left"])
    return jsonify(upcoming)


VALID_FOOD_TYPES = [
    "Fresh produce", "Dry / low-moisture food", "Snack / fried food",
    "Dairy", "Meat / seafood", "Processed / ready-to-eat", "Other",
]
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB — generous for a phone photo, small enough to fail fast


@app.route('/api/identify-commodity', methods=['POST'])
def identify_commodity():
    """
    Photo-based commodity input. Takes a food photo, asks Gemini's vision
    capability to identify the commodity and estimate the packaging-relevant
    properties (food_type category, rough moisture/fat %, respiration),
    and returns them so the frontend can pre-fill Step 1 of the form.

    This never writes a recommendation or touches the materials database --
    it only proposes values for the user to review/edit before they hit
    "Generate", same as if they'd typed them in themselves.
    """
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image_file = request.files['image']
    mime_type = image_file.mimetype or "image/jpeg"
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        return jsonify({"error": "Please upload a JPEG, PNG or WEBP image."}), 400

    image_bytes = image_file.read()
    if not image_bytes:
        return jsonify({"error": "That image came through empty. Please try again."}), 400
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return jsonify({"error": "That image is too large. Please use a photo under 8MB."}), 400

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Server configuration error: Gemini API Key is missing!"}), 500

    prompt = f"""
You are looking at a photo someone took of a food item they want to package for storage or sale.

Identify the food commodity shown and estimate the packaging-relevant properties needed to
recommend suitable packaging for it. Respond with ONLY a single fenced json code block and
nothing else -- no preamble, no explanation outside the block -- using exactly these keys:

{{
  "identified": <true or false -- false if the image does not clearly show a food/food-adjacent item>,
  "commodity": <short common name of the food item in English, e.g. "Mango" or "Potato chips". Empty string if not identified>,
  "food_type": <exactly one of {VALID_FOOD_TYPES}>,
  "moisture_percent": <number, your best typical estimate of moisture content percent for this food, or null if not meaningfully applicable>,
  "fat_percent": <number, your best typical estimate of oil/fat content percent for this food, or null if not meaningfully applicable>,
  "respiration": <one of "High", "Medium", "Low", "Not sure" -- whether this food keeps respiring/ripening after harvest>,
  "note": <one short plain-English sentence flagging anything the user should double check or adjust, or empty string if nothing notable>
}}

Use your best realistic estimate for a typical specimen of this food -- these are starting values
the user will review and can edit themselves, not final numbers. If several different foods are
visible, identify the single most prominent one. If the photo is blurry, dark, or doesn't show a
recognizable food item, set "identified" to false, "commodity" to "", other fields to null/"Not sure",
and put a short explanation in "note".
"""

    raw_text = ""
    last_error = None
    for model in MODELS:
        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=20000),  # 20 seconds
            )
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
            )
            raw_text = response.text or ""
            if raw_text:
                break
        except Exception as e:
            last_error = e
            print(f"identify-commodity failed on {model}: {e}")

    if not raw_text:
        return jsonify({
            "error": "Could not analyze that photo right now. Please try again in a moment.",
            "details": str(last_error)
        }), 503

    match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if not match:
        match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
    if not match:
        return jsonify({"error": "Could not make sense of the photo. Please try a clearer shot or enter details manually."}), 502

    try:
        parsed = json.loads(match.group(1))
    except Exception:
        return jsonify({"error": "Could not make sense of the photo. Please try a clearer shot or enter details manually."}), 502

    if not parsed.get("identified"):
        return jsonify({
            "identified": False,
            "message": (parsed.get("note") or "").strip()
                or "Couldn't clearly identify a food item in that photo — try a closer, well-lit shot, or enter the details manually."
        })

    food_type = parsed.get("food_type")
    if food_type not in VALID_FOOD_TYPES:
        food_type = "Other"

    respiration = parsed.get("respiration")
    if respiration not in ("High", "Medium", "Low", "Not sure"):
        respiration = "Not sure"

    def _clean_percent(value):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        return round(max(0.0, min(100.0, v)), 1)

    return jsonify({
        "identified": True,
        "commodity": (parsed.get("commodity") or "").strip(),
        "food_type": food_type,
        "moisture_percent": _clean_percent(parsed.get("moisture_percent")),
        "fat_percent": _clean_percent(parsed.get("fat_percent")),
        "respiration": respiration,
        "note": (parsed.get("note") or "").strip(),
    })


@app.route('/api/parse-voice', methods=['POST'])
def parse_voice():
    """Convert one natural-language voice transcript into the existing form fields."""
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json or {}
    transcript = str(data.get('transcript', '')).strip()
    language = data.get('language', 'English')

    if not transcript:
        return jsonify({"error": "No voice transcript received."}), 400

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Server configuration error: Gemini API Key is missing!"}), 500

    prompt = f"""
You are a form-filling assistant for PackSense, a food-packaging recommendation website.

The user spoke one natural-language request. Extract ONLY information that is clearly stated or
strongly implied. Do not invent values. The user may speak English, Hindi, Marathi, Punjabi, or a
mix of these languages. Understand the meaning and return field values in the exact formats below.

User's selected website language: {language}
Voice transcript:
{transcript}

Return ONLY one fenced JSON block with exactly these keys:
{{
  "language": <one of "English", "Hindi", "Marathi", "Punjabi" or null if not clear>,
  "commodity": <food/product name as a short string or null>,
  "food_type": <one of "Fresh produce", "Dry / low-moisture food", "Snack / fried food", "Dairy", "Meat / seafood", "Processed / ready-to-eat", "Other", or null>,
  "moisture": <number as a string or null>,
  "fat": <number as a string or null>,
  "ph": <number as a string or null>,
  "storage_type": <one of "Room temperature", "Refrigerated", "Frozen", "Warehouse", "Cold chain", or null>,
  "temp": <number as a string or null>,
  "humidity": <number as a string or null>,
  "shelf_life": <one of "3", "7", "14", "30", "60", "90" or null>,
  "respiration": <one of "Not sure", "Low", "Medium", "High" or null>,
  "transport": <one of "Road / Truck", "Local delivery", "Sea Freight", "Air Freight" or null>,
  "budget": <one of "Low / Economy", "Standard", "Premium / Export" or null>,
  "extra_notes": <short string containing useful requirements that do not belong in another field, or null>
}}

Rules:
- If the user says "cheap", "low cost", "budget", or similar, use "Low / Economy".
- If the user says "normal" or "medium budget", use "Standard".
- If the user says "premium", "export", or similar, use "Premium / Export".
- Convert common spoken temperature, moisture, fat and pH values to simple numbers without units.
- If the user gives a shelf life such as "one week", use "7"; "two weeks" -> "14"; "one month" -> "30"; "two months" -> "60"; "three months" -> "90".
- If the user mentions refrigerated/chilled/cold storage, use "Refrigerated". Frozen -> "Frozen". Cold chain -> "Cold chain".
- If the user mentions truck/road, use "Road / Truck". Local delivery -> "Local delivery". Ship/sea -> "Sea Freight". Flight/air -> "Air Freight".
- If a value is not mentioned, return null. Do not fill missing fields with guesses.
- Keep the food name concise. If the user says "mangoes", return "Mango".
- Put preferences such as "eco-friendly", "recyclable", "strong", "cheap", or other packaging wishes in extra_notes unless they directly map to budget.
"""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=MODELS[0], contents=prompt)
        raw_text = response.text or ""
    except Exception as e:
        return jsonify({
            "error": "Could not understand the voice request right now. Please try again.",
            "details": str(e)
        }), 503

    match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if not match:
        match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
    if not match:
        return jsonify({"error": "The voice response could not be parsed. Please try again."}), 502

    try:
        parsed = json.loads(match.group(1))
    except Exception:
        return jsonify({"error": "The voice response could not be parsed. Please try again."}), 502

    allowed = {
        "language": {"English", "Hindi", "Marathi", "Punjabi"},
        "food_type": set(VALID_FOOD_TYPES),
        "storage_type": {"Room temperature", "Refrigerated", "Frozen", "Warehouse", "Cold chain"},
        "shelf_life": {"3", "7", "14", "30", "60", "90"},
        "respiration": {"Not sure", "Low", "Medium", "High"},
        "transport": {"Road / Truck", "Local delivery", "Sea Freight", "Air Freight"},
        "budget": {"Low / Economy", "Standard", "Premium / Export"},
    }

    result = {}
    for key in ["language", "commodity", "food_type", "moisture", "fat", "ph", "storage_type", "temp", "humidity", "shelf_life", "respiration", "transport", "budget", "extra_notes"]:
        value = parsed.get(key)
        if value is None or str(value).strip() == "":
            result[key] = None
            continue
        if key in allowed and value not in allowed[key]:
            result[key] = None
            continue
        if key in {"moisture", "fat", "ph", "temp", "humidity"}:
            try:
                result[key] = str(float(str(value).replace('%', '').replace('°C', '').replace('°', '').strip()))
            except (TypeError, ValueError):
                result[key] = None
        else:
            result[key] = str(value).strip()

    return jsonify(result)

@app.route('/api/spec-sheet', methods=['POST'])
def spec_sheet_route():
    """
    Builds a formal, supplier-facing PDF spec sheet from a recommendation the
    user already generated. No new Gemini call here -- the frontend sends
    back the same form_data, roi_data (extra_data) and trace it already has
    from the /api/generate response, and this just formats it as a document.

    'photo' (optional): a compressed data URL ("data:image/jpeg;base64,...")
    of the food photo the user uploaded during identification, if any. It is
    never stored server-side -- decoded in-memory just long enough to embed
    a small reference thumbnail in the PDF, purely for the supplier's visual
    confirmation of the product. Not present for recommendations the user
    typed in by hand.
    """
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    payload = request.json or {}
    form_data = payload.get("form_data") or {}
    extra_data = payload.get("roi_data") or {}
    trace_data = payload.get("trace") or {}

    photo_bytes = None
    photo_data_url = payload.get("photo")
    if photo_data_url and isinstance(photo_data_url, str) and photo_data_url.startswith("data:image/"):
        try:
            header, b64_data = photo_data_url.split(",", 1)
            photo_bytes = base64.b64decode(b64_data)
            if len(photo_bytes) > MAX_IMAGE_BYTES:
                photo_bytes = None  # ignore oversized/garbled payloads rather than failing the whole PDF
        except Exception:
            photo_bytes = None  # malformed data URL -- spec sheet still generates, just without the photo

    try:
        pdf_buffer = spec_sheet.build_spec_sheet_pdf(form_data, extra_data, trace_data, photo_bytes=photo_bytes)
    except Exception as e:
        return jsonify({"error": "Could not generate spec sheet.", "details": str(e)}), 500

    filename = f"packaging-spec-{trace_data.get('batch_no', 'draft')}.pdf"
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)