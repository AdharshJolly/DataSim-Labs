"""Shared dataframe and chunking helpers for generation flows."""

from __future__ import annotations


def iter_chunks(row_count: int, chunk_size: int) -> list[int]:
    """Return chunk sizes that sum exactly to row_count."""
    full_chunks, remainder = divmod(row_count, chunk_size)
    chunks = [chunk_size] * full_chunks
    if remainder:
        chunks.append(remainder)
    return chunks or [row_count]


def effective_chunk_size(
    *,
    base_chunk_size: int,
    attribute_count: int,
    row_count: int,
    min_chunk_size: int,
    target_cells_per_chunk: int,
) -> int:
    """Compute adaptive chunk size to reduce peak memory pressure."""
    by_cells = max(1, target_cells_per_chunk // max(1, attribute_count))
    bounded = min(base_chunk_size, by_cells)
    bounded = max(min_chunk_size, bounded)
    return max(1, min(bounded, row_count))
