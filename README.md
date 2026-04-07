# 🔬 Research to JSON — AI Paper Extractor

A premium, AI-powered web application that intelligently parses academic research papers (PDF) and extracts structured data into a downloadable JSON format. Powered by **Google Gemini AI** and **PyMuPDF**.

![Research to JSON Interface](https://img.shields.io/badge/AI-Powered-blueviolet?style=for-the-badge&logo=google-gemini)
![Frontend](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)
![Language](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python)

---

## 🚀 Features

- **Intelligent Extraction:** Automatically identifies Title, Authors, Abstract, Keywords, Sections, and References.
- **Real-time Preview:** Interactive side-by-side view with a high-fidelity PDF document previewer.
- **Premium UI/UX:** Stunning dark theme with glassmorphism, animated gradients, and micro-interactions.
- **Smart Quota Handling:** Beautifully handles API rate limits with retry countdowns and monitoring links.
- **Dynamic Model Selection:** Automatically detects and picks the best available Gemini model on your API key.
- **Format Ready:** Export results instantly as a clean, structured JSON file.

---

## 🛠️ Technology Stack

- **Framework:** [Streamlit](https://streamlit.io/) (Python)
- **AI Engine:** [Google Gemini API](https://ai.google.dev/) (Generative AI)
- **PDF Parsing:** [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/)
- **State Management:** Streamlit Session State (to prevent redundant API calls)
- **Styling:** Custom CSS with Glassmorphism & Inter Typography

---

## 🏗️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MIHMahmudEli/Research-to-JSON.git
   cd Research-to-JSON
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup:**
   Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
   *(Optional: You can paste your Gemini API Key directly into the `.env` file or enter it in the app's sidebar.)*

4. **Run the Application:**
   ```bash
   python -m streamlit run app.py
   ```

---

## 📖 How to Use

1. **Get a Gemini API Key:** Visit [Google AI Studio](https://aistudio.google.com/) to generate a free API key.
2. **Launch the App:** Open `http://localhost:8501` in your browser.
3. **Configure:** Enter your API key in the left sidebar.
4. **Upload:** Drag & drop a research paper (PDF) into the upload zone.
5. **Extract:** Wait for the AI to analyze the paper (usually 10-20 seconds).
6. **Download:** Review the extracted JSON in the right pane and click **Download JSON**.

---

## 📊 Extracted JSON Schema

The application follows a strict schema for all extractions:

```json
{
  "title": "String",
  "authors": ["String", "..."],
  "abstract": "String",
  "keywords": ["String", "..."],
  "sections": [
    {
      "heading": "String",
      "body": "String"
    }
  ],
  "references": ["String", "..."]
}
```

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 👤 Author

**MIH Mahmud Eli**
- GitHub: [@MIHMahmudEli](https://github.com/MIHMahmudEli)
- Project Link: [Research-to-JSON](https://github.com/MIHMahmudEli/Research-to-JSON)
