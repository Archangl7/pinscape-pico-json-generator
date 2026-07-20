from pathlib import Path

from pinscape_parser import PinscapeParseError, loads


def run() -> None:
    sample = """
    // Pinscape-style syntax
    {
      id: { unitNum: 1, unitName: 'Main Pico', },
      keyboard: { enable: true },
      buttons: [{ source: { type: 'gpio', gp: 7 }, shiftBits: 0x0001, action: { type: 'key', key: 'left alt' } }],
      value: null,
    }
    """
    parsed = loads(sample)
    assert parsed["id"]["unitNum"] == 1
    assert parsed["buttons"][0]["shiftBits"] == 1
    assert parsed["keyboard"]["enable"] is True

    try:
        loads("{ a: 1 b: 2 }")
    except PinscapeParseError as exc:
        assert exc.line == 1
        assert "Expected ','" in str(exc)
    else:
        raise AssertionError("Invalid input should have failed")

    template = Path("../upload/Pasted text(18).txt")
    if template.exists():
        full = loads(template.read_text(encoding="utf-8-sig"))
        assert isinstance(full.get("buttons"), list)
        assert isinstance(full.get("outputs"), list)

    print("Parser tests passed")


if __name__ == "__main__":
    run()
