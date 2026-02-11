"""
Hybrid Semantic Page Locator for Course PDFs
BM25 keyword search + FastEmbed reranking (lightweight ONNX-based)
"""

import os
import sys
import json
import pickle
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ----------------------------
# Bundled model configuration
# ----------------------------
BUNDLED_MODEL_NAME = "BAAI/bge-small-en-v1.5"

def _get_bundled_model_path() -> Optional[str]:
    """Get path to bundled model if it exists (for PyInstaller builds)."""
    # Check various locations where bundled model might be
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller exe
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        possible_paths = [
            os.path.join(base_path, '_internal', 'models', 'bge-small-en-v1.5'),
            os.path.join(base_path, 'models', 'bge-small-en-v1.5'),
            os.path.join(os.path.dirname(sys.executable), '_internal', 'models', 'bge-small-en-v1.5'),
            os.path.join(os.path.dirname(sys.executable), 'models', 'bge-small-en-v1.5'),
        ]
    else:
        # Running as script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths = [
            os.path.join(script_dir, 'models', 'bge-small-en-v1.5'),
        ]
    
    for path in possible_paths:
        # Check if model.onnx exists in the path
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                if 'model.onnx' in files or 'model_optimized.onnx' in files:
                    return path
    return None


# ----------------------------
# FastEmbed cache configuration
# ----------------------------
def _default_fastembed_cache_dir() -> str:
    """Choose a persistent cache directory for FastEmbed (avoid system Temp)."""
    home = str(Path.home())
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or home
        return os.path.join(base, "Locus", "fastembed_cache")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Caches", "Locus", "fastembed_cache")
    return os.path.join(home, ".cache", "Locus", "fastembed_cache")

# Set once, early, so all FastEmbed usage is consistent across the app.
os.environ.setdefault("FASTEMBED_CACHE_PATH", _default_fastembed_cache_dir())
os.makedirs(os.environ["FASTEMBED_CACHE_PATH"], exist_ok=True)


def _compute_pdf_dir_hash(pdf_dir: Path) -> str:
    """Compute a stable hash of PDF files (name, size, mtime)."""
    h = hashlib.sha1()
    pdf_files = sorted(p for p in pdf_dir.glob("*.pdf"))
    for p in pdf_files:
        try:
            stat = p.stat()
            h.update(str(p.name).encode("utf-8"))
            h.update(str(stat.st_size).encode("utf-8"))
            h.update(str(stat.st_mtime).encode("utf-8"))
        except OSError:
            continue
    return h.hexdigest()


def _default_index_cache_dir() -> Path:
    """Persistent cache directory for index files."""
    home = str(Path.home())
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or home
        return Path(base) / "Locus" / "index_cache"
    if sys.platform == "darwin":
        return Path(home) / "Library" / "Caches" / "Locus" / "index_cache"
    return Path(home) / ".cache" / "Locus" / "index_cache"


def _index_cache_prefix(pdf_dir: Path, ocr_mode: str, ocr_dpi: int) -> str:
    """Stable prefix for cache files per folder + OCR settings."""
    folder_hash = _compute_pdf_dir_hash(pdf_dir)
    return f"locator_{folder_hash}_{ocr_mode}_dpi{ocr_dpi}"

import fitz  # PyMuPDF
import numpy as np
from rank_bm25 import BM25Okapi
import re

def _default_ocr_cache_dir() -> str:
    """Choose a persistent cache directory for OCR results."""
    home = str(Path.home())
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or home
        return os.path.join(base, "Locus", "ocr_cache")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Caches", "Locus", "ocr_cache")
    return os.path.join(home, ".cache", "Locus", "ocr_cache")

