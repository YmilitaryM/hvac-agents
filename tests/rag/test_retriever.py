import pytest
from src.rag.loader import chunk_text, load_text_document, DocumentChunk
from src.rag.retriever import DocumentStore, create_hvac_knowledge_base, RetrievalResult


class TestChunking:
    def test_empty_text(self):
        chunks = chunk_text("", source="test")
        assert len(chunks) == 0

    def test_short_text_single_chunk(self):
        chunks = chunk_text("Short text.", source="test", chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0].source == "test"

    def test_long_text_multiple_chunks(self):
        text = "A. " + "B. " * 300  # ~900 chars
        chunks = chunk_text(text, source="test", chunk_size=100, chunk_overlap=0)
        assert len(chunks) > 1

    def test_chunk_metadata(self):
        chunks = chunk_text("Hello world.", source="ashrae_90.1", section="6.4")
        assert chunks[0].source == "ashrae_90.1"
        assert chunks[0].section == "6.4"
        assert chunks[0].chunk_id == "ashrae_90.1_chunk_0000"
        assert chunks[0].chunk_index == 0


class TestDocumentStore:
    @pytest.fixture
    def store(self):
        s = DocumentStore()
        chunks = chunk_text(
            "Centrifugal chiller surge occurs at low load with high condensing pressure. "
            "The minimum PLR increases as condenser water temperature rises. "
            "ASHRAE 90.1 requires minimum COP of 5.0 for centrifugal chillers. "
            "Cooling tower approach should be 3-5°C under design conditions.",
            source="hvac_guide",
            chunk_size=200,
            chunk_overlap=0,
        )
        s.add_chunks(chunks)
        return s

    def test_search_returns_results(self, store):
        results = store.search("chiller surge", top_k=3)
        assert len(results) > 0

    def test_search_scores_are_sorted(self, store):
        results = store.search("chiller COP", top_k=3)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_empty_query(self, store):
        results = store.search("", top_k=5)
        # Empty query should either return empty or handle gracefully
        assert isinstance(results, list)

    def test_clear_store(self, store):
        store.clear()
        assert len(store) == 0
        assert store.search("test") == []


class TestHVACKnowledgeBase:
    @pytest.fixture
    def kb(self):
        return create_hvac_knowledge_base()

    def test_kb_has_chunks(self, kb):
        assert len(kb) > 0

    def test_surge_query(self, kb):
        results = kb.search("centrifugal chiller surge prevention", top_k=3)
        assert len(results) > 0
        # Top result should be about surge
        assert any("surge" in r.chunk.text.lower() for r in results)

    def test_ashrae_query(self, kb):
        results = kb.search("ASHRAE standard COP requirements", top_k=3)
        assert len(results) > 0

    def test_pump_laws_query(self, kb):
        results = kb.search("pump affinity laws speed power", top_k=3)
        assert len(results) > 0

    def test_safety_interlock_query(self, kb):
        results = kb.search("chiller safety interlock sequence", top_k=3)
        assert len(results) > 0
