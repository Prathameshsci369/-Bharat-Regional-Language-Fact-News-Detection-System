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
- The user enters a topic or claim in the UI.  
- This query is passed directly to the `reddit.py` module, which initiates a targeted search on Reddit.

### 2️⃣ Data Scraping (PRAW)
- The Reddit API (via PRAW) is used to scrape relevant **posts and comments**.  
- The collected data is stored in a JSON file named **`reddit_search_output.json`**.

### 3️⃣ Data Preparation (LangChain)
- The scraped text is loaded and split into smaller **text chunks** using `RecursiveCharacterTextSplitter`.  
- These chunks are then grouped into **manageable batches** for efficient processing.

### 4️⃣ Claim Analysis (Local LLM - Phi-4)
- Each batch is analyzed by the **local LLM (Phi-4)** via `llama-cpp-python`.  
- The model performs **zero-shot classification**, identifying and labeling each claim as:
  - ✅ True  
  - ❌ False  
  - ⚠️ Misleading  
  - ❓ Unverifiable

### 5️⃣ Reporting (Streamlit)
- The results are displayed through the **Streamlit UI (`final5.py`)**.  
- Features include:
  - Interactive **visual charts** (Altair)
  - **Color-coded claim cards**
  - **Summary metrics** for each claim category

---

## 🚀 Setup & Installation

### **1. Prerequisites**
Before running, ensure you have:

- 🐍 **Python 3.9+**
- 💾 A **quantized LLM model file** (e.g., `phi4.gguf`)
- 🔑 Reddit API credentials (for live scraping)

---

### **2. Install Dependencies**
Install all necessary Python packages:

```bash
pip install -r requirements.txt
