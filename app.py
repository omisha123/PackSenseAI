from flask import Flask, render_template, request, jsonify, session
import database as db
from google import genai
import os
import time

app = Flask(__name__)
app.secret_key = "super_secret_key_for_mofpi_packaging_app"

db.init_db()

MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

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

@app.route('/api/generate', methods=['POST'])
def generate():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Server configuration error: Gemini API Key is missing!"}), 500

    prompt = f"""
You are PackSense AI, a friendly food-packaging advisor.

The user may be a farmer, small food business owner, student, startup, or manufacturer.
Explain things in simple, practical language. Do not sound like a research paper.

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

Write the entire answer in {data['language']}.

Structure the answer for a visual web dashboard:

## 📦 Recommended packaging
State the main packaging material first.

## 💡 Why this works
Explain it in simple language for a non-expert.

## 🛒 What to look for
Give practical buying/specification guidance such as material, thickness and sealability.

## 💰 Lower-cost option
Suggest a sensible lower-cost alternative when possible.

## 🌱 More sustainable option
Suggest a realistic sustainable alternative when appropriate.

## ⚠️ One thing to watch
Give one important practical warning.

## 🔬 Technical details
Put OTR, WVTR, thickness, MAP gas composition and other technical numbers here when relevant.

End with a short "Why this choice?" sentence that a non-expert can understand.

IMPORTANT FORMATTING RULES:
- NEVER use LaTeX or mathematical formatting.
- NEVER use $, backslashes, \mathbf{{}}, \mathrm{{}}, \text{{}}, ^{{}}, _{{}}, or other LaTeX commands.
- Write O2, CO2 and N2 as normal plain text.
- Write percentages as normal text, for example 3% - 5%.
- Use normal Markdown headings and bullet points if useful.
- Keep the answer concise, visual, practical and easy for a non-expert to understand.
- If a value is uncertain because the user did not provide enough information, say that clearly instead of inventing precision.
"""

    last_error = None
    for model in MODELS:
        for attempt in range(3):
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(model=model, contents=prompt)
                recommendation = response.text
                db.save_recommendation(
                    session['username'],
                    data['commodity'],
                    data['language'],
                    recommendation
                )
                return jsonify({"recommendation": recommendation, "model": model})
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
    result = [{"commodity": h[0], "language": h[1], "recommendation": h[2], "timestamp": h[3]} for h in hist]
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