class OCRProcessor:
    """Optional OCR processor with disk cache."""

    def __init__(self):
        self.cache_dir = _default_ocr_cache_dir()
        os.makedirs(self.cache_dir, exist_ok=True)
        self._mem_cache: dict[str, str] = {}
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._ocr = RapidOCR()
            self.available = True
            self._err = None
        except Exception as e:
            self._ocr = None
            self.available = False
            self._err = str(e)

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.txt")

    def _load_cache(self, key: str) -> Optional[str]:
        if key in self._mem_cache:
            return self._mem_cache[key]
        path = self._cache_path(key)
        if os.path.exists(path):
            try:
                text = Path(path).read_text(encoding="utf-8")
                self._mem_cache[key] = text
                return text
            except OSError:
                return None
        return None

    def _save_cache(self, key: str, text: str) -> None:
        self._mem_cache[key] = text
        path = self._cache_path(key)
        try:
            Path(path).write_text(text, encoding="utf-8")
        except OSError:
            pass

    def ocr_image(self, img: np.ndarray) -> str:
        if not self.available or self._ocr is None:
            return ""

        try:
            result = self._ocr(img)
        except Exception:
            return ""

        if isinstance(result, tuple):
            result = result[0]
        if not isinstance(result, list):
            return ""

        texts = []
        for item in result:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                texts.append(str(item[1]))
            elif isinstance(item, dict):
                text_val = item.get("text")
                if text_val:
                    texts.append(str(text_val))
        return " ".join(t for t in texts if t).strip()

    def ocr_page(self, cache_key: str, page: fitz.Page, dpi: int) -> str:
        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached

        try:
            pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB)
            img = np.frombuffer(pix.samples, dtype=np.uint8)
            img = img.reshape(pix.height, pix.width, 3)
        except Exception:
            return ""

        text = self.ocr_image(img)
        self._save_cache(cache_key, text)
        return text



@dataclass
class PageDocument:
    """Represents a single page from a PDF."""
    pdf_name: str
    page_num: int  # 1-indexed for user display
    text: str
    chunk_id: int = 0
    tokens: list = field(default_factory=list)
    
    def __post_init__(self):
        if not self.tokens:
            self.tokens = tokenize(self.text)
    
    @property
    def doc_id(self) -> str:
        if self.chunk_id:
            return f"{self.pdf_name}::page_{self.page_num}::chunk_{self.chunk_id}"
        return f"{self.pdf_name}::page_{self.page_num}"


def tokenize(text: str) -> list[str]:
    """Tokenization supporting English and Chinese."""
    text = text.lower()
    
    # Extract English words
    english_tokens = re.findall(r'\b[a-z0-9]+\b', text)
    
    # Extract Chinese characters (each character is a token)
    chinese_tokens = re.findall(r'[\u4e00-\u9fff]', text)
    
    # Combine tokens
    tokens = english_tokens + chinese_tokens
    
    # Remove English stopwords
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                 'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
                 'during', 'before', 'after', 'above', 'below', 'between', 'under',
                 'again', 'further', 'then', 'once', 'here', 'there', 'when',
                 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most',
                 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
                 'same', 'so', 'than', 'too', 'very', 'just', 'and', 'but',
                 'if', 'or', 'because', 'until', 'while', 'this', 'that', 'these',
                 'those', 'it', 'its'}
    def _is_cjk_char(tok: str) -> bool:
        return len(tok) == 1 and '\u4e00' <= tok <= '\u9fff'

    return [t for t in tokens if (len(t) > 1 or _is_cjk_char(t)) and t not in stopwords]


