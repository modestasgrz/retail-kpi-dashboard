import argparse
import json
import re
from pathlib import Path

from loguru import logger

from kpi.fmt import SEP
from kpi.models import Summary

MARKER = re.compile(r" ?\[F\d+\]")
NOT_TEXT = re.compile(r"\s*([-*]\s|[-*_]{3,}\s*$|[>#|]|\d+\.\s)")
COMMA = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")


def extract(report_md: str) -> Summary | None:
    """Headline (first `## ` heading) + narrative paragraphs before the next `## ` heading, markers removed (DEC-14)."""
    lines = report_md.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    if not starts:
        return None
    end = starts[1] if len(starts) > 1 else len(lines)
    blocks = re.split(r"\n\s*\n", "\n".join(lines[starts[0] + 1 : end]))
    body = [
        " ".join(kept)
        for block in blocks
        if (
            kept := [
                line.strip()
                for line in block.splitlines()
                if line.strip() and not NOT_TEXT.match(line)
            ]
        )
    ]
    tidy = [
        COMMA.sub(SEP, MARKER.sub("", text)).strip()
        for text in [lines[starts[0]][3:], *body]
    ]
    return (
        Summary(headline=tidy[0], text="\n\n".join(tidy[1:])) if len(tidy) > 1 else None
    )


def build_summaries(src: Path, out: Path) -> int:
    """summaries.json {week: {headline, text}} from `<src>/<week>/report.md` of the earlier run; returns the count."""
    found = {}
    for report in sorted(src.glob("*/report.md")):
        summary = extract(report.read_text())
        if summary:
            found[report.parent.name] = summary.model_dump()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(found, indent=1, ensure_ascii=False) + "\n")
    logger.info("wrote {} saved summaries to {}", len(found), out)
    return len(found)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Extract the saved weekly summaries of an earlier offline run."
    )
    parser.add_argument("--from", dest="src", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("data/derived/summaries.json"))
    args = parser.parse_args(argv)
    build_summaries(args.src, args.out)


if __name__ == "__main__":
    main()
