"""
Hybrid Semantic Page Locator for Course PDFs
BM25 keyword search + Sentence Transformer reranking
"""

import os
import json
import pickle
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, util
import re


@dataclass
class PageDocument:
    """Represents a single page from a PDF."""
    pdf_name: str
    page_num: int  # 1-indexed for user display
    text: str
    tokens: list = field(default_factory=list)
    
    def __post_init__(self):
        if not self.tokens:
            self.tokens = tokenize(self.text)
    
    @property
    def doc_id(self) -> str:
        return f"{self.pdf_name}::page_{self.page_num}"


def tokenize(text: str) -> list[str]:
    """Simple tokenization: lowercase, split on non-alphanumeric."""
    text = text.lower()
    tokens = re.findall(r'\b[a-z0-9]+\b', text)
    # Remove very short tokens and stopwords
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
    return [t for t in tokens if len(t) > 1 and t not in stopwords]


class PDFIndexer:
    """Extracts and indexes text from PDFs."""
    
    def __init__(self, pdf_dir: str):
        self.pdf_dir = Path(pdf_dir)
        self.documents: list[PageDocument] = []
        
    def extract_all(self) -> list[PageDocument]:
        """Extract text from all PDFs in directory."""
        self.documents = []
        
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files")
        
        for pdf_path in pdf_files:
            print(f"  Processing: {pdf_path.name}")
            self._extract_pdf(pdf_path)
        
        print(f"Total pages indexed: {len(self.documents)}")
        return self.documents
    
    def _extract_pdf(self, pdf_path: Path):
        """Extract text from a single PDF."""
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Skip nearly empty pages
                if len(text.strip()) < 50:
                    continue
                
                self.documents.append(PageDocument(
                    pdf_name=pdf_path.name,
                    page_num=page_num + 1,  # 1-indexed
                    text=text
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


class SemanticReranker:
    """Sentence transformer-based semantic reranking."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        print(f"Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
    
    def rerank(self, query: str, candidates: list[tuple[PageDocument, float]], 
               top_k: int = 5, bm25_weight: float = 0.3) -> list[tuple[PageDocument, float]]:
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
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        
        # Encode all candidate texts (truncate long pages)
        texts = [doc.text[:2000] for doc, _ in candidates]  # Truncate for efficiency
        doc_embeddings = self.model.encode(texts, convert_to_tensor=True)
        
        # Compute semantic similarities
        semantic_scores = util.cos_sim(query_embedding, doc_embeddings)[0].cpu().numpy()
        
        # Normalize BM25 scores
        bm25_scores = np.array([score for _, score in candidates])
        if bm25_scores.max() > 0:
            bm25_scores = bm25_scores / bm25_scores.max()
        
        # Combine scores
        combined_scores = (1 - bm25_weight) * semantic_scores + bm25_weight * bm25_scores
        
        # Sort by combined score
        sorted_indices = np.argsort(combined_scores)[::-1][:top_k]
        
        results = []
        for idx in sorted_indices:
            doc, _ = candidates[idx]
            results.append((doc, float(combined_scores[idx])))
        
        return results


class HybridLocator:
    """Main interface combining BM25 + semantic reranking."""
    
    def __init__(self, pdf_dir: str, model_name: Optional[str] = "sentence-transformers/all-MiniLM-L6-v2"):
        self.pdf_dir = Path(pdf_dir)
        self.model_name = model_name
        self.indexer: Optional[PDFIndexer] = None
        self.bm25: Optional[BM25Retriever] = None
        self.reranker: Optional[SemanticReranker] = None
        self.documents: list[PageDocument] = []
        
    def build_index(self, force_rebuild: bool = False):
        """Build or load the search index."""
        cache_path = self.pdf_dir / ".locator_cache.pkl"
        
        # Try to load from cache
        if not force_rebuild and cache_path.exists():
            print("Loading index from cache...")
            with open(cache_path, 'rb') as f:
                self.documents = pickle.load(f)
            print(f"Loaded {len(self.documents)} pages from cache")
        else:
            # Build fresh index
            print("Building index from PDFs...")
            self.indexer = PDFIndexer(self.pdf_dir)
            self.documents = self.indexer.extract_all()
            
            # Cache for next time
            with open(cache_path, 'wb') as f:
                pickle.dump(self.documents, f)
            print("Index cached for future use")
        
        # Initialize retrievers
        self.bm25 = BM25Retriever(self.documents)
        
        # Only load semantic model if specified
        if self.model_name:
            self.reranker = SemanticReranker(self.model_name)
        else:
            self.reranker = None
            print("Running in keywords-only mode (no semantic reranking)")
        
    def search(self, query: str, top_k: int = 5, bm25_candidates: int = 20,
               bm25_weight: float = 0.3) -> list[dict]:
        """
        Search for pages relevant to the query.
        
        Args:
            query: Natural language question
            top_k: Number of results to return
            bm25_candidates: Number of candidates from BM25 stage
            bm25_weight: Weight for BM25 in final score (0-1)
            
        Returns:
            List of dicts with pdf_name, page_num, score, snippet
        """
        if self.bm25 is None:
            raise RuntimeError("Index not built. Call build_index() first.")
        
        # Stage 1: BM25 retrieval
        candidates = self.bm25.search(query, top_k=bm25_candidates)
        
        if not candidates:
            return []
        
        # Stage 2: Semantic reranking (if model available)
        if self.reranker:
            results = self.reranker.rerank(query, candidates, top_k=top_k, 
                                           bm25_weight=bm25_weight)
        else:
            # BM25 only mode - just take top_k from BM25 results
            results = candidates[:top_k]
        
        # Format output
        output = []
        for doc, score in results:
            # Extract a relevant snippet
            snippet = self._extract_snippet(doc.text, query)
            output.append({
                'pdf_name': doc.pdf_name,
                'page_num': doc.page_num,
                'score': round(score, 3),
                'snippet': snippet
            })
        
        return output
    
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
        results = self.search(query, **kwargs)
        
        if not results:
            return f"No results found for: {query}"
        
        lines = [f"Results for: \"{query}\"\n"]
        lines.append("-" * 50)
        
        for i, r in enumerate(results, 1):
            lines.append(f"\n{i}. {r['pdf_name']} - Page {r['page_num']} (score: {r['score']})")
            lines.append(f"   {r['snippet']}")
        
        return '\n'.join(lines)


# ============================================================
# Training utilities for fine-tuning the reranker
# ============================================================

class TrainingDataGenerator:
    """Generate training pairs from annotated data."""
    
    @staticmethod
    def from_json(json_path: str) -> list[dict]:
        """
        Load training data from JSON file.
        
        Expected format:
        [
            {"question": "What is the Bellman equation?", 
             "pdf": "RL_lecture.pdf", 
             "pages": [49, 50]},
            ...
        ]
        """
        with open(json_path, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def create_template(output_path: str, num_examples: int = 50):
        """Create a template JSON file for annotation."""
        template = [
            {
                "question": "Example: What is Q-learning?",
                "pdf": "lecture_notes.pdf",
                "pages": [42, 43],
                "notes": "Optional notes about this example"
            }
        ]
        
        with open(output_path, 'w') as f:
            json.dump(template, f, indent=2)
        
        print(f"Template created at: {output_path}")
        print("Edit this file to add your question→page annotations.")


def fine_tune_reranker(locator: HybridLocator, training_data: list[dict],
                       output_dir: str, epochs: int = 3):
    """
    Fine-tune the reranker on your question→page pairs.
    
    This creates training triplets: (query, positive_page, negative_page)
    """
    from sentence_transformers import InputExample, losses
    from torch.utils.data import DataLoader
    
    # Build document lookup
    doc_lookup = {}
    for doc in locator.documents:
        key = (doc.pdf_name, doc.page_num)
        doc_lookup[key] = doc
    
    # Create training examples
    train_examples = []
    
    for item in training_data:
        question = item['question']
        pdf_name = item['pdf']
        positive_pages = item['pages']
        
        for page_num in positive_pages:
            key = (pdf_name, page_num)
            if key not in doc_lookup:
                print(f"Warning: Page not found: {pdf_name} page {page_num}")
                continue
            
            positive_doc = doc_lookup[key]
            
            # Create a training pair
            train_examples.append(InputExample(
                texts=[question, positive_doc.text[:1000]],
                label=1.0
            ))
            
            # Add negative examples (random pages from same PDF)
            for neg_doc in locator.documents:
                if neg_doc.pdf_name == pdf_name and neg_doc.page_num not in positive_pages:
                    train_examples.append(InputExample(
                        texts=[question, neg_doc.text[:1000]],
                        label=0.0
                    ))
                    break  # Just one negative per positive
    
    if not train_examples:
        print("No valid training examples found!")
        return
    
    print(f"Created {len(train_examples)} training examples")
    
    # Fine-tune
    model = locator.reranker.model
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=8)
    train_loss = losses.CosineSimilarityLoss(model)
    
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=10,
        output_path=output_dir
    )
    
    print(f"Fine-tuned model saved to: {output_dir}")


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
    parser.add_argument('--create-training-template', help="Create training data template")
    
    args = parser.parse_args()
    
    if args.create_training_template:
        TrainingDataGenerator.create_template(args.create_training_template)
        return
    
    # Initialize locator
    locator = HybridLocator(args.pdf_dir)
    locator.build_index(force_rebuild=args.rebuild)
    
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
