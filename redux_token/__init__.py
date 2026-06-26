from redux_token_core import PyCompressor, CompressionStats


class ReduxToken:
    def __init__(self) -> None:
        self._compressor = PyCompressor()

    def compress(self, text: str) -> tuple[str, CompressionStats]:
        return self._compressor.compress(text)


__all__ = ["ReduxToken", "CompressionStats"]
