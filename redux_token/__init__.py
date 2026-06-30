from __future__ import annotations

from typing import Callable

from redux_token_core import PyCompressor, CompressionStats

FilterFn = Callable[[str], str]


class ReduxToken:
    """Compressor de tokens para LLMs.

    Aplica a cadeia de filtros Rust por padrão. Filtros Python adicionais
    podem ser passados via ``extra_filters`` e rodam em sequência após o core Rust.

    Exemplo com filtro customizado::

        def remove_urls(text: str) -> str:
            import re
            return re.sub(r'https?://\\S+', '', text)

        rt = ReduxToken(extra_filters=[remove_urls])
        compressed, stats = rt.compress(text)
    """

    def __init__(self, extra_filters: list[FilterFn] | None = None) -> None:
        self._compressor = PyCompressor()
        self._extra: list[FilterFn] = extra_filters or []

    def compress(self, text: str) -> tuple[str, CompressionStats]:
        result, stats = self._compressor.compress(text)
        for fn in self._extra:
            result = fn(result)
        return result, stats

    def add_filter(self, fn: FilterFn) -> None:
        """Adiciona um filtro Python ao final da cadeia."""
        self._extra.append(fn)


__all__ = ["ReduxToken", "CompressionStats", "FilterFn"]
