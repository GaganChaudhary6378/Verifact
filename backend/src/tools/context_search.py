"""Context search tool - grep-like search and windowing over large text."""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SearchMatch:
    """A single match with surrounding context."""

    match_text: str
    start: int
    end: int
    context_before: str
    context_after: str
    full_snippet: str


class ContextSearchTool:
    """
    Search and window over large text context (e.g. webpage full_text).
    Simulates grep-like capabilities for the LLM to pull relevant snippets.
    """

    def __init__(self, full_text: str) -> None:
        """
        Initialize with the document to search.

        Args:
            full_text: The full document text (e.g. from source_context).
        """
        self.full_text = full_text or ""
        self._normalized: Optional[str] = None

    def _normalize(self, text: str) -> str:
        """Normalize whitespace for fuzzy matching."""
        return " ".join(text.split())

    def search(
        self,
        pattern: str,
        window_size: int = 200,
        max_results: int = 10,
        case_sensitive: bool = False,
    ) -> List[SearchMatch]:
        """
        Regex or literal keyword search with context windows.

        Args:
            pattern: Regex pattern or literal string to search for.
            window_size: Characters of context to include before/after each match.
            max_results: Maximum number of matches to return.
            case_sensitive: Whether to match case.

        Returns:
            List of SearchMatch with snippet and context.
        """
        if not self.full_text:
            return []

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            regex = re.compile(re.escape(pattern), flags)

        matches: List[SearchMatch] = []
        for m in regex.finditer(self.full_text):
            if len(matches) >= max_results:
                break
            start = m.start()
            end = m.end()
            ctx_before = self.full_text[max(0, start - window_size) : start]
            ctx_after = self.full_text[end : min(len(self.full_text), end + window_size)]
            full_snippet = ctx_before + m.group() + ctx_after
            matches.append(
                SearchMatch(
                    match_text=m.group(),
                    start=start,
                    end=end,
                    context_before=ctx_before.strip(),
                    context_after=ctx_after.strip(),
                    full_snippet=full_snippet.strip(),
                )
            )
        return matches

    def get_window(
        self,
        anchor: str,
        size: int = 500,
        case_sensitive: bool = False,
    ) -> Optional[str]:
        """
        Retrieve text around a specific phrase (anchor).

        Args:
            anchor: Phrase or word to center the window on.
            size: Total characters to return (half before, half after anchor).
            case_sensitive: Whether anchor search is case sensitive.

        Returns:
            Window of text around the first occurrence of anchor, or None if not found.
        """
        if not self.full_text or not anchor:
            return None

        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.escape(anchor)
        m = re.search(pattern, self.full_text, flags)
        if not m:
            return None
        center = (m.start() + m.end()) // 2
        half = size // 2
        start = max(0, center - half)
        end = min(len(self.full_text), center + half)
        return self.full_text[start:end]

    def summarize_section(self, section_text: str, max_length: int = 300) -> str:
        """
        Truncate/summarize a section to a max length (simple trim at sentence boundary).

        Args:
            section_text: Text to summarize.
            max_length: Maximum character length.

        Returns:
            Truncated text, ideally at a sentence end.
        """
        if not section_text or len(section_text) <= max_length:
            return section_text or ""
        truncated = section_text[: max_length + 1]
        last_period = truncated.rfind(". ")
        if last_period > max_length // 2:
            return truncated[: last_period + 1].strip()
        return truncated.strip() + "..."
