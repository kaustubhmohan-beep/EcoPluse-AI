"""
EcoPulse AI - RAG Knowledge Indexer & Hybrid Retriever
Indexes domain literature from energy.txt and JETIR1405001.pdf into
granular semantic chunks with TF-IDF vectorization and BM25-style keyword matching.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
import pypdf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger("ecopulse.rag_indexer")
logging.basicConfig(level=logging.INFO)

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(WORKSPACE_ROOT, "data")
INDEX_PATH = os.path.join(DATA_DIR, "rag_index.json")

class RAGIndexer:
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self._build_or_load_index()

    def _extract_energy_txt(self) -> List[Dict[str, Any]]:
        """Extracts and chunks energy conservation rules from energy.txt."""
        txt_path = os.path.join(WORKSPACE_ROOT, "energy.txt")
        if not os.path.exists(txt_path):
            logger.warning("energy.txt not found!")
            return []

        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split into logical sections
        raw_sections = re.split(r'\n(?=[A-Z][A-Za-z &]+(?:\n|$))', content)
        chunks = []
        
        for idx, sec in enumerate(raw_sections):
            sec_clean = sec.strip()
            if not sec_clean:
                continue
            
            lines = [l.strip() for l in sec_clean.split("\n") if l.strip()]
            if not lines:
                continue
            
            title = lines[0]
            body_lines = lines[1:] if len(lines) > 1 else lines
            
            # Categorize
            title_lower = title.lower()
            category = "general"
            if any(k in title_lower for k in ["light", "bulb", "cfl", "tube"]):
                category = "lighting"
            elif any(k in title_lower for k in ["air conditioner", "ac", "fan", "thermostat"]):
                category = "hvac"
            elif any(k in title_lower for k in ["refrigerator", "fridge", "freezer"]):
                category = "refrigeration"
            elif any(k in title_lower for k in ["water heater", "geyser", "boiler"]):
                category = "water_heater"
            elif any(k in title_lower for k in ["microwave", "kettle", "cooking"]):
                category = "appliances"
            elif any(k in title_lower for k in ["computer", "office", "monitor", "charger", "standby"]):
                category = "standby"

            # Create granular sub-chunks per paragraph/rule
            paragraphs = re.split(r'\n\s*\n', "\n".join(body_lines))
            for p_idx, p in enumerate(paragraphs):
                p_text = p.strip()
                if not p_text:
                    continue
                chunks.append({
                    "id": f"energy_txt_{idx+1}_{p_idx+1}",
                    "source": "energy.txt",
                    "title": title,
                    "category": category,
                    "content": p_text,
                    "reference": f"energy.txt - Section: {title}"
                })
        return chunks

    def _extract_jetir_pdf(self) -> List[Dict[str, Any]]:
        """Extracts and chunks technical circuit and energy theory from JETIR1405001.pdf."""
        pdf_path = os.path.join(WORKSPACE_ROOT, "JETIR1405001.pdf")
        if not os.path.exists(pdf_path):
            logger.warning("JETIR1405001.pdf not found!")
            return []

        reader = pypdf.PdfReader(pdf_path)
        chunks = []

        # Key technical topics mapped to pages
        page_topics = {
            1: ("Abstract & Energy Crisis", "general"),
            2: ("Energy Losses & Transmission Inefficiency", "theory"),
            3: ("Per Capita Consumption Trends & Historical Dynamics", "theory"),
            4: ("Passive Solar Design & Efficiency Legislation", "hvac"),
            5: ("Automated Sensor Sensing & Behavioral Metering", "circuit_design"),
            6: ("Time Delay Circuit & 555 Monostable Multivibrator", "circuit_design"),
            7: ("LDR Light Dependent Switch & RC Timing Formula tp=1.1*R*C", "circuit_design"),
            8: ("LM35 Temperature Switch & Automated Fan Relay Circuit", "circuit_design")
        }

        for i, page in enumerate(reader.pages):
            page_num = i + 1
            raw_text = page.extract_text() or ""
            # Clean headers/footers
            cleaned = re.sub(r'Volume \d+ Issue \d+\s+JETIR.*?\d+', '', raw_text)
            cleaned = re.sub(r'JETIR\d+\s+Journal of Emerging Technologies.*?\d+', '', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            title, cat = page_topics.get(page_num, (f"Section Page {page_num}", "theory"))
            
            # Split page into 2-3 focused chunks if long
            sentences = cleaned.split(". ")
            chunk_size = 5
            for c_idx in range(0, len(sentences), chunk_size):
                sub_text = ". ".join(sentences[c_idx:c_idx+chunk_size]).strip()
                if len(sub_text) > 80:
                    chunks.append({
                        "id": f"jetir_p{page_num}_c{c_idx//chunk_size + 1}",
                        "source": "JETIR1405001.pdf",
                        "title": f"JETIR Research - {title}",
                        "category": cat,
                        "content": sub_text,
                        "reference": f"JETIR1405001 (Maheshwari, 2014) - Page {page_num}"
                    })
        return chunks

    def _build_or_load_index(self):
        """Loads cached chunks if available, or extracts documents and compiles TF-IDF vocabulary matrix."""
        os.makedirs(DATA_DIR, exist_ok=True)
        
        if os.path.exists(INDEX_PATH):
            try:
                with open(INDEX_PATH, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
                logger.info(f"Loaded {len(self.chunks)} knowledge chunks from cache.")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}, re-extracting...")
                self.chunks = []

        if not self.chunks:
            energy_chunks = self._extract_energy_txt()
            jetir_chunks = self._extract_jetir_pdf()
            self.chunks = energy_chunks + jetir_chunks
            
            logger.info(f"Extracted {len(self.chunks)} total knowledge chunks ({len(energy_chunks)} from energy.txt, {len(jetir_chunks)} from JETIR PDF).")

            with open(INDEX_PATH, "w", encoding="utf-8") as f:
                json.dump(self.chunks, f, indent=2)

        # Build TF-IDF vectorizer (unigrams + bigrams)
        corpus = [f"{c['title']} {c['category']} {c['content']}" for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        logger.info("TF-IDF Vector Index built successfully.")

    def search(self, query: str, category: Optional[str] = None, top_k: int = 4, min_similarity: float = 0.75) -> List[Dict[str, Any]]:
        """
        Hybrid semantic & keyword search over indexed knowledge chunks.
        Returns only matches above a strict cosine-similarity confidence threshold.
        """
        if not self.chunks or self.vectorizer is None or self.tfidf_matrix is None:
            return []

        stop_words = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at",
            "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "can't", "cannot",
            "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each",
            "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd",
            "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd",
            "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
            "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
            "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
            "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
            "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through",
            "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
            "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom",
            "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your",
            "yours", "yourself", "yourselves", "used", "using", "use", "make", "get", "give", "tell", "show", "know"
        }

        query_vec = self.vectorizer.transform([query])
        sim_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        query_terms = set(w for w in re.findall(r'\w+', query.lower()) if w not in stop_words and len(w) > 2)

        boosted_scores = np.copy(sim_scores)

        for idx, chunk in enumerate(self.chunks):
            if sim_scores[idx] > 0.01:
                if category and category.lower() not in ["all", "general", ""]:
                    if chunk["category"] == category.lower():
                        boosted_scores[idx] += 0.15

                if query_terms:
                    chunk_lower = chunk["content"].lower()
                    matched_terms = sum(1 for t in query_terms if t in chunk_lower)
                    if matched_terms > 0:
                        boosted_scores[idx] += (matched_terms * 0.05)

        top_indices = np.argsort(boosted_scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            cosine_score = float(sim_scores[idx])
            if cosine_score < min_similarity:
                continue
            item = dict(self.chunks[idx])
            item["score"] = round(cosine_score, 4)
            item["confidence_score"] = round(float(boosted_scores[idx]), 4)
            results.append(item)
        return results

# Global singleton instance
rag_indexer = RAGIndexer()
