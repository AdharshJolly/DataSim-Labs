"""Chunk planning utilities for large dataset generation."""

from __future__ import annotations

from app.utils.dataframe_utils import effective_chunk_size, iter_chunks


class ChunkProcessor:
    """Computes chunk sizes and iterates over chunk windows."""

    @staticmethod
    def resolve_chunk_size(
        base_chunk_size: int,
        attribute_count: int,
        row_count: int,
        min_chunk_size: int,
        target_cells_per_chunk: int,
    ) -> int:
        return effective_chunk_size(
            base_chunk_size=base_chunk_size,
            attribute_count=attribute_count,
            row_count=row_count,
            min_chunk_size=min_chunk_size,
            target_cells_per_chunk=target_cells_per_chunk,
        )

    @staticmethod
    def iterate_chunks(row_count: int, chunk_size: int) -> list[int]:
        return iter_chunks(row_count=row_count, chunk_size=chunk_size)
