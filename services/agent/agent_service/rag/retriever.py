"""Simple vector retriever for document chunks.

Uses sklearn's TfidfVectorizer for text vectorization and cosine similarity
for retrieval. This is a lightweight approach that works without external
services (no pgvector, no embedding API required).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .loader import DocumentChunk, chunk_text


@dataclass
class RetrievalResult:
    """A single retrieval result."""
    chunk: DocumentChunk
    score: float  # similarity score 0-1
    rank: int = 0


class DocumentStore:
    """Stores document chunks and provides TF-IDF based retrieval."""

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.vectors: Optional[np.ndarray] = None

    def add_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Add chunks to the store and re-index."""
        self.chunks.extend(chunks)
        self._reindex()

    def _reindex(self) -> None:
        """Rebuild the TF-IDF index from all chunks."""
        if not self.chunks:
            self.vectors = None
            return

        texts = [c.text for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
        )
        try:
            self.vectors = self.vectorizer.fit_transform(texts)
        except ValueError:
            # Fallback if all texts are empty
            self.vectors = None

    def search(self, query: str, top_k: int = 5, min_score: float = 0.0) -> List[RetrievalResult]:
        """Search for chunks relevant to the query.

        Args:
            query: Search query string.
            top_k: Maximum number of results to return.
            min_score: Minimum similarity score threshold (0-1).

        Returns:
            List of RetrievalResult sorted by score descending.
        """
        if not self.chunks or self.vectorizer is None or self.vectors is None:
            return []

        try:
            query_vec = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self.vectors).flatten()

            # Get top-k indices
            if len(similarities) == 0:
                return []

            top_indices = np.argsort(similarities)[::-1][:top_k]

            results = []
            for rank, idx in enumerate(top_indices):
                score = float(similarities[idx])
                if score >= min_score:
                    results.append(RetrievalResult(
                        chunk=self.chunks[idx],
                        score=score,
                        rank=rank + 1,
                    ))

            return results
        except Exception:
            return []

    def search_by_source(self, source: str, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """Search within a specific document source."""
        source_chunks = [c for c in self.chunks if c.source == source]
        if not source_chunks:
            return []

        # Temporarily create a store with only source chunks
        temp_store = DocumentStore()
        temp_store.add_chunks(source_chunks)
        return temp_store.search(query, top_k=top_k)

    def get_chunk_by_id(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Retrieve a specific chunk by ID."""
        for c in self.chunks:
            if c.chunk_id == chunk_id:
                return c
        return None

    def clear(self) -> None:
        """Clear all chunks and index."""
        self.chunks = []
        self.vectorizer = None
        self.vectors = None

    def __len__(self) -> int:
        return len(self.chunks)


def create_hvac_knowledge_base() -> DocumentStore:
    """Create a DocumentStore pre-loaded with HVAC domain knowledge snippets."""
    store = DocumentStore()

    # Standard HVAC knowledge snippets for the chiller plant domain
    knowledge_snippets = [
        (
            "Centrifugal chiller surge occurs when the compressor operates at low load "
            "with high condensing pressure. The minimum part-load ratio (PLR) increases "
            "as condenser water temperature rises. Typical surge boundary: PLR_min = "
            "0.2 + 0.015 × (T_cw - 30°C). Operation below this boundary can cause "
            "compressor damage and should be avoided.",
            "chiller_basics"
        ),
        (
            "ASHRAE Standard 90.1 requires minimum chiller COP of 5.0 for centrifugal "
            "chillers > 300 tons. Full-load COP shall be rated at ARI Standard 550/590 "
            "conditions: 7°C leaving chilled water, 30°C entering condenser water. "
            "Part-load IPLV (Integrated Part Load Value) must meet or exceed 6.0 for "
            "water-cooled centrifugal chillers.",
            "ashrae_90.1"
        ),
        (
            "GB 50189-2015 (Chinese standard for energy efficiency in public buildings) "
            "specifies that water-cooled centrifugal chillers with capacity > 1163 kW "
            "shall have COP >= 5.6 at design conditions. For variable-speed chillers, "
            "IPLV shall be >= 7.0.",
            "gb_50189"
        ),
        (
            "Cooling tower approach temperature is the difference between the leaving "
            "water temperature and the outdoor wet-bulb temperature. Typical design "
            "approach is 3-5°C. Approach increases when the tower is overloaded or "
            "fan speed is reduced. Approach > 5°C indicates potential issues: fouling, "
            "low airflow, or excessive heat load.",
            "cooling_tower"
        ),
        (
            "Chiller sequencing strategy: For multiple chillers, the most efficient "
            "operating point is typically at 60-80% PLR per chiller. Running too many "
            "chillers at low PLR increases total power due to fixed losses. Running "
            "too few chillers at high PLR reduces redundancy and may increase condenser "
            "water temperature. The optimal number of running chillers depends on total "
            "load and individual chiller efficiency curves.",
            "chiller_sequencing"
        ),
        (
            "Carbon pricing for HVAC operations: The European Union Emissions Trading "
            "System (EU ETS) carbon price typically ranges from €50-100 per ton CO2. "
            "China's national ETS carbon price ranges from ¥50-80 per ton. Grid carbon "
            "intensity varies by region: 0.4-0.6 kgCO2/kWh for coal-heavy grids, "
            "0.1-0.3 kgCO2/kWh for gas/renewable grids.",
            "carbon_accounting"
        ),
        (
            "Pump affinity laws: For variable-speed pumps, flow is proportional to "
            "speed (Q ∝ N), head is proportional to speed squared (H ∝ N²), and power "
            "is proportional to speed cubed (P ∝ N³). Reducing pump speed by 20% "
            "reduces power by approximately 49%. Minimum pump speed should be limited "
            "to prevent dead-heading and ensure minimum flow for chiller evaporators.",
            "pump_basics"
        ),
        (
            "Safety interlock requirements for chiller plants: (1) Cooling water pump "
            "must start before chiller, (2) Chilled water pump must start before chiller, "
            "(3) Minimum 30-second interval between large motor starts to limit inrush "
            "current, (4) Chiller must not restart within 15 minutes of shutdown to "
            "allow refrigerant pressure equalization, (5) Flow switches must prove flow "
            "before chiller start.",
            "safety_interlocks"
        ),
        (
            "Optimal chiller plant control: The most energy-efficient operating strategy "
            "considers (1) chiller part-load efficiency curves, (2) cooling tower fan "
            "speed vs chiller lift trade-off, (3) condenser water temperature reset "
            "based on outdoor wet-bulb, (4) variable primary flow for chilled water, "
            "(5) chiller sequencing to match load profile. System COP optimization "
            "typically saves 10-30% compared to fixed-setpoint operation.",
            "optimal_control"
        ),
        (
            "Demand response for chiller plants: During grid peak pricing events, "
            "chiller plants can reduce load by (1) pre-cooling buildings during off-peak "
            "hours (thermal energy storage), (2) raising chilled water setpoint by 1-3°C "
            "temporarily, (3) reducing chiller capacity and utilizing building thermal "
            "mass, (4) switching to on-site generation or storage if available.",
            "demand_response"
        ),
    ]

    for text, source in knowledge_snippets:
        chunks = chunk_text(text, source=source, chunk_size=1000, chunk_overlap=0)
        store.add_chunks(chunks)

    return store
