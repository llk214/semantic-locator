# Semantic Page Locator for Course PDFs

A hybrid BM25 + semantic search system to find which pages in your course materials answer a given question.

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install requirements
pip install -r requirements.txt
```

### 2. Organize Your PDFs

Put all your course PDFs in a single directory:
```
D:\NUS\EE3703\materials\
├── RL_lecture.pdf
├── Tutorial_1.pdf
├── Tutorial_2.pdf
└── ...
```

### 3. Run the Locator

**Option A: GUI (easiest)**
```bash
python gui.py
```
Then browse to your PDF directory and click "Load/Rebuild Index".

**Option B: Command Line**
```bash
# Interactive mode
python locator.py "D:\NUS\EE3703\materials" -i

# Single query
python locator.py "D:\NUS\EE3703\materials" -q "What is the Bellman equation?"

# More results
python locator.py "D:\NUS\EE3703\materials" -q "policy gradient" --top-k 10
```

## How It Works

```
Query: "What is the Bellman equation?"
         │
         ▼
┌─────────────────────────┐
│  Stage 1: BM25 Search   │  Fast keyword matching
│  (top 20 candidates)    │  No ML model needed
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Stage 2: Reranking     │  Semantic similarity
│  (MiniLM transformer)   │  Understands meaning
└──────────┬──────────────┘
           │
           ▼
    Results: Page 49-50
    (with confidence scores)
```

## Fine-Tuning (Optional)

To improve results for your specific courses:

### 1. Create Training Data

Edit `training_data_example.json` with your own question→page mappings:

```json
[
    {
        "question": "What is the Bellman equation?",
        "pdf": "RL_lecture.pdf",
        "pages": [49, 50]
    },
    ...
]
```

Aim for ~50 examples covering different topics.

### 2. Run Fine-Tuning

```python
from locator import HybridLocator, TrainingDataGenerator, fine_tune_reranker

# Load locator
locator = HybridLocator("D:/NUS/EE3703/materials")
locator.build_index()

# Load training data
training_data = TrainingDataGenerator.from_json("training_data.json")

# Fine-tune (saves to ./fine_tuned_model/)
fine_tune_reranker(locator, training_data, "./fine_tuned_model", epochs=3)
```

### 3. Use Fine-Tuned Model

```python
locator = HybridLocator(
    "D:/NUS/EE3703/materials",
    model_name="./fine_tuned_model"
)
```

## API Usage

```python
from locator import HybridLocator

# Initialize
locator = HybridLocator("D:/NUS/EE3703/materials")
locator.build_index()  # First time takes ~30s, cached after

# Search
results = locator.search("What is Q-learning?", top_k=5)

for r in results:
    print(f"{r['pdf_name']} - Page {r['page_num']} (score: {r['score']})")
    print(f"  {r['snippet']}")
```

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `top_k` | 5 | Number of results to return |
| `bm25_candidates` | 20 | Candidates from BM25 stage |
| `bm25_weight` | 0.3 | Weight for keyword matching (0-1) |

- Higher `bm25_weight` = favors exact keyword matches
- Lower `bm25_weight` = favors semantic similarity

## Performance Tips

1. **First run is slow** - The model downloads (~80MB) and PDFs are indexed
2. **Index is cached** - Subsequent runs use `.locator_cache.pkl`
3. **Force rebuild** - Use `--rebuild` flag if you add new PDFs
4. **GPU acceleration** - Install CUDA-enabled PyTorch for faster reranking

## Troubleshooting

**"No results found"**
- Check if PDFs have extractable text (not scanned images)
- Try broader search terms

**Slow performance**
- Reduce `bm25_candidates` for faster (but less accurate) results
- Use GPU if available

**Memory issues**
- Process fewer PDFs at once
- The model uses ~500MB RAM

## File Structure

```
semantic_locator/
├── locator.py              # Main search engine
├── gui.py                  # tkinter GUI
├── requirements.txt        # Dependencies
├── training_data_example.json  # Template for fine-tuning
└── README.md
```
