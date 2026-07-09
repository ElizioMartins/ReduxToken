"""Example: reversible compression round-trip with ReduxToken."""

def main() -> None:
    try:
        from redux_token import compress, decompress  # type: ignore
    except Exception:
        try:
            from redux_token.core import compress, decompress  # type: ignore
        except Exception as e:
            print("Install package first:", e)
            return

    original = {"user": {"id": 1, "name": "tap"}, "items": list(range(20))}
    token = compress(original)
    restored = decompress(token)
    print("round-trip ok:", restored == original)
    print("token preview:", str(token)[:120])


if __name__ == "__main__":
    main()
