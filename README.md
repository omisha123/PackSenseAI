 AI-Based Intelligent Food Packaging Material Recommendation System
This is an AI-powered Streamlit web application designed to recommend suitable packaging materials and specifications for various food commodities. It uses the Google Gemini API to analyze food properties and environmental conditions, acting as a smart decision-support tool for the food processing and packaging industry.
## Features
- Input parameters like moisture content, oil/fat content, respiration rate, and storage conditions.
- Recommends suitable packaging materials (LDPE, HDPE, PET, biodegradable films, etc.).
- Predicts barrier properties (OTR, WVTR, Film Thickness).
- Recommends Modified Atmosphere Packaging (MAP) gas compositions.
- Suggests sustainable and recyclable alternatives.
## Setup Instructions
### 1. Prerequisites
- Python 3.9 or higher
- A Google Gemini API Key. You can get one from [Google AI Studio](https://aistudio.google.com/).
### 2. Create a Virtual Environment (Recommended)
Open your terminal (Command Prompt or PowerShell) and navigate to this folder:
```powershell
cd "C:\Users\Omisha Iyer\.gemini\antigravity\scratch\food_packaging_system"
python -m venv venv
```
Activate the virtual environment:
- On Windows:
  ```powershell
  .\venv\Scripts\activate
  ```
- On Mac/Linux:
  ```bash
  source venv/bin/activate
  ```
### 3. Install Dependencies
Install the required packages using pip:
```powershell
pip install -r requirements.txt
```