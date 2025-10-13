# 🇮🇳 Bharat: Regional Language Fact News Detection System

![Streamlit](https://img.shields.io/badge/Built%20With-Streamlit-FF4B4B?logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-success)

---

## 📘 Overview

**Bharat** is a multilingual, agentic AI system built with **Streamlit**, designed to detect and verify misinformation across **22 Indian languages**.
It continuously monitors platforms like **Reddit, YouTube, and regional news portals**, detects claims, verifies them against trusted sources, and presents transparent, evidence-backed results.

The platform integrates **Local Large Language Models (LLMs)** (e.g., *Phi-4 via llama-cpp-python*) and **Gemini-based query generation**, offering both accuracy and explainability.

---

## ⚙️ How It Works (Pipeline Overview)

The analysis pipeline executes in **five main stages**:

### 1️⃣ User Query Input

* The user enters a topic or claim in the UI.
* This query is passed directly to the `reddit.py` module, which initiates a targeted search on Reddit.

### 2️⃣ Data Scraping (PRAW)

* The Reddit API (via PRAW) is used to scrape relevant **posts and comments**.
* The collected data is stored in a JSON file named **`reddit_search_output.json`**.

### 3️⃣ Data Preparation (LangChain)

* The scraped text is split into smaller, meaningful **chunks** using `RecursiveCharacterTextSplitter`.
* These chunks are grouped into **batches** for efficient parallel analysis.

### 4️⃣ Claim Verification (Local LLM - Phi-4)

* Each batch is analyzed by the **local LLM (Phi-4)** via `llama-cpp-python`.
* The model performs reasoning and zero-shot classification, identifying and labeling each claim as:

  * ✅ True
  * ❌ False
  * ⚠️ Misleading
  * ❓ Unverifiable

### 5️⃣ Multilingual Explanation & Visualization (Streamlit)

* The results are displayed in the **Streamlit app (`final5.py`)** with:

  * Interactive **visual charts** using Altair
  * **Color-coded claim cards**
  * **Confidence scores, sources, and explanations** in readable format

---

## 🚀 Setup & Installation

### **1. Prerequisites**

Before running, ensure you have:

* 🐍 **Python 3.9+**
* 💾 A **quantized LLM model file** (e.g., `phi4.gguf`)
* 🔑 Reddit API credentials (for live scraping)

---

### **2. Install Dependencies**

Install all necessary Python packages:

```bash
pip install -r requirements.txt
```

---

### **3. Configure Reddit API Credentials**

Before running live analysis, authenticate the Reddit scraper.

#### 🔹 Step 1: Create a Reddit App

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps).
2. Click **"Create App"** → select **"script"** type.
3. Fill in:

   * **Name:** `Bharat-AI`
   * **Redirect URI:** `http://localhost:8080`
4. Save to obtain your **Client ID** and **Client Secret**.

#### 🔹 Step 2: Apply Credentials in `reddit.py`

```python
import os
import praw

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "your_client_id")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "your_client_secret")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "Bharat-FactCheck-App by /u/your_username")

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)
```

> 💡 **Tip:** Export credentials securely from terminal:
>
> ```bash
> export REDDIT_CLIENT_ID="your_client_id"
> export REDDIT_CLIENT_SECRET="your_client_secret"
> export REDDIT_USER_AGENT="Bharat-FactCheck-App by /u/your_username"
> ```

---

### **4. Run the Application**

Once dependencies and credentials are ready, launch the app:

```bash
streamlit run final5.py
```

Then open the app in your browser:

```
http://localhost:8501
```

You’ll see the **Bharat Dashboard**, where you can:

* Enter any **claim or topic** (e.g., “Harshad Mehta Scam 1992”)
* Choose between:

  * **Live Analysis (Full Pipeline)** — Runs full Reddit + LLM workflow
  * **Test Mode (Mock Data)** — Runs demo with built-in examples
* Explore visual summaries, classification metrics, and detailed explanations.

---

## 🧠 In-App Information Sections

The updated UI includes:

* **Title:** `🇮🇳 Bharat: Regional Language Fact News Detection System`
* **Subheader:** Highlights multilingual, evidence-based approach.
* **Expander Section:** Describes the purpose and methodology.
* **Sidebar Tagline:** Short project summary for context.
* **Footer:** `Built for the Agentic AI - Misinformation Track | Team Bharat`

---

## 🖥️ Example Output

* Interactive classification charts
* Summarized claim statistics
* Transparent, citation-backed reasoning

```
✅ TRUE CLAIM
Claim: "Harshad Mehta was trapped by bureaucrats and journalists."
Reason: Supported by multiple Reddit posts verifying this narrative.
Source URL: https://www.reddit.com/r/indianews/comments/def456/
```

---

## 📁 Project Structure

| File                        | Description                                                     |
| --------------------------- | --------------------------------------------------------------- |
| `final5.py`                 | 🎨 Streamlit App — updated UI and orchestration logic.          |
| `final.py`                  | 🧠 Analysis Core — chunking, batching, and LLM-based reasoning. |
| `reddit.py`                 | 🔎 Reddit Scraper — PRAW integration and search management.     |                 |
| `requirements.txt`          | 📦 Project dependencies.                                        |
| `reddit_search_output.json` | 💾 Raw scraped Reddit data.                                     |
| `README.md`                 | 📘 Documentation file.                                          |

---

## 🤝 Contributing

We welcome contributions!
Improve multilingual support, optimize prompts, or enhance visualization — just submit a PR.

---

## 📜 License

Licensed under the **MIT License** — see [LICENSE](./LICENSE) for details.

---

### 💡 Summary

**Bharat AI** is a next-generation misinformation detection framework combining local LLMs and transparent reasoning.
It offers multilingual verification, context awareness, and a user-friendly interface for real-time fact-checking across India.

> **Developed with ❤️ by Team Bharat | Agentic AI - Misinformation Track**
