from datetime import date, timedelta

from pydantic import BaseModel, model_validator

FIRST_WEEK = date(2010, 12, 6)
LAST_WEEK = date(2011, 12, 5)
MAX_DATE = LAST_WEEK + timedelta(days=6)
ALL = "All countries"
UK = "United Kingdom"
OUTSIDE_UK = "Outside UK"


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


class Filters(BaseModel):
    """Dashboard filters; dates snap to the Monday of their ISO week (DEC-05)."""

    start: date
    end: date
    country: str = ALL
    week: date

    @model_validator(mode="after")
    def check(self) -> "Filters":
        if any(
            d < FIRST_WEEK or d > MAX_DATE for d in (self.start, self.end, self.week)
        ):
            raise ValueError(f"Dates must be between {FIRST_WEEK} and {MAX_DATE}.")
        self.start, self.end, self.week = (
            monday(self.start),
            monday(self.end),
            monday(self.week),
        )
        if self.start > self.end:
            raise ValueError("Start week must be on or before end week.")
        if not self.start <= self.week <= self.end:
            raise ValueError("Selected week must be inside the date range.")
        return self


class Flag(BaseModel):
    week_start: date
    rule: str
    reason: str


class WeekRow(BaseModel):
    week_start: date
    revenue: float
    orders: int
    aov: float | None
    units: int
    customers: int
    new_customers: int
    returning_customers: int
    cancellation_rate: float | None
    cancelled_value: float
    net_revenue: float
    cancellation_invoices: int
    product_lines: int
    lines_without_customer_id: int
    revenue_wow: float | None
    orders_wow: float | None
    aov_wow: float | None
    units_wow: float | None
    customers_wow: float | None
    new_customers_wow: float | None
    returning_customers_wow: float | None
    cancellation_rate_change_pp: float | None
    cancelled_value_wow: float | None
    net_revenue_wow: float | None
    flags: list[Flag]


class Ranked(BaseModel):
    label: str
    revenue: float


class Totals(BaseModel):
    revenue: float
    orders: int
    units: int
    cancelled_value: float
    net_revenue: float
    weeks: int
    flagged_weeks: int


class Summary(BaseModel):
    headline: str
    text: str


class Scenario(BaseModel):
    filters: Filters
    weeks: list[WeekRow]
    selected: WeekRow
    totals: Totals
    top_products: list[Ranked]
    top_countries: list[Ranked]
    flags: list[Flag]
    sources: dict[str, str]
    summary: Summary | None