class PDFIndexer:
    """Extracts and indexes text from PDFs."""
    _MAX_TOKENS = 400
    _OVERLAP_TOKENS = 80

    def __init__(self, pdf_dir: str, ocr_mode: str = "fast", ocr_progress_callback=None,
                 ocr_dpi: int = 200, cancel_event=None):
        self.pdf_dir = Path(pdf_dir)
        self.documents: list[PageDocument] = []
        self.ocr_mode = ocr_mode
        self.ocr_progress_callback = ocr_progress_callback
        self.ocr_dpi = ocr_dpi
        self.cancel_event = cancel_event
        if self.ocr_mode == "off":
            self.ocr = None
        else:
            self.ocr = OCRProcessor()
            if not self.ocr.available:
                print(f"OCR disabled (rapidocr-onnxruntime not available): {self.ocr._err}")

    def _pdf_cache_key(self, pdf_path: Path, page_num: int) -> str:
        base = f"{pdf_path.resolve()}::{pdf_path.stat().st_mtime}::{page_num}::{self.ocr_dpi}"
        return hashlib.sha1(base.encode("utf-8")).hexdigest()

    def _split_units(self, text: str) -> list[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        units: list[str] = []
        for p in paragraphs:
            parts = re.split(r"(?<=[\.\?\!。！？])\s+", p)
            if len(parts) == 1:
                lines = [l.strip() for l in p.splitlines() if l.strip()]
                units.extend(lines if lines else [p.strip()])
            else:
                units.extend([s.strip() for s in parts if s.strip()])
        return units

    def _chunk_text(self, text: str) -> list[str]:
        units = self._split_units(text)
        if not units:
            return []

        chunks: list[str] = []
        window: list[tuple[str, int]] = []
        total_tokens = 0

        for unit in units:
            tok_count = len(tokenize(unit))
            if tok_count == 0:
                tok_count = 1

            if total_tokens + tok_count > self._MAX_TOKENS and window:
                chunks.append(" ".join(u for u, _ in window).strip())
                while window and total_tokens > self._OVERLAP_TOKENS:
                    _, t = window.pop(0)
                    total_tokens -= t

            window.append((unit, tok_count))
            total_tokens += tok_count

        if window:
            chunks.append(" ".join(u for u, _ in window).strip())

        return [c for c in chunks if c]
        
    def extract_all(self) -> list[PageDocument]:
        """Extract text from all PDFs in directory."""
        self.documents = []
        
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files")
        
        for pdf_path in pdf_files:
            if self.cancel_event is not None and self.cancel_event.is_set():
                break
            print(f"  Processing: {pdf_path.name}")
            self._extract_pdf(pdf_path)
        
        print(f"Total pages indexed: {len(self.documents)}")
        return self.documents
    
    def _extract_pdf(self, pdf_path: Path):
        """Extract text from a single PDF."""
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            for page_num in range(total_pages):
                if self.cancel_event is not None and self.cancel_event.is_set():
                    break
                page = doc[page_num]
                text = page.get_text()
                ocr_text = ""
                has_images = bool(page.get_images(full=True))
                cache_key = self._pdf_cache_key(pdf_path, page_num)

                if self.ocr_mode == "deep":
                    if has_images and self.ocr and self.ocr.available:
                        if self.ocr_progress_callback:
                            self.ocr_progress_callback(pdf_path.name, page_num + 1, total_pages)
                        ocr_text = self.ocr.ocr_page(cache_key, page, self.ocr_dpi)
                elif self.ocr_mode == "fast":
                    if has_images and len(text.strip()) < 20 and self.ocr and self.ocr.available:
                        if self.ocr_progress_callback:
                            self.ocr_progress_callback(pdf_path.name, page_num + 1, total_pages)
                        ocr_text = self.ocr.ocr_page(cache_key, page, self.ocr_dpi)

                if ocr_text:
                    text = f"{text}\n{ocr_text}".strip()

                # Skip nearly empty pages
                min_chars = 10 if ocr_text else 50
                if len(text.strip()) < min_chars:
                    continue

                chunks = self._chunk_text(text)
                if not chunks:
                    continue

                for idx, chunk_text in enumerate(chunks, 1):
                    self.documents.append(PageDocument(
                        pdf_name=pdf_path.name,
                        page_num=page_num + 1,  # 1-indexed
                        text=chunk_text,
                        chunk_id=idx
                    ))
            doc.close()
        except Exception as e:
            print(f"    Error processing {pdf_path.name}: {e}")


class BM25Retriever:
    """BM25-based first-stage retrieval."""
    
    def __init__(self, documents: list[PageDocument]):
        self.documents = documents
        self.corpus = [doc.tokens for doc in documents]
        self.bm25 = BM25Okapi(self.corpus)
    
    def search(self, query: str, top_k: int = 20) -> list[tuple[PageDocument, float]]:
        """Return top-k documents with BM25 scores."""
        query_tokens = tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include docs with non-zero scores
                results.append((self.documents[idx], scores[idx]))
        
        return results


# Model name mapping: GUI names -> FastEmbed model names
MODEL_NAME_MAP = {
    # English models
    "BAAI/bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
    "BAAI/bge-base-en-v1.5": "BAAI/bge-base-en-v1.5",
    "BAAI/bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
    # Chinese models
    "BAAI/bge-small-zh-v1.5": "BAAI/bge-small-zh-v1.5",
    "BAAI/bge-large-zh-v1.5": "BAAI/bge-large-zh-v1.5",
    # Multilingual
    "intfloat/multilingual-e5-large": "intfloat/multilingual-e5-large",
}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query vector and document vectors."""
    # Normalize vectors
    a_norm = a / np.linalg.norm(a)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)
    return np.dot(b_norm, a_norm)


def _percentile_normalize(scores: np.ndarray, p_low: float = 5.0, p_high: float = 95.0,
                          eps: float = 1e-8) -> np.ndarray:
    """Robustly normalize scores to [0,1] using percentiles with fallback."""
    if scores.size == 0:
        return scores
    if scores.size < 20:
        s_min = float(scores.min())
        s_max = float(scores.max())
        denom = s_max - s_min
        if denom < eps:
            return np.zeros_like(scores)
        return (scores - s_min) / denom
    p5 = float(np.percentile(scores, p_low))
    p95 = float(np.percentile(scores, p_high))
    denom = p95 - p5
    if denom < eps:
        s_min = float(scores.min())
        s_max = float(scores.max())
        denom2 = s_max - s_min
        if denom2 < eps:
            return np.zeros_like(scores)
        return (scores - s_min) / denom2
    return np.clip((scores - p5) / denom, 0.0, 1.0)


class SemanticReranker:
    """FastEmbed-based semantic reranking (lightweight ONNX)."""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding
        
        print(f"Loading search model: {model_name}")
        
        # Map model name if needed
        fastembed_name = MODEL_NAME_MAP.get(model_name, model_name)
        cache_dir = os.environ.get("FASTEMBED_CACHE_PATH")
        
        # Check if we should use bundled model
        bundled_path = _get_bundled_model_path()
        if bundled_path and model_name == BUNDLED_MODEL_NAME:
            print(f"Using bundled model from: {bundled_path}")
            # Use local_files_only to prevent download attempts
            self.model = TextEmbedding(
                model_name=fastembed_name,
                cache_dir=cache_dir,
                local_files_only=False  # Still allow fallback to download
            )
            # Copy bundled model to cache if not already there
            self._ensure_bundled_model_in_cache(bundled_path, cache_dir, fastembed_name)
        else:
            print("(First run downloads the model - please wait...)")
            self.model = TextEmbedding(model_name=fastembed_name, cache_dir=cache_dir)
        
        self.model_name = model_name
        
        # Check if this model needs query/passage prefixes
        # BGE models and E5 models both use these prefixes
        self.needs_prefix = "bge" in model_name.lower() or "e5" in model_name.lower()
        print("Model loaded successfully!")
    
    def _ensure_bundled_model_in_cache(self, bundled_path: str, cache_dir: str, model_name: str):
        """Copy bundled model to cache directory if not already present."""
        import shutil
        
        # FastEmbed expects models in a specific structure
        # We'll copy to cache so it can find it naturally
        model_short = model_name.split("/")[-1]
        
        # Check if model already exists in cache
        if cache_dir:
            for folder in os.listdir(cache_dir) if os.path.exists(cache_dir) else []:
                if model_short in folder:
                    folder_path = os.path.join(cache_dir, folder)
                    for root, dirs, files in os.walk(folder_path):
                        if 'model.onnx' in files or 'model_optimized.onnx' in files:
                            return  # Model already in cache
        
        # Model not in cache, but bundled model exists - FastEmbed will handle it
    
    def _add_prefix(self, text: str, is_query: bool = False) -> str:
        """Add prefix for BGE/E5 models."""
        if not self.needs_prefix:
            return text
        if is_query:
            return f"query: {text}"
        else:
            return f"passage: {text}"
    
    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        """Encode texts to embeddings."""
        # Add prefixes for BGE models
        prefixed_texts = [self._add_prefix(t, is_query) for t in texts]
        # FastEmbed returns a generator, convert to numpy array
        embeddings = list(self.model.embed(prefixed_texts))
        return np.array(embeddings)
    
    def encode_single(self, text: str, is_query: bool = False) -> np.ndarray:
        """Encode a single text to embedding."""
        return self.encode([text], is_query)[0]
    
    def rerank(self, query: str, candidates: list[tuple[PageDocument, float]], 
               top_k: int = 5, bm25_weight: float = 0.3,
               fusion_method: str = "rrf") -> list[tuple[PageDocument, float]]:
        """
        Rerank candidates using semantic similarity.
        
        Args:
            query: The search query
            candidates: List of (document, bm25_score) tuples
            top_k: Number of results to return
            bm25_weight: Weight for BM25 score in final ranking (0-1)
        """
        if not candidates:
            return []
        
        # Encode query
        query_embedding = self.encode_single(query, is_query=True)
        
        # Encode all candidate texts (truncate long pages)
        texts = [doc.text[:2000] for doc, _ in candidates]
        doc_embeddings = self.encode(texts, is_query=False)
        
        # Compute semantic similarities
        semantic_scores = cosine_similarity(query_embedding, doc_embeddings)
        semantic_scores = semantic_scores.astype(float)

        bm25_scores = np.array([score for _, score in candidates], dtype=float)

        if fusion_method == "rrf":
            # Reciprocal Rank Fusion (RRF)
            k = 60.0
            sem_rank = np.argsort(semantic_scores)[::-1]
            bm_rank = np.argsort(bm25_scores)[::-1]
            sem_pos = np.empty_like(sem_rank)
            bm_pos = np.empty_like(bm_rank)
            sem_pos[sem_rank] = np.arange(1, len(sem_rank) + 1)
            bm_pos[bm_rank] = np.arange(1, len(bm_rank) + 1)
            combined_scores = (1.0 / (k + sem_pos)) + (1.0 / (k + bm_pos))
        else:
            # Percentile-normalized linear blend
            semantic_scores = _percentile_normalize(semantic_scores)
            bm25_scores = _percentile_normalize(bm25_scores)
            combined_scores = (1 - bm25_weight) * semantic_scores + bm25_weight * bm25_scores

        # Sort by combined score
        sorted_indices = np.argsort(combined_scores)[::-1][:top_k]
        
        results = []
        for idx in sorted_indices:
            doc, _ = candidates[idx]
            score = None if fusion_method == "rrf" else float(combined_scores[idx])
            results.append((doc, score))
        
        return results


class HybridLocator:
    """Main interface combining BM25 + semantic reranking."""
    
    def __init__(self, pdf_dir: str, model_name: Optional[str] = "BAAI/bge-small-en-v1.5"):
        self.pdf_dir = Path(pdf_dir)
        self.model_name = model_name
        self.indexer: Optional[PDFIndexer] = None
        self.bm25: Optional[BM25Retriever] = None
        self.reranker: Optional[SemanticReranker] = None
        self.documents: list[PageDocument] = []
        self.doc_embeddings = None  # Pre-computed embeddings
        self.deep_mode = False  # Whether using pre-computed embeddings
        
    def build_index(self, force_rebuild: bool = False, ocr_mode: str = "fast",
                    ocr_progress_callback=None, ocr_dpi: int = 200, cancel_event=None):
        """Build or load the search index."""
        if ocr_mode not in ("fast", "deep", "off"):
            ocr_mode = "fast"
        cache_dir = _default_index_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        prefix = _index_cache_prefix(self.pdf_dir, ocr_mode, ocr_dpi)
        cache_path = cache_dir / f"{prefix}.pkl"
        meta_path = cache_dir / f"{prefix}.meta.json"

        # Try to load from cache
        if not force_rebuild and cache_path.exists():
            dir_hash = _compute_pdf_dir_hash(self.pdf_dir)
            use_cache = True
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    if meta.get("dir_hash") != dir_hash:
                        use_cache = False
                except Exception:
                    use_cache = False
            else:
                use_cache = False

            if not use_cache:
                print("PDF folder changed, rebuilding index...")
            else:
                print("Loading index from cache...")
                with open(cache_path, 'rb') as f:
                    self.documents = pickle.load(f)
                print(f"Loaded {len(self.documents)} pages from cache")
                # Initialize retrievers
                if not self.documents:
                    self.bm25 = None
                    self.reranker = None
                    self.deep_mode = False
                    self.doc_embeddings = None
                    print("No searchable pages found in the selected directory.")
                    return
                self.bm25 = BM25Retriever(self.documents)
                if self.model_name:
                    self.reranker = SemanticReranker(self.model_name)
                else:
                    self.reranker = None
                    print("Running in keywords-only mode (no semantic reranking)")
                return
        else:
            # Build fresh index
            print("Building index from PDFs...")
            self.indexer = PDFIndexer(self.pdf_dir, ocr_mode=ocr_mode,
                                      ocr_progress_callback=ocr_progress_callback,
                                      ocr_dpi=ocr_dpi, cancel_event=cancel_event)
            self.documents = self.indexer.extract_all()

            if cancel_event is not None and cancel_event.is_set():
                # Ensure no partial cache is left behind
                if cache_path.exists():
                    try:
                        cache_path.unlink()
                    except Exception:
                        pass
                if meta_path.exists():
                    try:
                        meta_path.unlink()
                    except Exception:
                        pass
                raise RuntimeError("Indexing canceled")
            
            # Cache for next time
            with open(cache_path, 'wb') as f:
                pickle.dump(self.documents, f)
            try:
                meta = {"dir_hash": _compute_pdf_dir_hash(self.pdf_dir)}
                meta_path.write_text(json.dumps(meta), encoding="utf-8")
            except Exception:
                pass
            print("Index cached for future use")
        
        # If nothing was indexed, leave retrievers unset.
        if not self.documents:
            self.bm25 = None
            self.reranker = None
            self.deep_mode = False
            self.doc_embeddings = None
            print("No searchable pages found in the selected directory.")
            return

        # Initialize retrievers
        self.bm25 = BM25Retriever(self.documents)

        # Only load semantic model if specified
        if self.model_name:
            self.reranker = SemanticReranker(self.model_name)
        else:
            self.reranker = None
            print("Running in keywords-only mode (no semantic reranking)")
    
    def precompute_embeddings(self, progress_callback=None, cancel_event=None):
        """Pre-compute embeddings for all documents (Deep mode).
        
        Args:
            progress_callback: Optional function(current, total) to report progress
        """
        if not self.reranker:
            print("No semantic model loaded, skipping embedding computation")
            return
        if not self.documents:
            print("No documents to embed.")
            return
        
        total = len(self.documents)
        print(f"Computing embeddings for {total} pages...")
        
        # Prepare texts (truncate long pages)
        texts = [doc.text[:2000] for doc in self.documents]
        
        # Encode in batches to show progress
        batch_size = 10
        all_embeddings = []
        
        for i in range(0, total, batch_size):
            if cancel_event is not None and cancel_event.is_set():
                self.doc_embeddings = None
                self.deep_mode = False
                raise RuntimeError("Indexing canceled")
            batch_texts = texts[i:i+batch_size]
            batch_embeddings = self.reranker.encode(batch_texts, is_query=False)
            all_embeddings.append(batch_embeddings)
            
            # Report progress
            current = min(i + batch_size, total)
            if progress_callback:
                progress_callback(current, total)
            print(f"  Processed {current}/{total} pages...")
        
        # Combine all embeddings
        import numpy as np
        self.doc_embeddings = np.vstack(all_embeddings)
        self.deep_mode = True
        print("Embeddings computed and ready!")
        
    def search(self, query: str, top_k: int = 5, bm25_candidates: int = 20,
               bm25_weight: float = 0.3, fusion_method: str = "rrf") -> tuple[list[dict], bool]:
        """
        Search for pages relevant to the query.
        
        Args:
            query: Natural language question
            top_k: Number of results to return
            bm25_candidates: Number of candidates from BM25 stage
            bm25_weight: Weight for BM25 in final score (0-1)
            
        Returns:
            Tuple of (results list, is_cross_lingual flag)
        """
        if not self.documents:
            return [], False
        if self.bm25 is None:
            raise RuntimeError("Index not built. Call build_index() first.")
        
        is_cross_lingual = False
        
        # Check if using multilingual model
        is_multilingual_model = self.model_name and (
            "multilingual" in self.model_name.lower() 
            or "e5" in self.model_name.lower()
            or "zh" in self.model_name.lower()
            or "chinese" in self.model_name.lower()
        )
        
        # Deep mode: use pre-computed embeddings for full semantic search
        if self.deep_mode and self.reranker and self.doc_embeddings is not None:
            return self._search_deep(query, top_k, bm25_weight, is_multilingual_model, fusion_method)
        
        # Fast mode: BM25 filtering + semantic reranking
        # Stage 1: BM25 retrieval
        candidates = self.bm25.search(query, top_k=bm25_candidates)
        
        # If BM25 finds nothing and using multilingual model, do pure semantic search
        # This enables cross-lingual search (e.g., Chinese query → English docs)
        # Only for multilingual model - English models would give garbage results
        if not candidates and self.reranker and is_multilingual_model:
            # Use all documents as candidates for semantic search
            all_candidates = [(doc, 0.0) for doc in self.documents]
            # Sample if too many (for performance)
            if len(all_candidates) > 100:
                import random
                all_candidates = random.sample(all_candidates, 100)
            candidates = all_candidates
            bm25_weight = 0.0  # Pure semantic search
            is_cross_lingual = True
        
        if not candidates:
            return [], False
        
        # Stage 2: Semantic reranking (if model available)
        if self.reranker:
            results = self.reranker.rerank(query, candidates, top_k=top_k, 
                                           bm25_weight=bm25_weight, fusion_method=fusion_method)
        else:
            # BM25 only mode - just take top_k from BM25 results
            results = candidates[:top_k]
        
        # Format output
        output = []
        for doc, score in results:
            # Extract a relevant snippet
            snippet = self._extract_snippet(doc.text, query)
            score_val = None if score is None else round(score, 3)
            output.append({
                'pdf_name': doc.pdf_name,
                'page_num': doc.page_num,
                'chunk_id': doc.chunk_id,
                'score': score_val,
                'snippet': snippet
            })
        
        return output, is_cross_lingual
    
    def _search_deep(self, query: str, top_k: int, bm25_weight: float, 
                     is_multilingual: bool, fusion_method: str = "rrf") -> tuple[list[dict], bool]:
        """Deep search using pre-computed embeddings."""
        is_cross_lingual = False
        
        # Get BM25 scores for all documents
        query_tokens = tokenize(query)
        bm25_scores = np.array(self.bm25.bm25.get_scores(query_tokens))
        
        # Check if BM25 found anything (for cross-lingual detection)
        if bm25_scores.max() == 0 and is_multilingual:
            is_cross_lingual = True
            bm25_weight = 0.0
        
        bm25_scores = bm25_scores.astype(float)
        
        # Compute semantic scores using pre-computed embeddings
        query_embedding = self.reranker.encode_single(query, is_query=True)
        semantic_scores = cosine_similarity(query_embedding, self.doc_embeddings).astype(float)

        if fusion_method == "rrf":
            k = 60.0
            sem_rank = np.argsort(semantic_scores)[::-1]
            bm_rank = np.argsort(bm25_scores)[::-1]
            sem_pos = np.empty_like(sem_rank)
            bm_pos = np.empty_like(bm_rank)
            sem_pos[sem_rank] = np.arange(1, len(sem_rank) + 1)
            bm_pos[bm_rank] = np.arange(1, len(bm_rank) + 1)
            combined_scores = (1.0 / (k + sem_pos)) + (1.0 / (k + bm_pos))
        else:
            bm25_scores = _percentile_normalize(bm25_scores)
            semantic_scores = _percentile_normalize(semantic_scores)
            combined_scores = (1 - bm25_weight) * semantic_scores + bm25_weight * bm25_scores
        
        # Get top results
        top_indices = np.argsort(combined_scores)[::-1][:top_k]
        
        # Format output
        output = []
        for idx in top_indices:
            doc = self.documents[idx]
            snippet = self._extract_snippet(doc.text, query)
            score = None if fusion_method == "rrf" else round(float(combined_scores[idx]), 3)
            output.append({
                'pdf_name': doc.pdf_name,
                'page_num': doc.page_num,
                'chunk_id': doc.chunk_id,
                'score': score,
                'snippet': snippet
            })
        
        return output, is_cross_lingual
    
    def _extract_snippet(self, text: str, query: str, max_len: int = 200) -> str:
        """Extract a relevant snippet from the page text."""
        # Try to find query terms in text
        query_terms = tokenize(query)
        text_lower = text.lower()
        
        best_pos = 0
        for term in query_terms:
            pos = text_lower.find(term)
            if pos != -1:
                best_pos = pos
                break
        
        # Extract snippet around best position
        start = max(0, best_pos - 50)
        end = min(len(text), start + max_len)
        
        snippet = text[start:end].strip()
        snippet = ' '.join(snippet.split())  # Normalize whitespace
        
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
            
        return snippet
    
    def search_formatted(self, query: str, **kwargs) -> str:
        """Search and return formatted string output."""
        results, _ = self.search(query, **kwargs)
        
        if not results:
            return f"No results found for: {query}"
        
        lines = [f"Results for: \"{query}\"\n"]
        lines.append("-" * 50)
        
        for i, r in enumerate(results, 1):
            chunk_info = f", Chunk {r['chunk_id']}" if r.get("chunk_id") else ""
            score_info = f" (score: {r['score']})" if r.get("score") is not None else ""
            lines.append(f"\n{i}. {r['pdf_name']} - Page {r['page_num']}{chunk_info}{score_info}")
            lines.append(f"   {r['snippet']}")
        
        return '\n'.join(lines)


# ============================================================
# CLI Interface
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Semantic Page Locator for Course PDFs")
    parser.add_argument('pdf_dir', help="Directory containing PDF files")
    parser.add_argument('--query', '-q', help="Search query")
    parser.add_argument('--rebuild', action='store_true', help="Force rebuild index")
    parser.add_argument('--top-k', type=int, default=5, help="Number of results")
    parser.add_argument('--interactive', '-i', action='store_true', help="Interactive mode")
    parser.add_argument('--deep', '-d', action='store_true', help="Use deep indexing mode")
    parser.add_argument('--model', '-m', default="BAAI/bge-small-en-v1.5",
                        help="Model to use")
    
    args = parser.parse_args()
    
    # Initialize locator
    locator = HybridLocator(args.pdf_dir, model_name=args.model)
    ocr_mode = "deep" if args.deep else "fast"
    locator.build_index(force_rebuild=args.rebuild, ocr_mode=ocr_mode)
    
    if args.deep:
        locator.precompute_embeddings()
    
    if args.interactive:
        print("\nInteractive mode. Type 'quit' to exit.\n")
        while True:
            query = input("Query: ").strip()
            if query.lower() in ('quit', 'exit', 'q'):
                break
            if query:
                print(locator.search_formatted(query, top_k=args.top_k))
                print()
    elif args.query:
        print(locator.search_formatted(args.query, top_k=args.top_k))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
