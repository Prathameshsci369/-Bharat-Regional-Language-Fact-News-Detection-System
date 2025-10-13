# 🧠 FND-AI: Fake News Detection and Analysis Platform

![Streamlit](https://img.shields.io/badge/Built%20With-Streamlit-FF4B4B?logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-success)

---

## 📘 Overview

**FND-AI** (Fake News Detection and Analysis Platform) is a proof-of-concept web application built with **Streamlit** that orchestrates a complete pipeline to **detect and classify potential fake news claims** found in social media discussions — specifically **Reddit**.

It uses a **local Large Language Model (LLM)** (e.g., *Phi-4 via llama-cpp-python*) to automatically **extract, verify, and classify claims** as **True**, **False**, **Misleading**, or **Unverifiable**.

---

## ⚙️ How It Works (Pipeline Overview)

The analysis pipeline executes in **four main stages**:

### 1️⃣ User Query Input

* The user enters a topic or claim in the UI.
* This query is passed directly to the `reddit.py` module, which initiates a targeted search on Reddit.

### 2️⃣ Data Scraping (PRAW)

* The Reddit API (via PRAW) is used to scrape relevant **posts and comments**.
* The collected data is stored in a JSON file named **`reddit_search_output.json`**.

### 3️⃣ Data Preparation (LangChain)

* The scraped text is loaded and split into smaller **text chunks** using `RecursiveCharacterTextSplitter`.
* These chunks are then grouped into **manageable batches** for efficient processing.

### 4️⃣ Claim Analysis (Local LLM - Phi-4)

* Each batch is analyzed by the **local LLM (Phi-4)** via `llama-cpp-python`.
* The model performs **zero-shot classification**, identifying and labeling each claim as:

  * ✅ True
  * ❌ False
  * ⚠️ Misleading
  * ❓ Unverifiable

### 5️⃣ Reporting (Streamlit)

* The results are displayed through the **Streamlit UI (`final5.py`)**.
* Features include:

  * Interactive **visual charts** (Altair)
  * **Color-coded claim cards**
  * **Summary metrics** for each claim category

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

Before running live analysis, you must authenticate the Reddit scraper.

#### 🔹 Step 1: Create a Reddit App

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps).
2. Click **"Create App"** or **"Create Another App"**.
3. Select **"script"** as the app type.
4. Set:

   * **Name:** `FND-AI`
   * **Redirect URI:** `http://localhost:8080`
5. Save the app — you’ll now see your **Client ID** and **Client Secret**.

#### 🔹 Step 2: Apply Credentials in `reddit.py`

Open your `reddit.py` file and update your environment variable section as follows:

```python
import os
import praw

# Load Reddit API credentials from environment variables
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "your_client_id")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "your_client_secret")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "FND-AI-App by /u/your_username")

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)
```

> 💡 **Tip:** To keep credentials secure, define them in your system environment before running the app:
>
> ```bash
> export REDDIT_CLIENT_ID="your_client_id"
> export REDDIT_CLIENT_SECRET="your_client_secret"
> export REDDIT_USER_AGENT="FND-AI-App by /u/your_username"
> ```

---

### **4. Run the Application**

Once dependencies and credentials are set up, you can start the platform.

#### 🔹 Step 1: Run Streamlit

In your terminal, navigate to the project directory and run:

```bash
streamlit run final5.py
```

#### 🔹 Step 2: Open in Browser

After launching, Streamlit will automatically open your default browser with a URL like:

```
http://localhost:8501
```

You’ll see the **FND-AI Dashboard**, where you can:

* Enter any **claim or topic** (e.g., “Harshad Mehta Scam 1992”)
* Choose between:

  * **Live Analysis (Full Pipeline)** — Runs the full Reddit + LLM pipeline
  * **Test Mode (Mock Data)** — Loads built-in demo results
* View visual analytics, claim classifications, and detailed explanations.

---

## 🖥️ Example Output

When the app runs successfully, you’ll see:

* ✅ A sidebar with mode selection and configuration info
* 🧠 Interactive visualizations showing classification distributions
* 🗞️ Claim cards like:

```
✅ TRUE CLAIM
Claim: "Harshad Mehta was trapped by bureaucrats, politicians, and journalists."
Reason: Supported by multiple Reddit posts confirming this narrative.
Source URL: https://www.reddit.com/r/indianews/comments/def456/
```

---

## ✅ You’re Ready to Go!

The app is now live at **[http://localhost:8501](http://localhost:8501)** 🎉
You can start analyzing claims, viewing their truth classifications, and exploring how the local LLM interprets context from real-world Reddit discussions.

> 🧭 For mock data preview, switch to **Test Mode** in the sidebar — no Reddit API or LLM setup needed.

## 📁 Project Structure

| File                        | Description                                                       |
| --------------------------- | ----------------------------------------------------------------- |
| `final5.py`                 | 🎨 Streamlit App — main UI and orchestration logic.               |
| `final.py`                  | 🧠 Analysis Core — handles chunking, batching, and LLM reasoning. |
| `reddit.py`                 | 🔎 Reddit Scraper — manages API integration and query search.     |                           |
| `requirements.txt`          | 📦 Project dependencies.                                          |
| `reddit_search_output.json` | 💾 Output of scraped Reddit data.                                 |
| `README.md`                 | 📘 Documentation file.                                            |

---

## 🤝 Contributing

Contributions are welcome!
If you’d like to improve the LLM prompt, enhance multilingual support, or refine the visualization layer, please open a pull request.

---

## 📜 License

Licensed under the **MIT License** — see [LICENSE](./LICENSE) for details.

---

### 💡 Summary

FND-AI demonstrates how **local LLMs + open-source frameworks** can power transparent and multilingual **fake news detection** systems.
It’s built to show how **agentic AI reasoning** can operate locally, verifying claims directly from public discussions — without relying on external APIs.

> **Developed with ❤️ by Team Bharat | FND-AI**
