"""
Recursive / character text splitting for RAG chunking.

Adapted from LangChain's text splitter logic (MIT license) to avoid a heavy
langchain / numpy<2 dependency chain on Python 3.13+.
"""

from __future__ import annotations

import logging
import re
from typing import Callable, Iterable, List, Optional

logger = logging.getLogger(__name__)


def _split_text_with_regex(
    text: str, separator: str, keep_separator: bool
) -> List[str]:
    if separator:
        if keep_separator:
            _splits = re.split(f"({separator})", text)
            splits = [_splits[i] + _splits[i + 1] for i in range(1, len(_splits), 2)]
            if len(_splits) % 2 == 0:
                splits += _splits[-1:]
            splits = [_splits[0]] + splits
        else:
            splits = re.split(separator, text)
    else:
        splits = list(text)
    return [s for s in splits if s != ""]


class _BaseTextSplitter:
    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        length_function: Callable[[str], int] = len,
        keep_separator: bool = False,
        strip_whitespace: bool = True,
    ) -> None:
        if chunk_overlap > chunk_size:
            raise ValueError(
                f"chunk overlap ({chunk_overlap}) exceeds chunk size ({chunk_size})"
            )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._length_function = length_function
        self._keep_separator = keep_separator
        self._strip_whitespace = strip_whitespace

    def _join_docs(self, docs: List[str], separator: str) -> Optional[str]:
        text = separator.join(docs)
        if self._strip_whitespace:
            text = text.strip()
        return None if text == "" else text

    def _merge_splits(self, splits: Iterable[str], separator: str) -> List[str]:
        separator_len = self._length_function(separator)
        docs: List[str] = []
        current_doc: List[str] = []
        total = 0
        for d in splits:
            _len = self._length_function(d)
            if (
                total + _len + (separator_len if len(current_doc) > 0 else 0)
                > self._chunk_size
            ):
                if total > self._chunk_size:
                    logger.warning(
                        "Created chunk of size %s, longer than chunk_size %s",
                        total,
                        self._chunk_size,
                    )
                if len(current_doc) > 0:
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)
                    while total > self._chunk_overlap or (
                        total + _len + (separator_len if len(current_doc) > 0 else 0)
                        > self._chunk_size
                        and total > 0
                    ):
                        total -= self._length_function(current_doc[0]) + (
                            separator_len if len(current_doc) > 1 else 0
                        )
                        current_doc = current_doc[1:]
            current_doc.append(d)
            total += _len + (separator_len if len(current_doc) > 1 else 0)
        doc = self._join_docs(current_doc, separator)
        if doc is not None:
            docs.append(doc)
        return docs


class RecursiveCharacterTextSplitter(_BaseTextSplitter):
    """Split text by recursively trying separators (paragraphs, lines, words)."""

    def __init__(
        self,
        separators: Optional[List[str]] = None,
        keep_separator: bool = True,
        is_separator_regex: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(keep_separator=keep_separator, **kwargs)
        self._separators = separators or ["\n\n", "\n", " ", ""]
        self._is_separator_regex = is_separator_regex

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators: List[str] = []
        for i, _s in enumerate(separators):
            _sep = _s if self._is_separator_regex else re.escape(_s)
            if _s == "":
                separator = _s
                break
            if re.search(_sep, text):
                separator = _s
                new_separators = separators[i + 1 :]
                break

        _sep = separator if self._is_separator_regex else re.escape(separator)
        splits = _split_text_with_regex(text, _sep, self._keep_separator)

        _separator = "" if self._keep_separator else separator
        _good_splits: List[str] = []
        for s in splits:
            if self._length_function(s) < self._chunk_size:
                _good_splits.append(s)
            else:
                if _good_splits:
                    merged_text = self._merge_splits(_good_splits, _separator)
                    final_chunks.extend(merged_text)
                    _good_splits = []
                if not new_separators:
                    final_chunks.append(s)
                else:
                    final_chunks.extend(self._split_text(s, new_separators))
        if _good_splits:
            merged_text = self._merge_splits(_good_splits, _separator)
            final_chunks.extend(merged_text)
        return final_chunks

    def split_text(self, text: str) -> List[str]:
        return self._split_text(text, self._separators)


class CharacterTextSplitter(_BaseTextSplitter):
    """Split on a fixed separator then merge into chunk_size segments."""

    def __init__(
        self,
        separator: str = "\n\n",
        is_separator_regex: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._separator = separator
        self._is_separator_regex = is_separator_regex

    def split_text(self, text: str) -> List[str]:
        separator = (
            self._separator if self._is_separator_regex else re.escape(self._separator)
        )
        splits = _split_text_with_regex(text, separator, self._keep_separator)
        _separator = "" if self._keep_separator else self._separator
        return self._merge_splits(splits, _separator)
