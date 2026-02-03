# 📚 Locus - PDF Semantic Search

**Find the exact page that answers your question.**

A lightweight desktop tool for students to search through course PDFs using natural language. 

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## ✨ Features

- **Hybrid Search** — Combines keyword matching (BM25) with semantic understanding
- **Two Index Modes** — Fast mode for quick startup, Deep mode for comprehensive search
- **Multilingual Support** — Search Chinese documents with English queries (and vice versa)
- **Works Offline** — No internet needed after initial setup
- **Open PDF at Page** — Double-click a result to jump directly to that page
- **Adjustable Search Mode** — Slider to balance between semantic and literal matching

---

## 🚀 Quick Start

### Option A: Download Executable (Windows)

Download the latest release from [Releases](https://github.com/llk214/semantic-locator/releases) and run `Locus.exe`.

### Option B: Run from Source

```bash
# Clone the repo
git clone https://github.com/llk214/semantic-locator.git
cd semantic-locator

# Install dependencies
pip install -r requirements.txt

# Run
python gui.py
```

---

## 📖 How to Use

1. Click **Browse** and select a folder containing your PDFs
2. Click **Load Index** and choose index mode:
   - **⚡ Fast Index** — Quick startup, good for small collections
   - **🔬 Deep Index** — Slower startup, finds all semantically related content
3. Type your question and hit **Search**
4. Double-click any result to open the PDF at that page

---

## 🎛️ Model Options

Choose based on your hardware and needs:

| Option | Size | RAM | Best For            |
|--------|------|-----|---------------------|
| ⚡ Fast | ~80MB | 4GB | Any laptop, fastest |
| ⚖️ Balanced | ~130MB | 4GB | Standard laptops    |
| 🎯 High Accuracy | ~440MB | 8GB | Better results      |
| 🚀 Best | ~1.3GB | 16GB | Performance PCs     |
| 🌍 Multilingual | ~2.2GB | 16GB+ | 100+ languages      |

---

## 🔬 Index Modes

| Mode | Startup | Search | Use When |
|------|---------|--------|----------|
| ⚡ Fast | Quick | Good | Small collections, quick lookups |
| 🔬 Deep | Slower | Best | Large collections, thorough research |

**Deep mode** pre-computes embeddings for all pages, enabling:
- Full semantic search across all documents
- Finding related content even without keyword matches
- Cross-lingual search (with Multilingual model)

---

## 🌍 Multilingual Search

With the **🌍 Multilingual** model, you can:
- Search Chinese PDFs with English queries
- Search English PDFs with Chinese queries
- Mix languages in your document collection

When cross-lingual search is active, you'll see: `🌍 Cross-lingual: X results (semantic only)`

---

## 🎚️ Search Mode Slider

Adjust how search works:

```
🧠 Semantic ◀━━━━━━━━━━▶ 🔤 Literal
```

| Slide Left | Slide Right |
|------------|-------------|
| Understands meaning | Matches exact words |
| *"How to prevent overfitting?"* | *"regularization"* |

---

## 📁 Supported Files

- ✅ PDF (`.pdf`)

> **Tip:** Export your `.pptx` and `.docx` files to PDF for best results

---

## 🛠️ Requirements

- Python 3.8+
- ~500MB - 2.5GB disk space (depending on model)
- PDF reader with command-line support (e.g., [SumatraPDF](https://www.sumatrapdfreader.org/))

---

## 📦 Dependencies

```
PyMuPDF              # PDF text extraction
rank-bm25            # Keyword search
sentence-transformers # Semantic matching
customtkinter        # Modern GUI
```

---

## 💡 Tips for Better Results

1. **Use Deep mode** for large collections — ensures nothing is missed
2. **Use specific terms** — *"Q-learning update rule"* works better than *"how does it learn"*
3. **Adjust the slider** — Literal mode for exact terms, semantic mode for concepts
4. **Try Multilingual** — if you have mixed-language documents

---

## 🤔 FAQ

**What's the difference between Fast and Deep index?**  
Fast mode uses BM25 to filter candidates first (may miss semantically related pages). Deep mode searches all pages semantically (slower startup, better results).

**Is this an AI/LLM?**  
No. It uses embedding models for similarity matching, not generative AI. It finds information — it doesn't generate answers.

**Can I use this during exams?**  
If "no LLM" is the rule, this tool is fine — it's just a smart search engine for your own materials.

**Why doesn't the page jump work?**  
Install [SumatraPDF](https://www.sumatrapdfreader.org/) — it has the best command-line page navigation support.

---

## 📄 License

MIT — free for personal and educational use.

---

<p align="center">
  Made for students, by students 📖
</p>