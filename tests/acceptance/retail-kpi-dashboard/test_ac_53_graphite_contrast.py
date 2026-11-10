"""AC-53 — Given `kpi/theme.py`, then the WCAG contrast against `BG` is at least 4.5:1 for `TEXT`, `MUTED`, `GOOD` and `BAD`, and at least 3:1 for the data colours `BLUE`, `NEW`, `RETURNING` and `AMBER`; `NEW` ≠ `RETURNING`; and the Plotly template's paper and plot background are `BG`."""


def contrast(a: str, b: str) -> float:
    def lum(h: str) -> float:
        rgb = [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b_ = (
            c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb
        )
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_

    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_ac_53_graphite_contrast() -> None:
    import kpi.theme as t

    for name in ("TEXT", "MUTED", "GOOD", "BAD"):
        assert contrast(getattr(t, name), t.BG) >= 4.5, name
    for name in ("BLUE", "NEW", "RETURNING", "AMBER"):
        assert contrast(getattr(t, name), t.BG) >= 3.0, name
    assert t.NEW.lower() != t.RETURNING.lower()
    assert t.TEMPLATE.layout.paper_bgcolor == t.BG
    assert t.TEMPLATE.layout.plot_bgcolor == t.BG
