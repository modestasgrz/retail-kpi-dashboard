from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

SEP = " "


def rounded(value: float, places: str) -> Decimal:
    """Half-up on the intended value: the float is snapped to 9 decimals first, so 538.3249999… (538.325) rounds up."""
    return (
        Decimal(value)
        .quantize(Decimal("1e-9"), ROUND_HALF_EVEN)
        .quantize(Decimal(places), ROUND_HALF_UP)
    )


def grouped(value: Decimal | int) -> str:
    return f"{value:,}".replace(",", SEP)


def money(value: float) -> str:
    r = rounded(value, "1")
    return f"{'-' if r < 0 else ''}£{grouped(abs(r))}"


def money2(value: float | None) -> str:
    if value is None:
        return "n/a"
    r = rounded(value, "0.01")
    return f"{'-' if r < 0 else ''}£{grouped(abs(r))}"


def count(value: int) -> str:
    return grouped(int(value))


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{rounded(value, '0.1')}%"


def signed(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    r = rounded(value, "0.1")
    return f"{'-' if r < 0 else '+'}{grouped(abs(r))}{unit}"


def change(value: float | None) -> str:
    return signed(value, "%")


def points(value: float | None) -> str:
    return signed(value, " pp")
