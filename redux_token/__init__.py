from __future__ import annotations

from typing import Callable

from redux_token._core import PyCompressor, CompressionStats

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

    def __init__(
        self,
        extra_filters: list[FilterFn] | None = None,
        source: str = "lib",
        reversible: bool = False,
    ) -> None:
        self._compressor = PyCompressor()
        self._extra: list[FilterFn] = extra_filters or []
        self._source = source
        self._reversible = reversible

    def compress(self, text: str) -> tuple[str, CompressionStats]:
        if self._reversible:
            # CCR: o core troca cada trecho removido por um marcador ⟦rdx:ref⟧ e
            # devolve os pares (ref, original) para guardarmos no store local.
            result, stats, spans = self._compressor.compress_reversible(text)
            for fn in self._extra:
                result = fn(result)
            try:
                from redux_token import reversible as _rev

                for _ref, span in spans:
                    _rev.put(span)
            except Exception:
                pass
        else:
            result, stats = self._compressor.compress(text)
            for fn in self._extra:
                result = fn(result)
        try:
            from redux_token import telemetry

            telemetry.record(self._source, stats, text)
        except Exception:
            pass
        return result, stats

    def add_filter(self, fn: FilterFn) -> None:
        """Adiciona um filtro Python ao final da cadeia."""
        self._extra.append(fn)


__all__ = ["ReduxToken", "CompressionStats", "FilterFn"]
