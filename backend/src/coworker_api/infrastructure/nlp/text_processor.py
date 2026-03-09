"""
Text Processor — Utility for text chunking and cleaning.

Used during RAG ingestion to prepare raw documents for embedding.
"""

from __future__ import annotations

import re
from typing import Optional


class TextProcessor:
    """Provides text cleaning and chunking utilities."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Remove redundant whitespace, control characters, etc."""
        # Remove control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def chunk_by_sentences(
        text: str,
        max_chunk_size: int = 512,
        overlap_sentences: int = 1,
    ) -> list[str]:
        """
        Split text into chunks at sentence boundaries.

        Args:
            text: Raw text to chunk.
            max_chunk_size: Approximate max characters per chunk.
            overlap_sentences: Number of sentences to overlap between chunks.

        Returns:
            List of text chunks.
        """
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return []

        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            if current_length + sentence_len > max_chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Keep overlap sentences
                if overlap_sentences > 0:
                    current_chunk = current_chunk[-overlap_sentences:]
                    current_length = sum(len(s) for s in current_chunk)
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(sentence)
            current_length += sentence_len

        # Add the last chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    @staticmethod
    def extract_key_phrases(text: str, max_phrases: int = 10) -> list[str]:
        """
        Simple keyword extraction via frequency analysis.

        For production, consider using spaCy or KeyBERT.
        """
        # Tokenize: split on non-alphanumeric, lowercase
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # Remove common stop words
        stop_words = {
            "the", "and", "for", "that", "this", "with", "are", "was",
            "were", "been", "have", "has", "had", "not", "but", "what",
            "all", "can", "her", "his", "from", "they", "will", "one",
            "each", "which", "their", "there", "than", "its", "also",
            "into", "more", "some", "when", "very", "just", "about",
        }
        filtered = [w for w in words if w not in stop_words]

        # Frequency count
        freq: dict[str, int] = {}
        for word in filtered:
            freq[word] = freq.get(word, 0) + 1

        # Sort by frequency, return top N
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_phrases]]
