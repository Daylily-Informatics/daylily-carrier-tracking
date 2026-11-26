"""Offline carrier recognition using the bundled tracking_number_data v2.0.0 catalog."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal


@dataclass(frozen=True)
class CarrierCandidate:
    """A plausible carrier and the number to query, when uniquely determined."""

    carrier_id: str
    display_name: str
    tracking_number: str | None


@dataclass(frozen=True)
class RecognitionResult:
    """An unchanged scan and all plausible carriers, in stable carrier-ID order."""

    scan: str
    status: Literal["identified", "ambiguous", "unknown"]
    candidates: tuple[CarrierCandidate, ...]


@dataclass(frozen=True)
class _Format:
    carrier_id: str
    display_name: str
    format_id: str | None
    pattern: re.Pattern[str]
    validation: dict[str, Any]


@lru_cache(maxsize=1)
def _catalog() -> tuple[tuple[_Format, ...], dict[str, str]]:
    formats = []
    postal_issuers = {}
    root = files("daylily_carrier_tracking").joinpath("data").joinpath("couriers")
    for path in sorted(root.iterdir(), key=lambda item: item.name):
        if not path.name.endswith(".json"):
            continue
        courier = json.loads(path.read_text(encoding="utf-8"))
        for rule in courier["tracking_numbers"]:
            pattern = "".join(rule["regex"])
            # The catalog uses Ruby/PCRE named groups. Leave lookarounds intact.
            pattern = re.sub(r"\(\?<([A-Za-z]\w*)>", r"(?P<\1>", pattern)
            formats.append(_Format(courier["courier_code"], courier["name"], rule.get("id"),
                                   re.compile(pattern, re.ASCII), rule["validation"]))
            if rule.get("id") == "s10":
                issuer_table = next(item for item in rule["additional"] if item["name"] == "Courier")
                postal_issuers = {entry["matches"]: entry["courier"] for entry in issuer_table["lookup"]}
    return tuple(formats), postal_issuers


def _checksum_valid(serial: str, check: str, rule: dict[str, Any]) -> bool:
    algorithm = rule["name"]
    if algorithm == "mod_37_36":
        alphabet = rule["alphabet"]
        remainder = 36
        for char in serial:
            remainder = (alphabet.index(char) + remainder - 1) % 36 + 1
            remainder = remainder * 2 % 37
        return alphabet[(37 - remainder) % 36] == check
    if algorithm == "mod10":
        if rule["reverse"]:
            serial = serial[::-1]
        values = (int(c) if c.isdigit() else (ord(c) - 3) % 10 for c in serial)
        weights = (rule["evens_multiplier"], rule["odds_multiplier"])
        total = sum(value * weights[i % 2] for i, value in enumerate(values))
        expected = -total % 10
    elif algorithm == "luhn":
        total = 0
        for i, char in enumerate(reversed(serial)):
            value = int(char) * (2 if i % 2 == 0 else 1)
            total += value - 9 if value > 9 else value
        expected = -total % 10
    elif algorithm == "mod7":
        expected = int(serial) % 7
    elif algorithm == "s10":
        total = sum(int(c) * w for c, w in zip(serial, rule["weightings"], strict=True))
        difference = 11 - total % 11
        expected = {10: 0, 11: 5}.get(difference, difference)
    elif algorithm == "sum_product_with_weightings_and_modulo":
        total = sum(int(c) * w for c, w in zip(serial, rule["weightings"], strict=True))
        expected = total % rule["modulo1"] % rule["modulo2"]
    else:
        raise ValueError(f"Unsupported catalog checksum {algorithm!r}")
    return str(expected) == check


def _valid(match: re.Match[str], fmt: _Format) -> bool:
    checksum = fmt.validation.get("checksum")
    if checksum is None:
        return True
    serial = match["SerialNumber"]
    if "serial_number_format" in fmt.validation:
        prepend = fmt.validation["serial_number_format"]["prepend_if"]
        if re.match(prepend["matches_regex"], serial):
            serial = prepend["content"] + serial
    return _checksum_valid(serial, match["CheckDigit"], checksum)


def _query_number(compact: str, match: re.Match[str], fmt: _Format) -> str | None:
    # FedEx FDX 1D positions 21–34 hold the tracking field. A 12-digit
    # Express number has exactly two padding zeros. Keep zeros within the ID.
    if fmt.format_id in {"fedex_34", "fedex_ground_gsn"}:
        encoded = match["SerialNumber"] + match["CheckDigit"]
        return encoded[2:] if encoded.startswith("00") else encoded
    if fmt.format_id in {"fedex_astra_32", "fedex_ground_96"}:
        return match["SerialNumber"] + match["CheckDigit"]
    if fmt.carrier_id == "usps" and match.groupdict().get("RoutingApplicationId"):
        return match["SerialNumber"] + match["CheckDigit"]
    if fmt.format_id == "dpd":
        # DPD's 28-character parcel label includes the destination ZIP,
        # 14-digit parcel number, service, country and label check character.
        return compact[7:21]
    return compact


def recognize_tracking_number(scan: str) -> RecognitionResult:
    """Identify carriers from scanner text without configuration or network I/O.

    A shared format may yield one named candidate and still be ambiguous.
    A missing query number means the scan cannot be mapped to a unique
    provider identifier for that candidate.
    """
    if not isinstance(scan, str):
        raise TypeError("scan must be a string")
    # Only ASCII layout whitespace is presentation. Do not remove punctuation,
    # arbitrary bytes, routing digits or leading zeros from unknown scans.
    compact = re.sub(r"[ \t\r\n]+", "", scan)
    if compact.startswith(("]C0", "]C1")):
        compact = compact[3:]  # AIM Code 128 / GS1-128 scanner header
    if not compact or not compact.isascii() or not compact.isprintable():
        return RecognitionResult(scan, "unknown", ())
    compact = compact.upper()

    formats, postal_issuers = _catalog()
    names: dict[str, str] = {}
    numbers: dict[str, set[str | None]] = {}
    has_identifying_match = False
    for fmt in formats:
        match = fmt.pattern.fullmatch(compact)
        if match is None or not _valid(match, fmt):
            continue
        carrier_id, display_name = fmt.carrier_id, fmt.display_name
        if fmt.format_id == "s10":
            country = match["CountryCode"]
            if country not in postal_issuers:
                continue  # The S10 rule requires a known issuing postal operator.
            display_name = postal_issuers[country]
            carrier_id = {"US": "usps", "CA": "canada_post"}.get(country, f"postal_{country.lower()}")
        # A postal issuing authority, shared GS1 container number, or bare
        # fourteen digits alone cannot identify the delivery carrier.
        if fmt.format_id not in {"s10", "fedex_ground_sscc_18", "dhl_ecommerce_14"}:
            has_identifying_match = True
        names[carrier_id] = display_name
        numbers.setdefault(carrier_id, set()).add(_query_number(compact, match, fmt))

    candidates = tuple(
        CarrierCandidate(carrier_id, names[carrier_id], next(iter(values)) if len(values) == 1 else None)
        for carrier_id, values in sorted(numbers.items())
    )
    if not candidates:
        return RecognitionResult(scan, "unknown", ())
    if len(candidates) == 1 and has_identifying_match:
        return RecognitionResult(scan, "identified", candidates)
    return RecognitionResult(scan, "ambiguous", candidates)

