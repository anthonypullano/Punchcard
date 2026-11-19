#!/usr/bin/env python3
"""
build_punchcard.py — Static Site Generator & Dev Server for PUNCHCARD.

Generates a standalone, mobile-responsive, 100% offline-capable HTML/CSS/JS
daily web game (`index.html`) measuring the historical labor cost (hours of
US labor required to purchase an item) across 5 escalating benchmarks.

Features:
  - Unified Median-Wage Gameplay + Dual-Lens Economic Receipts:
      * Per-round receipt shows both US Median Wage and Statutory Federal
        Minimum Wage work hours side by side.
      * Final scorecard features a prominent Median vs. Federal Minimum Wage
        toggle inside the Time-Price Trend synthesis banner (zero replay).
  - Rebalanced Scoring (2,000 Max / 1,000 Win Quota):
      * STANDARD PAY (1x / 0x, +200 / 0 PTS, unlimited) — 5/5 wins the shift
      * OVERTIME PAY (+2x / -1x, +400 / -200 PTS, silver ribbon, 2 per shift)
      * HOLIDAY PAY (+3x / -1.5x, +600 / -300 PTS, gold ribbon, 1 per shift)
      * TIME-PRICE BONUS AUDIT: 2 × +100 PTS questions with an explicit
        post-submission reveal showing all 5 items' 2026 labor-cost swings.
  - Time-Value-of-Money Asset Payout Tiers:
      * Company Scrip (<1,000) -> Paper Dollar (1,000–1,299) -> Silver Bullion
        (1,300–1,599) -> 24k Gold (1,600–1,899) -> Sovereign Gold (1,900–2,000)

Usage:
    python3 build_punchcard.py
    python3 build_punchcard.py --serve
    python3 build_punchcard.py --refresh-images --serve
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import math
from pathlib import Path
import re
import socket
import socketserver
import sys
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request


# =============================================================================
# 0. ARCHIVE LAUNCH DATE & IMAGE CACHE CONFIG
# =============================================================================
LAUNCH_DATE: str = "2026-11-12"
IMAGE_CACHE_FILENAME: str = ".punchcard_image_cache.json"


# =============================================================================
# 1. HISTORICAL US HOURLY WAGES (1940–2026)
# =============================================================================
# Production & nonsupervisory / median hourly compensation benchmarks (USD/hr)
HISTORICAL_US_HOURLY_WAGES: Dict[int, float] = {
    1940: 0.66,
    1941: 0.73,
    1942: 0.85,
    1943: 0.96,
    1944: 1.02,
    1945: 1.02,
    1946: 1.13,
    1947: 1.22,
    1948: 1.33,
    1949: 1.38,
    1950: 1.44,
    1951: 1.56,
    1952: 1.65,
    1953: 1.74,
    1954: 1.78,
    1955: 1.86,
    1956: 1.95,
    1957: 2.05,
    1958: 2.11,
    1959: 2.19,
    1960: 2.26,
    1961: 2.32,
    1962: 2.39,
    1963: 2.46,
    1964: 2.53,
    1965: 2.63,
    1966: 2.73,
    1967: 2.85,
    1968: 3.02,
    1969: 3.22,
    1970: 3.40,
    1971: 3.63,
    1972: 3.90,
    1973: 4.12,
    1974: 4.40,
    1975: 4.73,
    1976: 5.10,
    1977: 5.44,
    1978: 5.88,
    1979: 6.34,
    1980: 6.85,
    1981: 7.44,
    1982: 7.87,
    1983: 8.20,
    1984: 8.48,
    1985: 8.74,
    1986: 8.93,
    1987: 9.14,
    1988: 9.49,
    1989: 9.80,
    1990: 10.20,
    1991: 10.52,
    1992: 10.77,
    1993: 11.03,
    1994: 11.32,
    1995: 11.65,
    1996: 12.04,
    1997: 12.51,
    1998: 13.01,
    1999: 13.49,
    2000: 14.02,
    2001: 14.54,
    2002: 14.97,
    2003: 15.38,
    2004: 15.69,
    2005: 16.13,
    2006: 16.76,
    2007: 17.43,
    2008: 18.08,
    2009: 18.62,
    2010: 19.07,
    2011: 19.46,
    2012: 19.77,
    2013: 20.13,
    2014: 20.60,
    2015: 21.03,
    2016: 21.53,
    2017: 22.05,
    2018: 23.05,
    2019: 23.82,
    2020: 24.67,
    2021: 25.90,
    2022: 27.56,
    2023: 28.94,
    2024: 30.08,
    2025: 31.25,
    2026: 32.40,
}

# Statutory US Federal Minimum Wage (U.S. Department of Labor, USD/hr)
HISTORICAL_US_MINIMUM_WAGES: Dict[int, float] = {
    1940: 0.30,
    1941: 0.30,
    1942: 0.30,
    1943: 0.30,
    1944: 0.30,
    1945: 0.30,
    1946: 0.40,
    1947: 0.40,
    1948: 0.40,
    1949: 0.40,
    1950: 0.75,
    1951: 0.75,
    1952: 0.75,
    1953: 0.75,
    1954: 0.75,
    1955: 0.75,
    1956: 1.00,
    1957: 1.00,
    1958: 1.00,
    1959: 1.00,
    1960: 1.00,
    1961: 1.15,
    1962: 1.15,
    1963: 1.25,
    1964: 1.25,
    1965: 1.25,
    1966: 1.25,
    1967: 1.40,
    1968: 1.60,
    1969: 1.60,
    1970: 1.60,
    1971: 1.60,
    1972: 1.60,
    1973: 1.60,
    1974: 2.00,
    1975: 2.10,
    1976: 2.30,
    1977: 2.30,
    1978: 2.65,
    1979: 2.90,
    1980: 3.10,
    1981: 3.35,
    1982: 3.35,
    1983: 3.35,
    1984: 3.35,
    1985: 3.35,
    1986: 3.35,
    1987: 3.35,
    1988: 3.35,
    1989: 3.35,
    1990: 3.80,
    1991: 4.25,
    1992: 4.25,
    1993: 4.25,
    1994: 4.25,
    1995: 4.25,
    1996: 4.75,
    1997: 5.15,
    1998: 5.15,
    1999: 5.15,
    2000: 5.15,
    2001: 5.15,
    2002: 5.15,
    2003: 5.15,
    2004: 5.15,
    2005: 5.15,
    2006: 5.15,
    2007: 5.85,
    2008: 6.55,
    2009: 7.25,
    2010: 7.25,
    2011: 7.25,
    2012: 7.25,
    2013: 7.25,
    2014: 7.25,
    2015: 7.25,
    2016: 7.25,
    2017: 7.25,
    2018: 7.25,
    2019: 7.25,
    2020: 7.25,
    2021: 7.25,
    2022: 7.25,
    2023: 7.25,
    2024: 7.25,
    2025: 7.25,
    2026: 7.25,
}

DEFAULT_WAGE_TODAY: float = HISTORICAL_US_HOURLY_WAGES[2026]
DEFAULT_MIN_WAGE_TODAY: float = HISTORICAL_US_MINIMUM_WAGES[2026]

BENCHMARKS: List[Dict[str, Any]] = [
    {
        "round": 1,
        "hours": 1.0,
        "short_label": "1h",
        "title": "1 HOUR",
        "question_label": "1 WORK HOUR",
        "unit_singular": "Hour",
        "unit_plural": "Hours",
    },
    {
        "round": 2,
        "hours": 8.0,
        "short_label": "1d",
        "title": "1 DAY",
        "question_label": "1 WORKDAY",
        "unit_singular": "Workday",
        "unit_plural": "Workdays",
    },
    {
        "round": 3,
        "hours": 40.0,
        "short_label": "1w",
        "title": "1 WEEK",
        "question_label": "1 WORKWEEK",
        "unit_singular": "Workweek",
        "unit_plural": "Workweeks",
    },
    {
        "round": 4,
        "hours": 173.3,
        "short_label": "1m",
        "title": "1 MONTH",
        "question_label": "1 WORKMONTH",
        "unit_singular": "Workmonth",
        "unit_plural": "Workmonths",
    },
    {
        "round": 5,
        "hours": 2080.0,
        "short_label": "1y",
        "title": "1 YEAR",
        "question_label": "1 WORKYEAR",
        "unit_singular": "Workyear",
        "unit_plural": "Workyears",
    },
]

MIN_RATIO = 0.35
MAX_RATIO = 2.80


# =============================================================================
# 2. STARTER DATASET (30 HISTORICALLY ACCURATE ITEMS — 6 PER BENCHMARK TIER)
# =============================================================================
RAW_ITEMS: List[Dict[str, Any]] = [
    # --- TIER 1: ~1.0 WORK HOUR (0.35h – 2.80h) ---
    {
        "name": "1 lb Boneless Chuck Roast",
        "description": "Butcher counter beef chuck roast for a family pot roast dinner.",
        "category": "grocery",
        "year": 1948,
        "price_then": 0.69,
        "price_now": 7.49,
        "context_note": "Postwar beef shortages kept meat relatively costly per hour worked before industrial feedlots expanded supply.",
    },
    {
        "name": "1 Dozen Grade A Large Eggs",
        "description": "Carton of twelve fresh white shell eggs from a neighborhood grocer.",
        "category": "grocery",
        "year": 1955,
        "price_then": 0.72,
        "price_now": 3.85,
        "context_note": "Egg prices swung sharply by season in the 1950s before climate-controlled year-round poultry farming.",
    },
    {
        "name": "5-Gallon Fill-Up of Regular Gasoline",
        "description": "Five gallons of leaded regular pump fuel at a full-service station.",
        "category": "vehicle",
        "year": 1964,
        "price_then": 1.52,
        "price_now": 16.75,
        "context_note": "Despite decades of oil shocks, five gallons of gasoline costs nearly the same slice of median pay today as in 1964.",
    },
    {
        "name": "12-Inch Stereo Vinyl LP Album",
        "description": "Newly released major-label studio album pressed on 33-1/3 RPM vinyl.",
        "category": "electronics",
        "year": 1971,
        "price_then": 4.98,
        "price_now": 11.99,
        "context_note": "Buying one 40-minute LP in 1971 cost more work time than an entire month of unlimited music streaming today.",
    },
    {
        "name": "Evening Movie Ticket & Medium Popcorn",
        "description": "Single adult evening admission plus a medium salted popcorn at a suburban cinema.",
        "category": "grocery",
        "year": 1984,
        "price_then": 9.75,
        "price_now": 24.50,
        "context_note": "Even with modern multiplex concession markups, the median time-price of a night at the movies fell by a third since 1984.",
    },
    {
        "name": "Super NES Budget Cartridge Game",
        "description": "16-bit ROM cartridge video game in retail box with printed instruction manual.",
        "category": "electronics",
        "year": 1996,
        "price_then": 24.99,
        "price_now": 29.99,
        "context_note": "Custom silicon mask-ROM chips kept 1990s console cartridges expensive in labor terms compared to digital downloads.",
    },

    # --- TIER 2: ~8.0 WORK HOURS / 1 WORKDAY (2.83h – 17.88h) ---
    {
        "name": "Chrome 2-Slice Automatic Pop-Up Toaster",
        "description": "Heavy chrome-plated countertop electric toaster with thermostatic browning control.",
        "category": "appliance",
        "year": 1946,
        "price_then": 18.75,
        "price_now": 34.99,
        "context_note": "Early automatic pop-up toasters were precision-machined luxury appliances requiring over two full workdays of pay.",
    },
    {
        "name": "6-Transistor Pocket Portable Radio",
        "description": "Shirt-pocket battery-powered AM transistor radio with leatherette carrying case.",
        "category": "electronics",
        "year": 1957,
        "price_then": 29.95,
        "price_now": 19.99,
        "context_note": "Hand-soldered germanium transistors made pocket radios a major splurge before integrated circuits automated assembly.",
    },
    {
        "name": "10-Speed Countertop Kitchen Blender",
        "description": "Die-cast chrome base blender with 5-cup graduated glass pitcher.",
        "category": "appliance",
        "year": 1968,
        "price_then": 34.95,
        "price_now": 49.99,
        "context_note": "Heavy cast-metal housings and USA assembly made 1960s blenders durable but seven times costlier in work hours than today.",
    },
    {
        "name": "Sony Walkman Portable Cassette Player",
        "description": "Compact personal stereo tape player with lightweight foam-pad headphones.",
        "category": "electronics",
        "year": 1982,
        "price_then": 59.95,
        "price_now": 29.99,
        "context_note": "Rapid miniaturization pushed personal stereo players just under a single workday's median pay within three years of debut.",
    },
    {
        "name": "Standard 12-Volt Lead-Acid Car Battery",
        "description": "600 cold-cranking-amp replacement automotive starting battery.",
        "category": "vehicle",
        "year": 1998,
        "price_then": 54.99,
        "price_now": 159.99,
        "context_note": "High-draw onboard electronics and AGM battery chemistry have nudged car battery time-prices higher since 1998.",
    },
    {
        "name": "1-Week Family Grocery Cart (25 Staples)",
        "description": "Full supermarket cart of produce, dairy, meat, bread, and pantry staples for four.",
        "category": "grocery",
        "year": 2009,
        "price_then": 118.50,
        "price_now": 198.00,
        "context_note": "While checkout totals rose ~67% since 2009, median hourly wages climbed slightly faster—whereas the federal minimum wage stayed at $7.25.",
    },

    # --- TIER 3: ~40.0 WORK HOURS / 1 WORKWEEK (17.90h – 83.25h) ---
    {
        "name": "Tabletop Bakelite AM Tube Radio",
        "description": "Molded brown Bakelite cabinet 5-tube superheterodyne AM tabletop receiver.",
        "category": "electronics",
        "year": 1947,
        "price_then": 39.95,
        "price_now": 24.99,
        "context_note": "Hand-wired chassis and glass vacuum tubes meant even a basic tabletop radio cost over four full workdays in 1947.",
    },
    {
        "name": "Upright Bagged Household Vacuum Cleaner",
        "description": "Steel-body motorized beater-bar upright vacuum with cloth dust bag.",
        "category": "appliance",
        "year": 1959,
        "price_then": 69.95,
        "price_now": 129.00,
        "context_note": "Mid-century vacuums were built to be serviced for decades, costing roughly eight times more work hours than modern lightweight models.",
    },
    {
        "name": "Countertop Microwave Oven (Early Home Model)",
        "description": "1.1 cu. ft. countertop microwave with mechanical dial timer and browning element.",
        "category": "appliance",
        "year": 1976,
        "price_then": 349.00,
        "price_now": 119.00,
        "context_note": "Mass production of magnetrons in East Asia slashed microwave time-prices by nearly 95% over the next four decades.",
    },
    {
        "name": "Nintendo Entertainment System (NES) Bundle",
        "description": "8-bit home video game console with two controllers, Zapper light gun, and game.",
        "category": "electronics",
        "year": 1985,
        "price_then": 199.99,
        "price_now": 299.99,
        "context_note": "Launching after the 1983 video game crash, the NES bundle still demanded nearly three full workdays of median pay.",
    },
    {
        "name": "Set of 4 All-Season Radial Tires (Installed)",
        "description": "Four steel-belted all-season passenger tires including mounting and balancing.",
        "category": "vehicle",
        "year": 1993,
        "price_then": 520.00,
        "price_now": 680.00,
        "context_note": "Advances in synthetic rubber compounds and automated radial tire plants more than halved the median labor cost of re-shoeing a car.",
    },
    {
        "name": "3-Credit In-State Public University Course",
        "description": "One standard 3-credit undergraduate semester class at a public 4-year university.",
        "category": "housing_education",
        "year": 2014,
        "price_then": 1140.00,
        "price_now": 1425.00,
        "context_note": "Public university tuition outpaced wages for decades before state funding rebounds helped trim its median work-hour cost in the 2020s.",
    },

    # --- TIER 4: ~173.3 WORK HOURS / 1 WORKMONTH (83.26h – 485.2h) ---
    {
        "name": "17-Inch Black-and-White Console Television",
        "description": "Mahogany-veneer floor-standing CRT television with VHF rotary tuner.",
        "category": "electronics",
        "year": 1952,
        "price_then": 249.95,
        "price_now": 279.00,
        "context_note": "A 17-inch monochrome tube TV took nearly a month of median wages in 1952, versus one workday for a 55-inch 4K smart TV today.",
    },
    {
        "name": "12 cu. ft. Two-Door Frost-Free Refrigerator",
        "description": "Enameled steel top-freezer kitchen refrigerator with automatic defrost.",
        "category": "appliance",
        "year": 1963,
        "price_then": 329.00,
        "price_now": 799.00,
        "context_note": "Modern refrigerators offer 65% more capacity and use a quarter of the electricity while costing one-fifth the median labor hours.",
    },
    {
        "name": "1-Year In-State Tuition at a Public University",
        "description": "Full academic year undergraduate tuition and mandatory fees (in-state resident).",
        "category": "housing_education",
        "year": 1974,
        "price_then": 512.00,
        "price_now": 11610.00,
        "context_note": "In 1974, a student could cover an entire year of public university tuition with less than three weeks of median summer work.",
    },
    {
        "name": "IBM 5150 Personal Computer (64KB RAM)",
        "description": "Desktop PC with 4.77 MHz Intel 8088 CPU, 64KB RAM, floppy drive, and monochrome monitor.",
        "category": "electronics",
        "year": 1981,
        "price_then": 2880.00,
        "price_now": 699.00,
        "context_note": "The original IBM PC required over two full workmonths of median pay for 64 kilobytes of memory and no hard drive.",
    },
    {
        "name": "Central Air Conditioning System & Installation",
        "description": "3-ton split-system central A/C condenser, evaporator coil, and residential labor.",
        "category": "appliance",
        "year": 1997,
        "price_then": 3450.00,
        "price_now": 7800.00,
        "context_note": "Skilled HVAC installation labor and stricter SEER efficiency rules kept central air near 1.5 median workmonths across three decades.",
    },
    {
        "name": "1-Year Full-Time Toddler Childcare Tuition",
        "description": "Annual full-day enrollment at a licensed US center-based toddler childcare program.",
        "category": "housing_education",
        "year": 2018,
        "price_then": 10400.00,
        "price_now": 13100.00,
        "context_note": "Because early childhood care relies on hands-on human staffing that cannot be automated, its time-price exceeds 2.5 median workmonths.",
    },

    # --- TIER 5: ~2,080.0 WORK HOURS / 1 WORKYEAR (728.0h – 5,824.0h) ---
    {
        "name": "Brand-New Ford Custom Tudor Sedan",
        "description": "Factory-new two-door six-passenger sedan with flathead V8 and 3-speed manual.",
        "category": "vehicle",
        "year": 1949,
        "price_then": 1420.00,
        "price_now": 28500.00,
        "context_note": "Postwar sedans lacked seatbelts, airbags, A/C, and power steering, yet still required roughly half a year of median factory labor.",
    },
    {
        "name": "Median-Priced Single-Family US Home",
        "description": "Typical newly purchased single-family detached house in the United States.",
        "category": "housing_education",
        "year": 1960,
        "price_then": 11900.00,
        "price_now": 416900.00,
        "context_note": "The median US home more than doubled in median work-years required since 1960, even as average floor area expanded by 60%.",
    },
    {
        "name": "Brand-New Chevrolet Impala Sport Coupe",
        "description": "Full-size two-door hardtop coupe with V8 engine and Turbo Hydra-Matic transmission.",
        "category": "vehicle",
        "year": 1973,
        "price_then": 3760.00,
        "price_now": 34900.00,
        "context_note": "Crash-safety mandates, emissions gear, and onboard computers added capability while nudging full-size sedans past half a work-year.",
    },
    {
        "name": "4 Years of Private University (Tuition & Board)",
        "description": "Complete four-year undergraduate degree including tuition, fees, dorm, and meal plan.",
        "category": "housing_education",
        "year": 1988,
        "price_then": 46800.00,
        "price_now": 234000.00,
        "context_note": "Four years of private residential college climbed from 2.4 years of median wages in 1988 to nearly 3.5 full work-years today.",
    },
    {
        "name": "Brand-New Honda Accord LX Midsize Sedan",
        "description": "Four-door midsize sedan with 2.4L 4-cylinder engine, A/C, and anti-lock brakes.",
        "category": "vehicle",
        "year": 2003,
        "price_then": 19360.00,
        "price_now": 29390.00,
        "context_note": "Lean automotive manufacturing trimmed the Accord's median labor cost by ~350 work hours over two decades while doubling fuel economy.",
    },
    {
        "name": "Brand-New Full-Size 4WD Crew-Cab Pickup",
        "description": "Half-ton 4x4 four-door crew-cab pickup truck with V8 engine and towing package.",
        "category": "vehicle",
        "year": 2022,
        "price_then": 61500.00,
        "price_now": 65800.00,
        "context_note": "Loaded crew-cab pickups evolved from bare-bones work rigs into luxury family vehicles costing over an entire year of median labor.",
    },
]


# =============================================================================
# 3. ZERO-MAINTENANCE AUTOMATIC ITEM IMAGE RESOLVER (WIKIMEDIA COMMONS)
# =============================================================================
def build_image_search_queries(name: str, year: int, category: str) -> List[str]:
    """Generate primary and core-noun fallback search queries from any item name."""
    cleaned = re.sub(r"\([^)]*\)", "", name).strip()
    cleaned = re.sub(
        r"^(1\s+lb|1\s+Dozen|5-Gallon\s+Fill-Up\s+of|12-Inch|17-Inch|12\s+cu\.\s*ft\.|"
        r"Set\s+of\s+\d+|1-Week|1-Year|3-Credit|4\s+Years\s+of|Brand-New|Median-Priced)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    queries: List[str] = []
    if category == "vehicle" and any(
        brand in cleaned.lower() for brand in ("ford", "chevrolet", "honda")
    ):
        queries.append(f"{year} {cleaned}")
    queries.append(cleaned)

    words = [w for w in cleaned.split() if w.lower() not in ("of", "and", "&", "a", "the", "in", "at")]
    if len(words) > 2:
        short_q = " ".join(words[-2:])
        if short_q.lower() != cleaned.lower():
            queries.append(short_q)

    return queries


def query_wikimedia_commons(search_query: str, timeout: float = 4.0) -> Optional[str]:
    """Fetch a 320px bitmap thumbnail URL from Wikimedia Commons for search_query."""
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "generator": "search",
            "gsrnamespace": "6",  # File: namespace
            "gsrsearch": f"filetype:bitmap {search_query}",
            "gsrlimit": "5",
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": "320",
            "format": "json",
        }
    )
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PunchcardGameStaticBuilder/1.5 (https://github.com)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        ranked = sorted(pages.values(), key=lambda p: p.get("index", 999))
        for page in ranked:
            title_lower = page.get("title", "").lower()
            if any(bad in title_lower for bad in ("icon", "logo", "flag_of", "map_of")):
                continue
            info_list = page.get("imageinfo", [])
            if info_list:
                thumb = info_list[0].get("thumburl") or info_list[0].get("url")
                if thumb:
                    return str(thumb)
    except Exception:
        return None
    return None


def resolve_item_images(
    items: List[Dict[str, Any]],
    cache_path: Path,
    skip_fetch: bool = False,
    refresh: bool = False,
) -> None:
    """
    Populate `image_url` on each item automatically using primary + fallback queries.
    Caches results in `.punchcard_image_cache.json` for fast offline rebuilds.
    """
    cache: Dict[str, Optional[str]] = {}
    if cache_path.exists() and not refresh:
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    fetched_count = 0
    cache_dirty = False

    for item in items:
        queries = build_image_search_queries(item["name"], item["year"], item["category"])
        primary_q = queries[0]

        if item.get("image_url"):
            continue

        if primary_q in cache and cache[primary_q] and not refresh:
            item["image_url"] = cache[primary_q]
            continue

        if skip_fetch:
            item["image_url"] = None
            continue

        resolved_url: Optional[str] = None
        for q in queries:
            resolved_url = query_wikimedia_commons(q)
            if resolved_url:
                break

        item["image_url"] = resolved_url
        cache[primary_q] = resolved_url
        cache_dirty = True
        if resolved_url:
            fetched_count += 1

    if cache_dirty:
        try:
            cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        except Exception:
            pass

    if fetched_count > 0:
        print(f"Auto-resolved {fetched_count} new item photo(s) via Wikimedia Commons.")


# =============================================================================
# 4. AUTOMATIC LOGARITHMIC BUCKETING & DUAL WAGE-SERIES PIPELINE
# =============================================================================
def process_dataset(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Compute historical & current work hours under both US Median Wage and
    US Federal Minimum Wage, and assign each item to its logarithmic benchmark tier.
    """
    processed: List[Dict[str, Any]] = []

    for idx, item in enumerate(raw_items, start=1):
        year = int(item["year"])
        if year not in HISTORICAL_US_HOURLY_WAGES or year not in HISTORICAL_US_MINIMUM_WAGES:
            raise ValueError(
                f"Item '{item['name']}' uses year {year}, which is outside "
                f"wage tables ({min(HISTORICAL_US_HOURLY_WAGES)}-{max(HISTORICAL_US_HOURLY_WAGES)})."
            )

        price_then = float(item["price_then"])
        price_now = float(item["price_now"])

        # 1. Median Wage Series (Primary Gameplay Benchmark)
        wage_then = HISTORICAL_US_HOURLY_WAGES[year]
        wage_today = float(item.get("wage_today", DEFAULT_WAGE_TODAY))
        hours_then = price_then / wage_then
        hours_now = price_now / wage_today

        best_benchmark = min(
            BENCHMARKS,
            key=lambda b: abs(math.log(hours_then / float(b["hours"]))),
        )
        b_hours = float(best_benchmark["hours"])
        ratio = hours_then / b_hours

        if not (MIN_RATIO <= ratio <= MAX_RATIO):
            raise ValueError(
                f"Item '{item['name']}' ({year}) has ratio {ratio:.3f} against "
                f"benchmark {b_hours}h, outside [{MIN_RATIO}, {MAX_RATIO}]."
            )

        if abs(hours_then - b_hours) < 1e-9:
            raise ValueError(
                f"Item '{item['name']}' lands exactly on benchmark {b_hours}h under Median Wage."
            )

        direction = "OVER" if hours_then > b_hours else "UNDER"
        pct_diff = round(abs(ratio - 1.0) * 100)

        # 2. Federal Minimum Wage Series (Receipt Comparison & End-of-Shift Lens)
        min_wage_then = HISTORICAL_US_MINIMUM_WAGES[year]
        min_wage_today = float(item.get("min_wage_today", DEFAULT_MIN_WAGE_TODAY))
        min_hours_then = price_then / min_wage_then
        min_hours_now = price_now / min_wage_today
        min_ratio = min_hours_then / b_hours
        min_direction = "OVER" if min_hours_then > b_hours else "UNDER"
        min_pct_diff = round(abs(min_ratio - 1.0) * 100)

        processed.append(
            {
                "id": f"item_{idx:03d}",
                "name": item["name"],
                "description": item["description"],
                "category": item["category"],
                "year": year,
                "price_then": round(price_then, 2),
                "price_now": round(price_now, 2),
                "tier": int(best_benchmark["round"]),
                "benchmark_hours": b_hours,
                # Median Wage metrics
                "wage_then": round(wage_then, 2),
                "hours_then": round(hours_then, 2),
                "wage_today": round(wage_today, 2),
                "hours_now": round(hours_now, 2),
                "ratio": round(ratio, 4),
                "direction": direction,
                "pct_diff": pct_diff,
                # Federal Minimum Wage metrics
                "min_wage_then": round(min_wage_then, 2),
                "min_hours_then": round(min_hours_then, 2),
                "min_wage_today": round(min_wage_today, 2),
                "min_hours_now": round(min_hours_now, 2),
                "min_ratio": round(min_ratio, 4),
                "min_direction": min_direction,
                "min_pct_diff": min_pct_diff,
                "context_note": item["context_note"],
                "image_url": item.get("image_url"),
            }
        )

    for b in BENCHMARKS:
        tier_num = int(b["round"])
        tier_items = [x for x in processed if x["tier"] == tier_num]
        if not tier_items:
            raise ValueError(f"Benchmark tier {tier_num} ({b['title']}) has 0 items.")

    return processed


# =============================================================================
# 5. STANDALONE HTML / CSS / JS TEMPLATE
# =============================================================================
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0" />
  <title>PUNCHCARD — Daily Historical Labor Benchmark Game</title>
  <style>
    :root {
      /* 1960s Walnut Office Desk, Banker's Green Desk Blotter, & IBM Manila Cardstock */
      --desk-walnut: #5a3b22;
      --desk-walnut-dark: #3f2816;
      --blotter-felt: #264d39;
      --blotter-felt-deep: #1b3829;
      --blotter-leather: #231912;
      --card-manila: #efe1c1;
      --card-manila-light: #f8efd9;
      --card-manila-dark: #e0ceaa;
      --receipt-stock: #fbf6e9;
      --ink-primary: #1c1915;
      --ink-muted: #584e3f;
      --ink-faint: #847864;
      --col-rule: rgba(114, 92, 58, 0.14);
      --margin-red: rgba(185, 54, 38, 0.30);
      --border-dark: #221d17;
      --border-soft: #c2b191;
      --punch-red: #b93626;
      --punch-red-bg: #f9e6e2;
      --punch-teal: #196452;
      --punch-teal-bg: #e1f1ec;
      --silver-bar: linear-gradient(90deg, #b2bbc6, #eef2f6, #a8b2be);
      --silver-ink: #343d48;
      --gold-bar: linear-gradient(90deg, #c68716, #fae078, #c28112);
      --gold-ink: #754b04;
      --font-mono: "JetBrains Mono", "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--desk-walnut);
      background-image:
        repeating-linear-gradient(
          90deg,
          rgba(255, 214, 170, 0.04) 0px,
          rgba(255, 214, 170, 0.04) 3px,
          rgba(24, 13, 6, 0.14) 3px,
          rgba(24, 13, 6, 0.14) 9px,
          transparent 9px,
          transparent 22px
        ),
        repeating-linear-gradient(
          0deg,
          rgba(26, 14, 6, 0.28) 0px,
          rgba(26, 14, 6, 0.28) 2px,
          transparent 2px,
          transparent 140px
        ),
        linear-gradient(180deg, #634227 0%, #4b311c 50%, #3a2414 100%);
      color: var(--ink-primary);
      font-family: var(--font-mono);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 12px 14px 18px;
      line-height: 1.4;
    }

    /* Classic Banker's Green Felt Desk Blotter Pad under the Card */
    .desk-blotter {
      width: 100%;
      max-width: 884px;
      background-color: var(--blotter-felt);
      background-image:
        radial-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 0),
        radial-gradient(rgba(0, 0, 0, 0.12) 1px, transparent 0),
        linear-gradient(180deg, var(--blotter-felt) 0%, var(--blotter-felt-deep) 100%);
      background-size: 6px 6px, 9px 9px, 100% 100%;
      border: 5px solid var(--blotter-leather);
      outline: 2px dashed rgba(212, 178, 122, 0.35);
      outline-offset: -4px;
      border-radius: 10px;
      padding: 12px 14px 15px;
      box-shadow:
        0 18px 40px rgba(15, 8, 3, 0.65),
        inset 0 2px 10px rgba(0, 0, 0, 0.45);
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .app-shell {
      width: 100%;
      max-width: 848px;
      display: flex;
      flex-direction: column;
      gap: 9px;
    }

    /* --- TOP STEEL TIMECLOCK HEADER --- */
    .topbar {
      background: linear-gradient(180deg, #2d2a25 0%, #1c1a16 100%);
      border: 2px solid #534b3e;
      border-radius: 7px;
      padding: 8px 14px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      color: #f4ecda;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255,255,255,0.1);
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .brand-title {
      font-family: var(--font-sans);
      font-weight: 900;
      font-size: 1.2rem;
      letter-spacing: 0.16em;
      color: #f6eedc;
      text-transform: uppercase;
    }

    .puzzle-tag {
      font-size: 0.78rem;
      font-weight: 800;
      color: #f6eedc;
      background: #332f28;
      border: 1px solid #5e5547;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .pill-btn {
      background: #2e2a23;
      color: #ede3cf;
      border: 1px solid #595042;
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      padding: 5px 9px;
      border-radius: 4px;
      cursor: pointer;
      text-transform: uppercase;
      transition: background 0.15s, border-color 0.15s, transform 0.08s;
    }

    .pill-btn:hover {
      background: #3c372e;
      border-color: #8a7d68;
    }

    .pill-btn:active {
      transform: translateY(1px);
    }

    .pill-btn.archive-active {
      background: #d89b24;
      color: #171613;
      border-color: #f6d56b;
    }

    /* --- AUTHENTIC 80-COLUMN MANILA PUNCHCARD --- */
    .timecard {
      position: relative;
      background-color: var(--card-manila);
      background-image:
        linear-gradient(90deg, transparent 34px, var(--margin-red) 34px, var(--margin-red) 35px, transparent 35px),
        repeating-linear-gradient(
          90deg,
          transparent 0%,
          transparent calc(6.25% - 1px),
          var(--col-rule) calc(6.25% - 1px),
          var(--col-rule) 6.25%
        ),
        radial-gradient(rgba(115, 88, 46, 0.07) 1px, transparent 0);
      background-size: 100% 100%, 100% 100%, 10px 10px;
      border: 2px solid var(--border-dark);
      clip-path: polygon(22px 0, 100% 0, 100% 100%, 0 100%, 0 22px);
      border-radius: 0 6px 6px 6px;
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.52);
      overflow: hidden;
    }

    /* Crisp 2px Diagonal Ink Edge along the Top-Left Corner Chamfer */
    .timecard::before {
      content: "";
      position: absolute;
      top: -2px;
      left: -2px;
      width: 26px;
      height: 26px;
      background: linear-gradient(
        135deg,
        transparent 0%,
        transparent calc(50% - 1.5px),
        var(--border-dark) calc(50% - 1.5px),
        var(--border-dark) calc(50% + 1.5px),
        transparent calc(50% + 1.5px),
        transparent 100%
      );
      pointer-events: none;
      z-index: 6;
    }

    /* Top Card Form Header Strip */
    .card-perforation {
      height: 22px;
      background: var(--card-manila-dark);
      border-bottom: 1.5px solid #b5a27e;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 14px 0 42px;
      font-size: 0.58rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      color: var(--ink-muted);
      text-transform: uppercase;
    }

    /* Printed IBM 80-Column Registration Ruler */
    .column-ruler {
      background: rgba(224, 206, 170, 0.55);
      border-bottom: 1px dashed #b5a27e;
      padding: 2px 0;
      display: grid;
      grid-template-columns: repeat(16, 1fr);
      font-size: 0.52rem;
      font-weight: 800;
      color: #7d6f58;
      user-select: none;
    }

    .column-ruler span {
      text-align: right;
      padding-right: 4px;
    }

    .column-ruler-bottom {
      background: var(--card-manila-dark);
      border-top: 1px dashed #b5a27e;
      padding: 2px 0;
      display: grid;
      grid-template-columns: repeat(16, 1fr);
      font-size: 0.52rem;
      font-weight: 800;
      color: #7d6f58;
      user-select: none;
    }

    .column-ruler-bottom span {
      text-align: right;
      padding-right: 4px;
    }

    /* Archive Context Strip */
    .archive-banner {
      background: #1c1a17;
      color: #f6d56b;
      padding: 5px 16px;
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      border-bottom: 2px solid var(--border-dark);
    }

    .archive-return-link {
      background: #f6d56b;
      color: #1c1a17;
      border: none;
      border-radius: 3px;
      padding: 2px 8px;
      font-family: var(--font-mono);
      font-size: 0.66rem;
      font-weight: 800;
      cursor: pointer;
      text-transform: uppercase;
    }

    /* Shift HUD with 1,000-Pt Win Threshold Bar */
    .shift-hud {
      padding: 9px 16px;
      background: rgba(224, 206, 170, 0.72);
      border-bottom: 2px solid var(--border-dark);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .hud-top-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .score-readout {
      font-size: 0.84rem;
      font-weight: 800;
      letter-spacing: 0.02em;
      display: flex;
      align-items: center;
      gap: 7px;
      flex-wrap: wrap;
    }

    .score-readout .score-num {
      color: var(--ink-primary);
      font-size: 1.02rem;
    }

    .score-readout.cleared .score-num {
      color: var(--punch-teal);
    }

    .win-goal-badge {
      font-size: 0.62rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      padding: 1px 6px;
      border-radius: 3px;
      border: 1px solid var(--border-soft);
      background: var(--receipt-stock);
      color: var(--ink-muted);
      text-transform: uppercase;
    }

    .win-goal-badge.cleared {
      background: var(--punch-teal);
      color: #fff;
      border-color: var(--border-dark);
    }

    .countdown-readout {
      font-size: 0.72rem;
      color: var(--ink-muted);
      font-weight: 700;
    }

    /* 1,000-Point Shift Quota Gauge (1,000 / 2,000 = 50.0%) */
    .quota-track {
      position: relative;
      height: 6px;
      background: #d3c09c;
      border: 1px solid #8c7b5d;
      border-radius: 3px;
      overflow: visible;
    }

    .quota-fill {
      height: 100%;
      width: 0%;
      background: #9b6b19;
      border-radius: 2px;
      transition: width 0.35s ease, background 0.25s ease;
    }

    .quota-fill.cleared {
      background: var(--punch-teal);
    }

    .quota-marker {
      position: absolute;
      top: -3px;
      bottom: -3px;
      left: 50%;
      width: 2px;
      background: var(--punch-red);
    }

    .round-track {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 6px;
    }

    .round-pip {
      border: 1.5px solid #b5a27e;
      background: var(--receipt-stock);
      border-radius: 4px;
      padding: 4px 4px;
      text-align: center;
      font-size: 0.66rem;
      font-weight: 700;
      color: var(--ink-muted);
      transition: all 0.2s ease;
    }

    .round-pip.active {
      border-color: var(--border-dark);
      background: #1c1915;
      color: #f8efd9;
      box-shadow: 0 2px 0 rgba(0,0,0,0.2);
    }

    .round-pip.hit {
      border-color: var(--punch-teal);
      background: var(--punch-teal-bg);
      color: var(--punch-teal);
    }

    .round-pip.miss {
      border-color: var(--punch-red);
      background: var(--punch-red-bg);
      color: var(--punch-red);
    }

    .card-body {
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    /* Benchmark Banner */
    .benchmark-banner {
      border: 2px solid var(--border-dark);
      background: var(--receipt-stock);
      border-radius: 5px;
      padding: 8px 12px;
      text-align: center;
      box-shadow: 0 2px 0 rgba(0,0,0,0.08);
    }

    .benchmark-kicker {
      font-size: 0.68rem;
      font-weight: 800;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 2px;
    }

    .benchmark-headline {
      font-family: var(--font-sans);
      font-weight: 900;
      font-size: 1.22rem;
      letter-spacing: 0.03em;
      color: var(--ink-primary);
      text-transform: uppercase;
    }

    .benchmark-headline .accent-target {
      color: var(--punch-red);
      text-decoration: underline;
      text-decoration-thickness: 2px;
      text-underline-offset: 3px;
    }

    /* Item Specimen Dossier with Auto-Photo Plate + SVG Fallback */
    .item-dossier {
      display: grid;
      grid-template-columns: 82px 1fr;
      gap: 12px;
      align-items: center;
      background: var(--receipt-stock);
      border: 1.5px solid #b5a27e;
      border-radius: 5px;
      padding: 9px 12px;
    }

    .specimen-frame {
      position: relative;
      width: 82px;
      height: 82px;
      background: var(--card-manila-dark);
      border: 2px solid var(--border-dark);
      border-radius: 5px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: inset 0 0 0 2px rgba(255,255,255,0.45);
    }

    .specimen-svg-fallback {
      width: 66%;
      height: 66%;
      color: var(--ink-primary);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .specimen-svg-fallback svg {
      width: 100%;
      height: 100%;
    }

    .specimen-photo {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      opacity: 0;
      filter: sepia(0.18) contrast(1.06);
      transition: opacity 0.25s ease, filter 0.25s ease;
    }

    .specimen-photo.loaded {
      opacity: 1;
    }

    .specimen-frame:hover .specimen-photo.loaded {
      filter: sepia(0) contrast(1.03);
    }

    .item-meta-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 4px;
    }

    .year-stamp {
      background: var(--ink-primary);
      color: #f8efd9;
      font-family: var(--font-sans);
      font-weight: 900;
      font-size: 1.04rem;
      padding: 1px 9px;
      border-radius: 4px;
      letter-spacing: 0.06em;
      line-height: 1.25;
    }

    .category-stamp {
      border: 1px solid #b5a27e;
      color: var(--ink-muted);
      font-size: 0.65rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 2px 7px;
      border-radius: 3px;
      background: var(--card-manila-light);
    }

    .item-title {
      font-family: var(--font-sans);
      font-size: 1.08rem;
      font-weight: 800;
      color: var(--ink-primary);
      line-height: 1.22;
      margin-bottom: 2px;
    }

    .item-desc {
      font-size: 0.77rem;
      color: var(--ink-muted);
      line-height: 1.35;
    }

    /* --- PLAYER CONTROLS --- */
    .controls-panel {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .controls-split-grid {
      display: grid;
      grid-template-columns: 1fr 1.32fr;
      gap: 12px;
      align-items: stretch;
    }

    .control-group {
      display: flex;
      flex-direction: column;
    }

    .control-label {
      font-size: 0.68rem;
      font-weight: 800;
      letter-spacing: 0.07em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 5px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .direction-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      flex: 1;
    }

    .choice-btn {
      position: relative;
      background: var(--receipt-stock);
      border: 2px solid var(--border-dark);
      border-radius: 5px;
      padding: 10px 8px;
      font-family: var(--font-mono);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 3px;
      box-shadow: 0 3px 0 var(--border-dark);
      transition: transform 0.08s, box-shadow 0.08s, background 0.12s;
    }

    .choice-btn:hover {
      background: #fffdf7;
    }

    .choice-btn:active {
      transform: translateY(2px);
      box-shadow: 0 1px 0 var(--border-dark);
    }

    .keycap-tag {
      position: absolute;
      top: 4px;
      right: 5px;
      font-family: var(--font-mono);
      font-size: 0.54rem;
      font-weight: 800;
      line-height: 1;
      padding: 2px 4px;
      border-radius: 3px;
      border: 1px solid currentColor;
      opacity: 0.58;
      pointer-events: none;
    }

    .choice-btn .choice-main {
      font-family: var(--font-sans);
      font-size: 1.04rem;
      font-weight: 900;
      letter-spacing: 0.05em;
    }

    .choice-btn .choice-sub {
      font-size: 0.68rem;
      color: var(--ink-muted);
    }

    .choice-btn.selected-under {
      background: var(--punch-teal);
      color: #fff;
      border-color: var(--border-dark);
    }

    .choice-btn.selected-under .choice-sub {
      color: #d4efe8;
    }

    .choice-btn.selected-over {
      background: var(--punch-red);
      color: #fff;
      border-color: var(--border-dark);
    }

    .choice-btn.selected-over .choice-sub {
      color: #fbe0dc;
    }

    /* --- PAYROLL TIMECLOCK STAMP SELECTOR KEYS --- */
    .stamp-key-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 7px;
      flex: 1;
    }

    .stamp-key {
      position: relative;
      background: var(--receipt-stock);
      border: 2px solid var(--border-dark);
      border-radius: 5px;
      overflow: hidden;
      font-family: var(--font-mono);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: stretch;
      box-shadow: 0 3px 0 var(--border-dark);
      transition: transform 0.08s, box-shadow 0.08s, background 0.14s, opacity 0.15s;
      user-select: none;
    }

    .stamp-key:active:not(:disabled) {
      transform: translateY(2px);
      box-shadow: 0 1px 0 var(--border-dark);
    }

    .stamp-key:disabled {
      opacity: 0.4;
      cursor: not-allowed;
      box-shadow: none;
      background: var(--card-manila-dark);
    }

    .stamp-ribbon {
      position: relative;
      padding: 4px 16px 4px 6px;
      font-size: 0.57rem;
      font-weight: 900;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      text-align: center;
      border-bottom: 1.5px solid var(--border-dark);
      white-space: nowrap;
    }

    .stamp-ribbon .keycap-tag {
      top: 50%;
      right: 4px;
      transform: translateY(-50%);
      opacity: 0.72;
    }

    .stamp-key[data-stamp="BASE"] .stamp-ribbon {
      background: var(--card-manila-dark);
      color: var(--ink-primary);
    }

    .stamp-key[data-stamp="SILVER"] .stamp-ribbon {
      background: var(--silver-bar);
      color: #181e26;
    }

    .stamp-key[data-stamp="GOLD"] .stamp-ribbon {
      background: var(--gold-bar);
      color: #2c1c02;
    }

    .stamp-key-body {
      padding: 6px 4px 6px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
      flex: 1;
    }

    .stamp-mult-row {
      display: flex;
      align-items: baseline;
      gap: 4px;
      font-family: var(--font-sans);
      font-weight: 900;
    }

    .mult-win {
      font-size: 1.05rem;
      color: var(--ink-primary);
    }

    .mult-slash {
      font-size: 0.74rem;
      color: var(--ink-faint);
    }

    .mult-loss {
      font-size: 0.8rem;
      color: var(--punch-red);
    }

    .stamp-pts-row {
      font-size: 0.62rem;
      font-weight: 700;
      color: var(--ink-muted);
    }

    .stamp-holes-footer {
      margin-top: 2px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      font-size: 0.56rem;
      font-weight: 800;
      letter-spacing: 0.03em;
      padding: 1px 5px;
      border-radius: 3px;
      background: var(--card-manila-dark);
      color: var(--ink-primary);
      border: 1px solid #b5a27e;
    }

    .mini-hole-dots {
      display: inline-flex;
      gap: 2px;
    }

    .mini-hole-dots i {
      display: inline-block;
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: var(--ink-primary);
    }

    .stamp-key.selected {
      background: #1c1915;
      color: #f8efd9;
      transform: translateY(2px);
      box-shadow: 0 1px 0 #000;
    }

    .stamp-key.selected .mult-win {
      color: #f8efd9;
    }

    .stamp-key.selected .mult-loss {
      color: #ff8a7a;
    }

    .stamp-key.selected .stamp-pts-row {
      color: #cfc6b4;
    }

    .stamp-key.selected .stamp-holes-footer {
      background: #2f2b24;
      color: #f6d56b;
      border-color: #5a5141;
    }

    .stamp-key.selected .mini-hole-dots i {
      background: #f6d56b;
    }

    .punch-submit-btn {
      width: 100%;
      padding: 12px 16px;
      border: 2px solid var(--border-dark);
      border-radius: 5px;
      background: var(--ink-primary);
      color: #f8efd9;
      font-family: var(--font-sans);
      font-size: 0.98rem;
      font-weight: 900;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      cursor: pointer;
      box-shadow: 0 3px 0 #000;
      transition: transform 0.08s, box-shadow 0.08s, opacity 0.15s, background 0.15s;
    }

    .punch-submit-btn:disabled {
      opacity: 0.42;
      cursor: not-allowed;
      box-shadow: none;
    }

    .punch-submit-btn:not(:disabled):hover {
      background: #2f2b24;
    }

    .punch-submit-btn:not(:disabled):active {
      transform: translateY(2px);
      box-shadow: 0 1px 0 #000;
    }

    .punch-submit-btn.ready-teal {
      background: var(--punch-teal);
      color: #fff;
      box-shadow: 0 3px 0 var(--border-dark);
    }

    .punch-submit-btn.ready-teal:hover {
      background: #145344;
    }

    /* --- 4-STAT TIMECARD RECEIPT WITH MINIMUM WAGE LENS --- */
    .receipt-reveal {
      background: var(--receipt-stock);
      border: 2px solid var(--border-dark);
      border-radius: 5px;
      padding: 9px 14px 11px;
      display: flex;
      flex-direction: column;
      gap: 7px;
      animation: receiptSlideIn 0.25s ease-out both;
      box-shadow: inset 0 0 0 1px rgba(0,0,0,0.04);
    }

    @keyframes receiptSlideIn {
      0% {
        opacity: 0;
        transform: translateY(-6px);
      }
      100% {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .receipt-top-strip {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      padding-bottom: 7px;
      border-bottom: 2px dashed #b5a27e;
      flex-wrap: wrap;
    }

    .receipt-punch-cluster {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .punch-holes-row {
      display: flex;
      align-items: center;
      gap: 7px;
    }

    .die-cut-hole {
      width: 15px;
      height: 15px;
      border-radius: 50%;
      background: var(--blotter-felt-deep);
      border: 2px solid #96876b;
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.85);
      animation: holePunchPop 0.24s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    }

    .die-cut-hole:nth-child(2) {
      animation-delay: 0.06s;
    }

    .die-cut-hole:nth-child(3) {
      animation-delay: 0.12s;
    }

    @keyframes holePunchPop {
      0% {
        transform: scale(0.1);
        opacity: 0;
      }
      100% {
        transform: scale(1);
        opacity: 1;
      }
    }

    .punch-cluster-caption {
      font-size: 0.63rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--ink-muted);
    }

    .ink-stamp-box {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .ink-stamp-impression {
      font-family: var(--font-sans);
      font-weight: 900;
      font-size: 0.86rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 3px 10px;
      border: 3px double currentColor;
      border-radius: 4px;
      transform: rotate(-2deg);
      animation: stampSlam 0.34s cubic-bezier(0.18, 0.89, 0.32, 1.28) both;
    }

    @keyframes stampSlam {
      0% {
        opacity: 0;
        transform: scale(2.15) rotate(-9deg);
      }
      65% {
        opacity: 1;
        transform: scale(0.94) rotate(-1.8deg);
      }
      100% {
        opacity: 1;
        transform: scale(1) rotate(-2deg);
      }
    }

    .ink-stamp-impression.ink-hit-base {
      color: var(--punch-teal);
      background: var(--punch-teal-bg);
    }

    .ink-stamp-impression.ink-hit-silver {
      color: var(--silver-ink);
      background: #edf1f5;
      box-shadow: 0 0 0 1px #8c96a4;
    }

    .ink-stamp-impression.ink-hit-gold {
      color: var(--gold-ink);
      background: #fdf3d7;
      box-shadow: 0 0 0 1px #d89b24;
    }

    .ink-stamp-impression.ink-miss-neutral {
      color: var(--ink-muted);
      background: var(--card-manila-dark);
    }

    .ink-stamp-impression.ink-miss-docked {
      color: var(--punch-red);
      background: var(--punch-red-bg);
    }

    .verdict-points {
      font-weight: 900;
      font-size: 0.94rem;
    }

    .verdict-points.positive {
      color: var(--punch-teal);
    }

    .verdict-points.negative {
      color: var(--punch-red);
    }

    .verdict-points.neutral {
      color: var(--ink-muted);
    }

    .threshold-box {
      background: var(--card-manila-light);
      border: 1.5px solid #b5a27e;
      border-radius: 5px;
      padding: 6px 10px;
    }

    .threshold-labels {
      display: flex;
      justify-content: space-between;
      font-size: 0.62rem;
      font-weight: 800;
      color: var(--ink-muted);
      text-transform: uppercase;
      margin-bottom: 3px;
    }

    .threshold-track {
      position: relative;
      height: 15px;
      background: #dfd0b2;
      border: 1.5px solid var(--border-dark);
      border-radius: 4px;
      overflow: hidden;
    }

    .threshold-fill {
      height: 100%;
      width: 0%;
      transition: width 0.55s cubic-bezier(0.22, 1, 0.36, 1);
    }

    .threshold-fill.under {
      background: var(--punch-teal);
    }

    .threshold-fill.over {
      background: var(--punch-red);
    }

    .threshold-pin {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 50%;
      width: 2px;
      background: var(--border-dark);
      z-index: 2;
    }

    .threshold-pin::after {
      content: "";
      position: absolute;
      top: 0;
      left: -4px;
      border-left: 5px solid transparent;
      border-right: 5px solid transparent;
      border-top: 5px solid var(--border-dark);
    }

    .threshold-caption {
      margin-top: 3px;
      font-size: 0.71rem;
      font-weight: 700;
      text-align: center;
      color: var(--ink-primary);
    }

    .stats-4-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 7px;
    }

    .stat-cell {
      background: var(--card-manila-light);
      border: 1.5px solid #b5a27e;
      border-radius: 5px;
      padding: 6px 8px;
    }

    .stat-cell-label {
      font-size: 0.61rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--ink-muted);
      margin-bottom: 2px;
    }

    .stat-cell-value {
      font-family: var(--font-sans);
      font-size: 1.02rem;
      font-weight: 900;
      color: var(--ink-primary);
    }

    .stat-cell-sub {
      font-size: 0.65rem;
      color: var(--ink-muted);
      margin-top: 1px;
    }

    /* Per-Round Federal Minimum Wage Lens Strip */
    .min-wage-callout {
      background: #f4e6d8;
      border: 1.5px solid #c99a84;
      border-left: 4px solid #8a2c1e;
      border-radius: 4px;
      padding: 6px 10px;
      font-size: 0.71rem;
      color: var(--ink-primary);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .min-wage-tag {
      font-weight: 900;
      font-size: 0.63rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: #8a2c1e;
      background: #fbece7;
      border: 1px solid #d49d8a;
      padding: 1px 6px;
      border-radius: 3px;
    }

    .context-note-box {
      background: #eee3ca;
      border-left: 4px solid var(--ink-primary);
      padding: 6px 10px;
      font-size: 0.74rem;
      color: var(--ink-primary);
      line-height: 1.35;
    }

    /* --- 2-QUESTION ACTIVE TIME-PRICE BONUS AUDIT VIEW & REVEAL --- */
    .bonus-audit-header {
      border: 2px solid var(--border-dark);
      background: var(--receipt-stock);
      border-radius: 5px;
      padding: 9px 12px;
      text-align: center;
    }

    .bonus-audit-kicker {
      font-size: 0.68rem;
      font-weight: 800;
      letter-spacing: 0.09em;
      color: var(--gold-ink);
      text-transform: uppercase;
      margin-bottom: 2px;
    }

    .bonus-audit-title {
      font-family: var(--font-sans);
      font-size: 1.12rem;
      font-weight: 900;
      color: var(--ink-primary);
      text-transform: uppercase;
    }

    .bonus-questions-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    .bonus-q-card {
      background: var(--receipt-stock);
      border: 1.5px solid #b5a27e;
      border-radius: 5px;
      padding: 9px 10px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .bonus-q-header-row {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .bonus-q-label {
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--ink-primary);
      line-height: 1.3;
    }

    .bonus-q-badge {
      display: inline-block;
      background: var(--ink-primary);
      color: #f6d56b;
      font-size: 0.58rem;
      font-weight: 800;
      padding: 1px 5px;
      border-radius: 3px;
      margin-right: 4px;
      vertical-align: middle;
    }

    .audit-verdict-stamp {
      display: inline-block;
      align-self: flex-start;
      font-family: var(--font-sans);
      font-size: 0.66rem;
      font-weight: 900;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 2px 7px;
      border-radius: 3px;
      border: 1.5px solid currentColor;
      animation: receiptSlideIn 0.2s ease-out both;
    }

    .audit-verdict-stamp.hit {
      color: var(--punch-teal);
      background: var(--punch-teal-bg);
    }

    .audit-verdict-stamp.miss {
      color: var(--punch-red);
      background: var(--punch-red-bg);
    }

    .bonus-options-list {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .bonus-opt-btn {
      width: 100%;
      text-align: left;
      background: var(--card-manila-light);
      border: 1.5px solid #b5a27e;
      border-radius: 4px;
      padding: 6px 8px;
      font-family: var(--font-mono);
      font-size: 0.71rem;
      color: var(--ink-primary);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
      transition: background 0.12s, border-color 0.12s;
    }

    .bonus-opt-btn:hover:not(:disabled) {
      background: #fffdf7;
      border-color: var(--border-dark);
    }

    .bonus-opt-btn:disabled {
      cursor: default;
    }

    .bonus-opt-btn.selected {
      background: #1c1915;
      color: #f8efd9;
      border-color: var(--border-dark);
      font-weight: 800;
    }

    /* Revealed Option Highlight States */
    .bonus-opt-btn.audit-correct {
      background: var(--punch-teal-bg);
      color: var(--punch-teal);
      border: 2px solid var(--punch-teal);
      font-weight: 800;
    }

    .bonus-opt-btn.audit-winner-reveal {
      background: var(--punch-teal-bg);
      color: var(--punch-teal);
      border: 1.5px dashed var(--punch-teal);
      font-weight: 800;
    }

    .bonus-opt-btn.audit-wrong {
      background: var(--punch-red-bg);
      color: var(--punch-red);
      border: 2px solid var(--punch-red);
      font-weight: 800;
    }

    .bonus-opt-btn.audit-neutral {
      opacity: 0.78;
    }

    .bonus-opt-right {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      flex-shrink: 0;
    }

    .bonus-opt-year {
      font-size: 0.64rem;
      font-weight: 800;
      opacity: 0.75;
    }

    .audit-role-tag {
      font-size: 0.56rem;
      font-weight: 900;
      letter-spacing: 0.04em;
      padding: 1px 4px;
      border-radius: 2px;
      border: 1px solid currentColor;
      text-transform: uppercase;
    }

    .audit-swing-pill {
      font-size: 0.63rem;
      font-weight: 900;
      padding: 1px 5px;
      border-radius: 3px;
      min-width: 44px;
      text-align: right;
    }

    .audit-swing-pill.drop {
      background: #d2ebe4;
      color: #0e4a3b;
    }

    .audit-swing-pill.surge {
      background: #f5d6d1;
      color: #8f2214;
    }

    .audit-swing-pill.flat {
      background: var(--card-manila-dark);
      color: var(--ink-muted);
    }

    /* --- END-OF-RUN SUMMARY SCREEN WITH PAYOUT ASSET RANKS & WAGE LENS TOGGLE --- */
    .summary-header {
      text-align: center;
      padding: 10px 12px;
      background: var(--receipt-stock);
      border: 2px solid var(--border-dark);
      border-radius: 5px;
    }

    .payout-rank-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 4px;
    }

    .payout-asset-pill {
      display: inline-block;
      font-family: var(--font-sans);
      font-size: 0.76rem;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 3px 11px;
      border-radius: 4px;
      border: 2px solid var(--border-dark);
    }

    .payout-asset-pill.tier-sovereign {
      background: var(--gold-bar);
      color: #2c1c02;
    }

    .payout-asset-pill.tier-gold {
      background: #fdf0c2;
      color: var(--gold-ink);
      border-color: #c68716;
    }

    .payout-asset-pill.tier-silver {
      background: var(--silver-bar);
      color: #181e26;
      border-color: #6c7785;
    }

    .payout-asset-pill.tier-paper {
      background: var(--punch-teal-bg);
      color: var(--punch-teal);
      border-color: var(--punch-teal);
    }

    .payout-asset-pill.tier-scrip {
      background: var(--punch-red-bg);
      color: var(--punch-red);
      border-color: var(--punch-red);
    }

    .summary-score-big {
      font-family: var(--font-sans);
      font-size: 1.9rem;
      font-weight: 900;
      color: var(--ink-primary);
      line-height: 1.1;
    }

    .summary-score-max {
      font-size: 0.92rem;
      font-weight: 700;
      color: var(--ink-muted);
    }

    .summary-threshold-sub {
      font-size: 0.69rem;
      font-weight: 700;
      color: var(--ink-muted);
      margin-top: 2px;
    }

    .summary-kpis {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 7px;
      margin-top: 8px;
    }

    .kpi-mini {
      background: var(--card-manila-light);
      border: 1px solid #b5a27e;
      border-radius: 4px;
      padding: 5px 4px;
    }

    .kpi-mini-val {
      font-weight: 900;
      font-size: 0.85rem;
    }

    .kpi-mini-lbl {
      font-size: 0.58rem;
      text-transform: uppercase;
      color: var(--ink-muted);
    }

    /* Prominent End-of-Shift Time-Price Trend & Wage Lens Switcher */
    .trend-synthesis-banner {
      background: #1c1915;
      color: #f8efd9;
      border: 2px solid var(--border-dark);
      border-radius: 5px;
      padding: 9px 12px;
      font-size: 0.72rem;
      line-height: 1.4;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .trend-banner-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .trend-synthesis-title {
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #f6d56b;
      font-size: 0.68rem;
    }

    .summary-wage-switch {
      display: inline-flex;
      border: 1.5px solid #6b604e;
      border-radius: 4px;
      overflow: hidden;
      background: #2b2721;
    }

    .summary-wage-btn {
      border: none;
      background: transparent;
      color: #cfc5b2;
      font-family: var(--font-mono);
      font-size: 0.66rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      padding: 4px 10px;
      cursor: pointer;
      text-transform: uppercase;
      transition: background 0.14s, color 0.14s;
    }

    .summary-wage-btn:hover:not(.active) {
      background: #3a352d;
      color: #fff;
    }

    .summary-wage-btn.active {
      background: #f6d56b;
      color: #1c1915;
    }

    .summary-wage-btn.active[data-lens="MINIMUM"] {
      background: #d9534f;
      color: #fff;
    }

    .recap-list {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .recap-row {
      background: var(--receipt-stock);
      border: 1.5px solid #b5a27e;
      border-radius: 5px;
      padding: 7px 11px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
    }

    .recap-left {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .recap-item-name {
      font-weight: 800;
      font-size: 0.8rem;
      color: var(--ink-primary);
    }

    .recap-meta {
      font-size: 0.68rem;
      color: var(--ink-muted);
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .trend-pill {
      display: inline-block;
      font-size: 0.61rem;
      font-weight: 800;
      padding: 1px 6px;
      border-radius: 3px;
      letter-spacing: 0.03em;
    }

    .trend-pill.cheaper {
      background: var(--punch-teal-bg);
      color: var(--punch-teal);
      border: 1px solid rgba(25, 100, 82, 0.35);
    }

    .trend-pill.costlier {
      background: var(--punch-red-bg);
      color: var(--punch-red);
      border: 1px solid rgba(185, 54, 38, 0.35);
    }

    .trend-pill.flat {
      background: var(--card-manila-dark);
      color: var(--ink-muted);
      border: 1px solid #b5a27e;
    }

    .recap-right {
      text-align: right;
      flex-shrink: 0;
    }

    .recap-badge {
      display: inline-block;
      font-size: 0.69rem;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 3px;
    }

    .recap-badge.hit {
      background: var(--punch-teal-bg);
      color: var(--punch-teal);
    }

    .recap-badge.miss {
      background: var(--punch-red-bg);
      color: var(--punch-red);
    }

    .recap-margin {
      font-size: 0.66rem;
      color: var(--ink-muted);
      margin-top: 2px;
    }

    .share-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      align-items: stretch;
    }

    .share-btn {
      width: 100%;
      padding: 10px 14px;
      background: var(--punch-teal);
      color: #fff;
      border: 2px solid var(--border-dark);
      border-radius: 5px;
      font-family: var(--font-sans);
      font-size: 0.9rem;
      font-weight: 900;
      letter-spacing: 0.07em;
      text-transform: uppercase;
      cursor: pointer;
      box-shadow: 0 3px 0 var(--border-dark);
      transition: transform 0.08s, box-shadow 0.08s;
    }

    .share-btn:active {
      transform: translateY(2px);
      box-shadow: 0 1px 0 var(--border-dark);
    }

    .secondary-action-btn {
      width: 100%;
      padding: 10px 14px;
      background: var(--receipt-stock);
      color: var(--ink-primary);
      border: 2px solid var(--border-dark);
      border-radius: 5px;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 800;
      text-transform: uppercase;
      cursor: pointer;
      box-shadow: 0 3px 0 var(--border-dark);
    }

    .secondary-action-btn:active {
      transform: translateY(2px);
      box-shadow: 0 1px 0 var(--border-dark);
    }

    .share-preview {
      grid-column: span 2;
      background: #1c1915;
      color: #efe1c1;
      padding: 8px 11px;
      border-radius: 5px;
      font-size: 0.69rem;
      white-space: pre-wrap;
      border: 1px solid #494237;
    }

    /* --- MODALS (RULES, STATS & TIMECARD RACK ARCHIVE) --- */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(18, 12, 7, 0.82);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 16px;
      z-index: 50;
    }

    .modal-backdrop.open {
      display: flex;
    }

    .modal-card {
      background: var(--card-manila);
      border: 2px solid var(--border-dark);
      border-radius: 7px;
      width: 100%;
      max-width: 530px;
      max-height: 88vh;
      padding: 18px;
      box-shadow: 0 14px 36px rgba(0, 0, 0, 0.65);
      display: flex;
      flex-direction: column;
      gap: 12px;
      overflow-y: auto;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid var(--border-dark);
      padding-bottom: 8px;
      flex-shrink: 0;
    }

    .modal-title {
      font-family: var(--font-sans);
      font-weight: 900;
      font-size: 1.05rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .close-btn {
      background: var(--ink-primary);
      color: #fff;
      border: none;
      border-radius: 4px;
      padding: 4px 10px;
      font-family: var(--font-mono);
      font-weight: 800;
      cursor: pointer;
    }

    .rules-list {
      display: flex;
      flex-direction: column;
      gap: 9px;
      font-size: 0.77rem;
      color: var(--ink-primary);
    }

    .rule-card {
      background: var(--receipt-stock);
      border: 1.5px solid #b5a27e;
      border-radius: 5px;
      padding: 9px 11px;
    }

    .rule-card-title {
      font-family: var(--font-sans);
      font-weight: 900;
      font-size: 0.83rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 3px;
      color: var(--ink-primary);
    }

    .rule-stamp-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 5px;
      font-size: 0.69rem;
    }

    .rule-stamp-table th,
    .rule-stamp-table td {
      border: 1px solid #c2b191;
      padding: 4px 6px;
      text-align: left;
    }

    .rule-stamp-table th {
      background: var(--card-manila-dark);
      font-weight: 800;
    }

    .lifetime-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }

    .lifetime-box {
      background: var(--receipt-stock);
      border: 1.5px solid #b5a27e;
      border-radius: 5px;
      padding: 10px;
      text-align: center;
    }

    .lifetime-val {
      font-family: var(--font-sans);
      font-size: 1.35rem;
      font-weight: 900;
      color: var(--ink-primary);
    }

    .lifetime-lbl {
      font-size: 0.68rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-top: 2px;
    }

    .modal-footnote {
      font-size: 0.72rem;
      color: var(--ink-muted);
      line-height: 1.4;
    }

    .rack-scroll {
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-right: 2px;
    }

    .rack-slot {
      width: 100%;
      text-align: left;
      background: var(--receipt-stock);
      border: 1.5px solid var(--border-dark);
      border-radius: 5px;
      padding: 11px 12px;
      font-family: var(--font-mono);
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      transition: background 0.12s, transform 0.08s;
    }

    .rack-slot:hover {
      background: #fffdf7;
    }

    .rack-slot.current-loaded {
      border-width: 2.5px;
      background: #fbf3df;
    }

    .rack-slot-title {
      font-family: var(--font-sans);
      font-weight: 900;
      font-size: 0.94rem;
      color: var(--ink-primary);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .rack-live-tag {
      background: var(--punch-red);
      color: #fff;
      font-family: var(--font-mono);
      font-size: 0.6rem;
      font-weight: 800;
      padding: 1px 5px;
      border-radius: 3px;
    }

    .rack-slot-date {
      font-size: 0.72rem;
      color: var(--ink-muted);
      margin-top: 2px;
    }

    .rack-status {
      text-align: right;
      flex-shrink: 0;
    }

    .status-pill {
      display: inline-block;
      font-size: 0.66rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      padding: 3px 7px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .status-pill.unpunched {
      background: var(--card-manila-dark);
      color: var(--ink-muted);
      border: 1px solid #b5a27e;
    }

    .status-pill.in-progress {
      background: #fbf1e1;
      color: #9b600c;
      border: 1px solid #d89b24;
    }

    .status-pill.completed-win {
      background: var(--punch-teal-bg);
      color: var(--punch-teal);
      border: 1px solid var(--punch-teal);
    }

    .status-pill.completed-short {
      background: var(--punch-red-bg);
      color: var(--punch-red);
      border: 1px solid var(--punch-red);
    }

    .rack-mini-squares {
      font-size: 0.68rem;
      margin-top: 3px;
      letter-spacing: 1px;
    }

    .toast {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%) translateY(18px);
      background: #1c1915;
      color: #f8efd9;
      border: 1.5px solid var(--punch-teal);
      padding: 9px 16px;
      border-radius: 5px;
      font-size: 0.8rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s, transform 0.2s;
      z-index: 80;
    }

    .toast.show {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }

    .hidden {
      display: none !important;
    }

    /* Responsive Collapse for Narrow Tablets & Mobile */
    @media (max-width: 720px) {
      body {
        justify-content: flex-start;
        padding: 10px 8px 36px;
      }
      .desk-blotter {
        padding: 10px 10px 14px;
        border-width: 4px;
      }
      .controls-split-grid,
      .bonus-questions-grid {
        grid-template-columns: 1fr;
        gap: 10px;
      }
      .stats-4-grid,
      .summary-kpis {
        grid-template-columns: repeat(2, 1fr);
      }
      .share-actions {
        grid-template-columns: 1fr;
      }
      .share-preview {
        grid-column: span 1;
      }
      .column-ruler span:nth-child(odd),
      .column-ruler-bottom span:nth-child(odd) {
        visibility: hidden;
      }
    }

    @media (max-width: 460px) {
      .item-dossier {
        grid-template-columns: 74px 1fr;
        padding: 10px;
        gap: 10px;
      }
      .specimen-frame {
        width: 74px;
        height: 74px;
      }
      .benchmark-headline {
        font-size: 1.05rem;
      }
      .stats-4-grid {
        grid-template-columns: 1fr;
      }
      .round-pip {
        font-size: 0.6rem;
        padding: 4px 2px;
      }
      .stamp-ribbon {
        font-size: 0.52rem;
        letter-spacing: 0.02em;
      }
      .card-perforation {
        padding-left: 38px;
      }
    }
  </style>
</head>
<body>
  <div class="desk-blotter">
    <div class="app-shell">
      <!-- Top Steel Timeclock Header -->
      <header class="topbar">
        <div class="brand-group">
          <h1 class="brand-title">PUNCHCARD</h1>
          <span id="puzzleBadge" class="puzzle-tag">#1</span>
        </div>
        <div class="header-controls">
          <button id="rulesBtn" class="pill-btn" type="button" title="How to play PUNCHCARD">RULES</button>
          <button id="archiveBtn" class="pill-btn" type="button" title="Open Timecard Rack Archive of past shifts">
            ARCHIVE
          </button>
          <button id="statsBtn" class="pill-btn" type="button">STATS</button>
          <button id="sfxBtn" class="pill-btn" type="button" title="Toggle mechanical timeclock audio">SFX: ON</button>
        </div>
      </header>

      <!-- Main 80-Column Manila Timecard -->
      <main class="timecard">
        <div class="card-perforation">
          <span>IBM 5081 • TIME VALUE OF MONEY</span>
          <span>80-COL TIMECARD • US MEDIAN WAGE SERIES</span>
        </div>

        <div class="column-ruler" aria-hidden="true">
          <span>05</span><span>10</span><span>15</span><span>20</span><span>25</span><span>30</span><span>35</span><span>40</span><span>45</span><span>50</span><span>55</span><span>60</span><span>65</span><span>70</span><span>75</span><span>80</span>
        </div>

        <!-- Archive Context Strip -->
        <div id="archiveBanner" class="archive-banner hidden">
          <span id="archiveBannerText">ARCHIVE TIMECARD #1</span>
          <button id="returnTodayBtn" class="archive-return-link" type="button">TODAY'S SHIFT →</button>
        </div>

        <!-- Running Score, 1,000-Pt Win Bar, Round Pips, & Midnight UTC Timer -->
        <section class="shift-hud">
          <div class="hud-top-row">
            <div id="scoreReadout" class="score-readout">
              SCORE: <span id="runningScore" class="score-num">0</span> / 2,000
              <span id="winGoalBadge" class="win-goal-badge">1,000 TO WIN</span>
            </div>
            <div id="countdownTimer" class="countdown-readout">
              NEXT SHIFT (UTC): --:--:--
            </div>
          </div>
          <div class="quota-track" title="1,000 points required to win the shift">
            <div id="quotaFill" class="quota-fill"></div>
            <div class="quota-marker"></div>
          </div>
          <div id="roundTrack" class="round-track"></div>
        </section>

        <!-- Active Round View -->
        <section id="activeRoundView" class="card-body">
          <div class="benchmark-banner">
            <div id="roundKicker" class="benchmark-kicker">ROUND 1 OF 5 • 1 HOUR MEDIAN US LABOR BENCHMARK</div>
            <div id="benchmarkHeadline" class="benchmark-headline">
              OVER OR UNDER <span class="accent-target">1 WORK HOUR</span>?
            </div>
          </div>

          <!-- Specimen Dossier (Auto-resolved Photo Plate + SVG Fallback, NO Prices) -->
          <div class="item-dossier">
            <div class="specimen-frame" aria-hidden="true">
              <div id="specimenSvgFallback" class="specimen-svg-fallback"></div>
              <img id="specimenPhoto" class="specimen-photo" alt="" loading="eager" referrerpolicy="no-referrer" />
            </div>
            <div>
              <div class="item-meta-row">
                <span id="itemYear" class="year-stamp">1948</span>
                <span id="itemCategory" class="category-stamp">GROCERY</span>
              </div>
              <h2 id="itemTitle" class="item-title">Item Name</h2>
              <p id="itemDesc" class="item-desc">Item description</p>
            </div>
          </div>

          <!-- Pre-Guess Controls -->
          <div id="preGuessControls" class="controls-panel">
            <div class="controls-split-grid">
              <div class="control-group">
                <div class="control-label">
                  <span>1. Shift Estimate</span>
                </div>
                <div class="direction-grid">
                  <button id="btnUnder" class="choice-btn" type="button" data-dir="UNDER">
                    <span class="keycap-tag">U</span>
                    <span class="choice-main">▼ UNDER</span>
                    <span id="subUnder" class="choice-sub">Less than 1 hr</span>
                  </button>
                  <button id="btnOver" class="choice-btn" type="button" data-dir="OVER">
                    <span class="keycap-tag">O</span>
                    <span class="choice-main">▲ OVER</span>
                    <span id="subOver" class="choice-sub">More than 1 hr</span>
                  </button>
                </div>
              </div>

              <div class="control-group">
                <div class="control-label">
                  <span>2. Pay Rate Stamp</span>
                </div>
                <div class="stamp-key-grid">
                  <!-- Standard Pay 1x Stamp -->
                  <button id="stampBaseBtn" class="stamp-key selected" type="button" data-stamp="BASE">
                    <div class="stamp-ribbon">STANDARD PAY<span class="keycap-tag">1</span></div>
                    <div class="stamp-key-body">
                      <div class="stamp-mult-row">
                        <span class="mult-win">1x</span>
                        <span class="mult-slash">/</span>
                        <span class="mult-loss">0x</span>
                      </div>
                      <div class="stamp-pts-row">+200 / 0 PTS</div>
                      <div class="stamp-holes-footer">
                        <span class="mini-hole-dots"><i></i></span>
                        <span>UNLIMITED</span>
                      </div>
                    </div>
                  </button>

                  <!-- Overtime Pay +2x / -1x Stamp (Silver ribbon, 2 per shift) -->
                  <button id="stampSilverBtn" class="stamp-key" type="button" data-stamp="SILVER">
                    <div class="stamp-ribbon">OVERTIME PAY<span class="keycap-tag">2</span></div>
                    <div class="stamp-key-body">
                      <div class="stamp-mult-row">
                        <span class="mult-win">+2x</span>
                        <span class="mult-slash">/</span>
                        <span class="mult-loss">-1x</span>
                      </div>
                      <div class="stamp-pts-row">+400 / -200 PTS</div>
                      <div class="stamp-holes-footer">
                        <span class="mini-hole-dots"><i></i><i></i></span>
                        <span id="silverCountPill">2 LEFT</span>
                      </div>
                    </div>
                  </button>

                  <!-- Holiday Pay +3x / -1.5x Stamp (Gold ribbon, 1 per shift) -->
                  <button id="stampGoldBtn" class="stamp-key" type="button" data-stamp="GOLD">
                    <div class="stamp-ribbon">HOLIDAY PAY<span class="keycap-tag">3</span></div>
                    <div class="stamp-key-body">
                      <div class="stamp-mult-row">
                        <span class="mult-win">+3x</span>
                        <span class="mult-slash">/</span>
                        <span class="mult-loss">-1.5x</span>
                      </div>
                      <div class="stamp-pts-row">+600 / -300 PTS</div>
                      <div class="stamp-holes-footer">
                        <span class="mini-hole-dots"><i></i><i></i><i></i></span>
                        <span id="goldCountPill">1 LEFT</span>
                      </div>
                    </div>
                  </button>
                </div>
              </div>
            </div>

            <button id="punchSubmitBtn" class="punch-submit-btn" type="button" disabled>
              PUNCH IN
            </button>
          </div>

          <!-- Post-Guess 4-Stat Timecard Receipt with Federal Minimum Wage Lens -->
          <div id="receiptReveal" class="receipt-reveal hidden">
            <div class="receipt-top-strip">
              <div class="receipt-punch-cluster">
                <div id="receiptPunchHoles" class="punch-holes-row"></div>
                <div id="receiptPunchCaption" class="punch-cluster-caption">1 PUNCH • STANDARD PAY</div>
              </div>
              <div class="ink-stamp-box">
                <div id="inkStampImpression" class="ink-stamp-impression ink-hit-base">STANDARD PAY • 1x</div>
                <div id="verdictPoints" class="verdict-points positive">+200 PTS</div>
              </div>
            </div>

            <!-- Horizontal Visual Threshold Bar -->
            <div class="threshold-box">
              <div class="threshold-labels">
                <span>◄ UNDER BENCHMARK</span>
                <span id="thresholdCenterLabel">1 HR</span>
                <span>OVER BENCHMARK ►</span>
              </div>
              <div class="threshold-track">
                <div id="thresholdFill" class="threshold-fill under"></div>
                <div class="threshold-pin" title="Round Benchmark Line"></div>
              </div>
              <div id="thresholdCaption" class="threshold-caption">
                Landed at 0.5 hrs (48% UNDER benchmark)
              </div>
            </div>

            <!-- 4-Stat Timecard Grid (US Median Wage) -->
            <div class="stats-4-grid">
              <div class="stat-cell">
                <div id="stat1Label" class="stat-cell-label">Sticker Price in 1948</div>
                <div id="stat1Value" class="stat-cell-value">$0.69</div>
                <div id="stat1Sub" class="stat-cell-sub">Median wage: $1.33/hr</div>
              </div>
              <div class="stat-cell">
                <div id="stat2Label" class="stat-cell-label">Median Work in 1948</div>
                <div id="stat2Value" class="stat-cell-value">0.5 hrs</div>
                <div id="stat2Sub" class="stat-cell-sub">0.52 Hours → UNDER</div>
              </div>
              <div class="stat-cell">
                <div class="stat-cell-label">Equivalent Price Today</div>
                <div id="stat3Value" class="stat-cell-value">$7.49</div>
                <div id="stat3Sub" class="stat-cell-sub">2026 median wage: $32.40/hr</div>
              </div>
              <div class="stat-cell">
                <div class="stat-cell-label">Median Work Today</div>
                <div id="stat4Value" class="stat-cell-value">0.2 hrs</div>
                <div id="stat4Sub" class="stat-cell-sub">-55% labor time vs. 1948</div>
              </div>
            </div>

            <!-- Per-Round Federal Minimum Wage Comparison Strip -->
            <div class="min-wage-callout">
              <span class="min-wage-tag">FEDERAL MIN WAGE LENS</span>
              <span id="minWageCompareText">In 1948 ($0.40/hr): 1.7 hrs (73% OVER) • Today ($7.25/hr): 1.0 hr (-40%)</span>
            </div>

            <div id="contextNoteBox" class="context-note-box">
              Historical note goes here.
            </div>

            <button id="nextRoundBtn" class="punch-submit-btn" type="button">
              NEXT ROUND (2 OF 5) → [ENTER]
            </button>
          </div>
        </section>

        <!-- 2-Question Active Time-Price Bonus Audit View (with Explicit Reveal Step) -->
        <section id="bonusAuditView" class="card-body hidden">
          <div class="bonus-audit-header">
            <div id="bonusAuditKicker" class="bonus-audit-kicker">END-OF-SHIFT BONUS AUDIT • UP TO +200 PTS</div>
            <h2 id="bonusAuditTitle" class="bonus-audit-title">TIME-PRICE PREDICTION CHECK</h2>
          </div>

          <div class="bonus-questions-grid">
            <div class="bonus-q-card">
              <div class="bonus-q-header-row">
                <div class="bonus-q-label">
                  <span class="bonus-q-badge">+100 PTS</span>
                  Which item's median labor cost <strong>DROPPED</strong> the most by 2026?
                </div>
                <div id="bonusDropVerdict" class="audit-verdict-stamp hidden"></div>
              </div>
              <div id="bonusDropOptions" class="bonus-options-list"></div>
            </div>

            <div class="bonus-q-card">
              <div class="bonus-q-header-row">
                <div id="bonusSurgeLabel" class="bonus-q-label">
                  <span class="bonus-q-badge">+100 PTS</span>
                  Which item's median labor cost <strong>SURGED</strong> the most by 2026?
                </div>
                <div id="bonusSurgeVerdict" class="audit-verdict-stamp hidden"></div>
              </div>
              <div id="bonusSurgeOptions" class="bonus-options-list"></div>
            </div>
          </div>

          <button id="submitBonusAuditBtn" class="punch-submit-btn" type="button" disabled>
            SELECT BOTH ITEMS TO LOCK IN AUDIT
          </button>
        </section>

        <!-- End-of-Run Summary View -->
        <section id="summaryView" class="card-body hidden">
          <div class="summary-header">
            <div class="payout-rank-row">
              <div id="payoutAssetPill" class="payout-asset-pill tier-gold">PAYOUT TIER: 24K GOLD</div>
            </div>
            <div class="summary-score-big">
              <span id="finalScore">0</span> <span class="summary-score-max">/ 2,000</span>
            </div>
            <div id="summaryThresholdSub" class="summary-threshold-sub">
              1,000 pts required to win shift
            </div>
            <div class="summary-kpis">
              <div class="kpi-mini">
                <div id="kpiAccuracy" class="kpi-mini-val">0/5</div>
                <div class="kpi-mini-lbl">Round Hits</div>
              </div>
              <div class="kpi-mini">
                <div id="kpiBonusAudit" class="kpi-mini-val">+0</div>
                <div class="kpi-mini-lbl">Trend Audit</div>
              </div>
              <div class="kpi-mini">
                <div id="kpiHoliday" class="kpi-mini-val">—</div>
                <div class="kpi-mini-lbl">Holiday Pay</div>
              </div>
              <div class="kpi-mini">
                <div id="kpiStreak" class="kpi-mini-val">0</div>
                <div class="kpi-mini-lbl">Win Streak</div>
              </div>
            </div>
          </div>

          <!-- Shift Time-Price Trend Synthesis with Interactive Median vs. Minimum Wage Toggle -->
          <div id="trendSynthesisBanner" class="trend-synthesis-banner">
            <div class="trend-banner-top">
              <div class="trend-synthesis-title">SHIFT TIME-PRICE TREND (RELEASE YEAR VS. 2026)</div>
              <div class="summary-wage-switch" role="group" aria-label="Compare Median vs Minimum Wage">
                <button id="lensMedianBtn" class="summary-wage-btn active" type="button" data-lens="MEDIAN">
                  MEDIAN EARNER
                </button>
                <button id="lensMinimumBtn" class="summary-wage-btn" type="button" data-lens="MINIMUM">
                  FEDERAL MIN WAGE
                </button>
              </div>
            </div>
            <div id="trendSynthesisBody">Loading time-price comparison...</div>
          </div>

          <div id="recapList" class="recap-list"></div>

          <div class="share-actions">
            <button id="shareBtn" class="share-btn" type="button">
              SHARE TIMECARD
            </button>
            <button id="openRackFromSummaryBtn" class="secondary-action-btn" type="button">
              TIMECARD RACK ARCHIVE
            </button>
            <pre id="sharePreview" class="share-preview"></pre>
          </div>
        </section>

        <div class="column-ruler-bottom" aria-hidden="true">
          <span>05</span><span>10</span><span>15</span><span>20</span><span>25</span><span>30</span><span>35</span><span>40</span><span>45</span><span>50</span><span>55</span><span>60</span><span>65</span><span>70</span><span>75</span><span>80</span>
        </div>
      </main>
    </div>
  </div>

  <!-- Rules / How to Play Modal -->
  <div id="rulesModal" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="rulesModalTitle">
    <div class="modal-card">
      <div class="modal-header">
        <h2 id="rulesModalTitle" class="modal-title">HOW TO PUNCH IN</h2>
        <button id="closeRulesBtn" class="close-btn" type="button">ESC</button>
      </div>
      <div class="rules-list">
        <div class="rule-card">
          <div class="rule-card-title">1. Estimate Median US Labor Cost (No Sticker Prices)</div>
          <p>
            Each shift features 5 historical items across escalating labor benchmarks:
            <strong>1 Hour → 1 Day (8h) → 1 Week (40h) → 1 Month (173.3h) → 1 Year (2,080h)</strong>.
            Decide whether buying the item in its release year took <strong>UNDER</strong> or <strong>OVER</strong> that benchmark of median US work.
          </p>
        </div>

        <div class="rule-card">
          <div class="rule-card-title">2. Allocate Pay Rate Stamps &amp; Bonus Audit (1,000+ Pts to Win)</div>
          <p>
            Going 5/5 on Standard Pay (<strong>1,000 pts</strong>) wins the shift. Use shared Overtime/Holiday stamps to climb higher—and earn up to <strong>+200 pts</strong> on the 2-question Time-Price Audit after Round 5:
          </p>
          <table class="rule-stamp-table">
            <thead>
              <tr>
                <th>Stamp / Bonus</th>
                <th>Allowance</th>
                <th>Hit</th>
                <th>Miss</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Standard Pay</strong></td>
                <td>Unlimited</td>
                <td>+200 pts (1x)</td>
                <td>0 pts (0x)</td>
              </tr>
              <tr>
                <td><strong>Overtime Pay</strong></td>
                <td>2 per shift</td>
                <td>+400 pts (+2x)</td>
                <td>-200 pts (-1x)</td>
              </tr>
              <tr>
                <td><strong>Holiday Pay</strong></td>
                <td>1 per shift</td>
                <td>+600 pts (+3x)</td>
                <td>-300 pts (-1.5x)</td>
              </tr>
              <tr>
                <td><strong>Time-Price Audit</strong></td>
                <td>2 questions</td>
                <td>+100 pts each</td>
                <td>0 pts</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="rule-card">
          <div class="rule-card-title">3. Time-Value-of-Money Payout Tiers &amp; Minimum Wage Lens</div>
          <p>
            Higher scores pay out in stronger inflation-resistant assets:
            <strong>Company Scrip</strong> (&lt;1,000) → <strong>Paper Dollar</strong> (1,000+) →
            <strong>Silver Bullion</strong> (1,300+) → <strong>24k Gold</strong> (1,600+) →
            <strong>Sovereign Gold</strong> (1,900+). Each receipt and the final scorecard also compare <strong>Federal Minimum Wage</strong> work hours.
          </p>
        </div>
      </div>
      <button id="startShiftBtn" class="punch-submit-btn" type="button">
        CLOCK IN &amp; PLAY
      </button>
    </div>
  </div>

  <!-- Timecard Rack Archive Modal -->
  <div id="archiveModal" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="archiveModalTitle">
    <div class="modal-card">
      <div class="modal-header">
        <h2 id="archiveModalTitle" class="modal-title">TIMECARD RACK ARCHIVE</h2>
        <button id="closeArchiveBtn" class="close-btn" type="button">ESC</button>
      </div>
      <div id="rackList" class="rack-scroll"></div>
      <p class="modal-footnote">
        Select any past shift to punch in or review your completed receipt. Archived shifts save separately and do not affect your live Daily Win Streak.
      </p>
    </div>
  </div>

  <!-- Lifetime Stats Modal -->
  <div id="statsModal" class="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="statsModalTitle">
    <div class="modal-card">
      <div class="modal-header">
        <h2 id="statsModalTitle" class="modal-title">LIFETIME PUNCHCARD STATS</h2>
        <button id="closeStatsBtn" class="close-btn" type="button">ESC</button>
      </div>
      <div class="lifetime-grid">
        <div class="lifetime-box">
          <div id="statGamesPlayed" class="lifetime-val">0</div>
          <div class="lifetime-lbl">Daily Shifts Played</div>
        </div>
        <div class="lifetime-box">
          <div id="statWinStreak" class="lifetime-val">0</div>
          <div class="lifetime-lbl">Current Win Streak</div>
        </div>
        <div class="lifetime-box">
          <div id="statAvgScore" class="lifetime-val">0</div>
          <div class="lifetime-lbl">Average Score</div>
        </div>
        <div class="lifetime-box">
          <div id="statOuAccuracy" class="lifetime-val">0%</div>
          <div class="lifetime-lbl">Over/Under Accuracy</div>
        </div>
        <div class="lifetime-box" style="grid-column: span 2;">
          <div id="stat3xHitRate" class="lifetime-val">—</div>
          <div class="lifetime-lbl">Holiday Pay (+3x) Hit Rate</div>
        </div>
      </div>
      <p class="modal-footnote">
        Daily shifts reset at 00:00 UTC. A live shift counts as a win when your final score reaches at least 1,000 points.
      </p>
    </div>
  </div>

  <div id="toast" class="toast" role="status" aria-live="polite"></div>

  <script>
    // =========================================================================
    // EMBEDDED BUILD DATA FROM build_punchcard.py
    // =========================================================================
    const GAME_DATA = __EMBEDDED_DATA_JSON__;

    const WIN_SCORE_THRESHOLD = 1000;
    const MAX_SHIFT_SCORE = 2000;

    const STAMPS = {
      BASE: {
        type: "BASE",
        name: "STANDARD PAY",
        shortName: "Standard",
        holes: 1,
        winMult: "1x",
        lossMult: "0x",
        win: 200,
        loss: 0,
        allowance: Infinity
      },
      SILVER: {
        type: "SILVER",
        name: "OVERTIME PAY",
        shortName: "Overtime",
        holes: 2,
        winMult: "+2x",
        lossMult: "-1x",
        win: 400,
        loss: -200,
        allowance: 2
      },
      GOLD: {
        type: "GOLD",
        name: "HOLIDAY PAY",
        shortName: "Holiday",
        holes: 3,
        winMult: "+3x",
        lossMult: "-1.5x",
        win: 600,
        loss: -300,
        allowance: 1
      }
    };

    function getPayoutTier(score) {
      if (score >= 1900) {
        return {
          code: "SOVEREIGN GOLD",
          pillText: "PAYOUT: SOVEREIGN GOLD • MINT BULLION",
          cssClass: "tier-sovereign",
          desc: "Peak purchasing power preserved across decades"
        };
      }
      if (score >= 1600) {
        return {
          code: "24K GOLD",
          pillText: "PAYOUT: 24K GOLD • STORE OF VALUE",
          cssClass: "tier-gold",
          desc: "Inflation-proof gold standard shift"
        };
      }
      if (score >= 1300) {
        return {
          code: "SILVER BULLION",
          pillText: "PAYOUT: SILVER BULLION • HARD ASSET",
          cssClass: "tier-silver",
          desc: "Strong shift hedged against currency erosion"
        };
      }
      if (score >= WIN_SCORE_THRESHOLD) {
        return {
          code: "PAPER DOLLAR",
          pillText: "PAYOUT: PAPER DOLLAR • QUOTA MET",
          cssClass: "tier-paper",
          desc: "Shift quota met (1,000+ pts)"
        };
      }
      return {
        code: "COMPANY SCRIP",
        pillText: "PAYOUT: COMPANY SCRIP • SHORT SHIFT",
        cssClass: "tier-scrip",
        desc: "Under 1,000-pt quota"
      };
    }

    const CATEGORY_META = {
      grocery: {
        label: "GROCERY & DINING",
        svg: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 24h40l-4 28H16L12 24z"/>
          <path d="M22 24V16a10 10 0 0 1 20 0v8"/>
          <line x1="24" y1="32" x2="24" y2="44"/>
          <line x1="32" y1="32" x2="32" y2="44"/>
          <line x1="40" y1="32" x2="40" y2="44"/>
        </svg>`
      },
      electronics: {
        label: "ELECTRONICS & MEDIA",
        svg: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="10" y="18" width="44" height="32" rx="4"/>
          <line x1="22" y1="18" x2="14" y2="8"/>
          <line x1="42" y1="18" x2="50" y2="8"/>
          <circle cx="24" cy="34" r="7"/>
          <line x1="38" y1="28" x2="46" y2="28"/>
          <line x1="38" y1="34" x2="46" y2="34"/>
          <line x1="38" y1="40" x2="46" y2="40"/>
        </svg>`
      },
      appliance: {
        label: "HOME APPLIANCE",
        svg: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="14" y="10" width="36" height="44" rx="3"/>
          <line x1="14" y1="24" x2="50" y2="24"/>
          <circle cx="22" cy="17" r="2"/>
          <circle cx="30" cy="17" r="2"/>
          <circle cx="32" cy="39" r="9"/>
          <path d="M27 39c2-3 8-3 10 0"/>
        </svg>`
      },
      vehicle: {
        label: "AUTOMOTIVE & FUEL",
        svg: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 36l5-14h30l5 14"/>
          <rect x="8" y="36" width="48" height="12" rx="3"/>
          <circle cx="18" cy="48" r="5" fill="#f8efd9"/>
          <circle cx="46" cy="48" r="5" fill="#f8efd9"/>
          <line x1="22" y1="28" x2="42" y2="28"/>
        </svg>`
      },
      housing_education: {
        label: "HOUSING & TUITION",
        svg: `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M8 30L32 12l24 18"/>
          <path d="M16 26v26h32V26"/>
          <rect x="27" y="36" width="10" height="16"/>
          <rect x="20" y="31" width="5" height="5"/>
          <rect x="39" y="31" width="5" height="5"/>
        </svg>`
      }
    };

    const LAUNCH_UTC_MS = Date.parse(GAME_DATA.launch_date + "T00:00:00Z");
    const STORAGE_KEYS = {
      STATS: "punchcard_lifetime_stats_v7",
      SHIFT_PREFIX: "punchcard_shift_v7_",
      RULES_SEEN: "punchcard_rules_seen_v3",
      SFX: "punchcard_sfx_enabled_v1"
    };

    // =========================================================================
    // ZERO-MAINTENANCE RUNTIME IMAGE LOADER (WITH CORE-NOUN FALLBACK & SVG)
    // =========================================================================
    const runtimeImageCache = {};
    let activeImageRequestToken = 0;

    function buildClientSearchQueries(item) {
      let q = item.name.replace(/\([^)]*\)/g, "").trim();
      q = q.replace(
        /^(1\s+lb|1\s+Dozen|5-Gallon\s+Fill-Up\s+of|12-Inch|17-Inch|12\s+cu\.\s*ft\.|Set\s+of\s+\d+|1-Week|1-Year|3-Credit|4\s+Years\s+of|Brand-New|Median-Priced)\s+/i,
        ""
      ).trim();

      const queries = [];
      if (item.category === "vehicle" && /(ford|chevrolet|honda)/i.test(q)) {
        queries.push(`${item.year} ${q}`);
      }
      queries.push(q);

      const words = q.split(/\s+/).filter((w) => !/^(of|and|&|a|the|in|at)$/i.test(w));
      if (words.length > 2) {
        const shortQ = words.slice(-2).join(" ");
        if (shortQ.toLowerCase() !== q.toLowerCase()) {
          queries.push(shortQ);
        }
      }
      return queries;
    }

    async function querySingleWikimediaTerm(query) {
      if (query in runtimeImageCache) {
        return runtimeImageCache[query];
      }
      const params = new URLSearchParams({
        action: "query",
        generator: "search",
        gsrnamespace: "6",
        gsrsearch: `filetype:bitmap ${query}`,
        gsrlimit: "5",
        prop: "imageinfo",
        iiprop: "url",
        iiurlwidth: "320",
        format: "json",
        origin: "*"
      });
      try {
        const res = await fetch(`https://commons.wikimedia.org/w/api.php?${params.toString()}`);
        if (!res.ok) return null;
        const data = await res.json();
        const pages = Object.values((data.query && data.query.pages) || {}).sort(
          (a, b) => (a.index || 999) - (b.index || 999)
        );
        for (const page of pages) {
          const t = (page.title || "").toLowerCase();
          if (t.includes("icon") || t.includes("logo") || t.includes("flag_of")) continue;
          const info = page.imageinfo && page.imageinfo[0];
          if (info && (info.thumburl || info.url)) {
            const url = info.thumburl || info.url;
            runtimeImageCache[query] = url;
            return url;
          }
        }
      } catch (e) {
        // Offline or blocked: gracefully retain SVG fallback
      }
      runtimeImageCache[query] = null;
      return null;
    }

    async function fetchLiveWikimediaThumb(item) {
      const queries = buildClientSearchQueries(item);
      for (const q of queries) {
        const url = await querySingleWikimediaTerm(q);
        if (url) return url;
      }
      return null;
    }

    function renderSpecimenVisual(item) {
      const catInfo = CATEGORY_META[item.category] || CATEGORY_META.electronics;
      const svgEl = document.getElementById("specimenSvgFallback");
      const imgEl = document.getElementById("specimenPhoto");

      svgEl.innerHTML = catInfo.svg;
      imgEl.classList.remove("loaded");
      imgEl.removeAttribute("src");

      const reqToken = ++activeImageRequestToken;

      const applyUrl = (url) => {
        if (!url || reqToken !== activeImageRequestToken) return;
        imgEl.onload = () => {
          if (reqToken === activeImageRequestToken) {
            imgEl.classList.add("loaded");
          }
        };
        imgEl.onerror = () => {
          if (reqToken === activeImageRequestToken) {
            imgEl.classList.remove("loaded");
          }
        };
        imgEl.src = url;
      };

      if (item.image_url) {
        applyUrl(item.image_url);
      } else {
        fetchLiveWikimediaThumb(item).then((url) => {
          if (url) {
            item.image_url = url;
            applyUrl(url);
          }
        });
      }
    }

    // =========================================================================
    // DETERMINISTIC PRNG & UTC CALENDAR HELPERS
    // =========================================================================
    function formatDateKeyFromUTC(dateObj) {
      const y = dateObj.getUTCFullYear();
      const m = String(dateObj.getUTCMonth() + 1).padStart(2, "0");
      const d = String(dateObj.getUTCDate()).padStart(2, "0");
      return `${y}-${m}-${d}`;
    }

    function formatHumanDateUTC(dateKey) {
      const dt = new Date(Date.parse(dateKey + "T00:00:00Z"));
      return dt.toLocaleDateString("en-US", {
        timeZone: "UTC",
        month: "short",
        day: "numeric",
        year: "numeric"
      });
    }

    function getShiftMetaForDateKey(dateKey) {
      const midnightMs = Date.parse(dateKey + "T00:00:00Z");
      const dayIndex = Math.max(0, Math.floor((midnightMs - LAUNCH_UTC_MS) / 86400000));
      return {
        dateKey,
        dayIndex,
        puzzleNumber: dayIndex + 1,
        midnightMs
      };
    }

    function getTodayUTCInfo(now = new Date()) {
      const dateKey = formatDateKeyFromUTC(now);
      const meta = getShiftMetaForDateKey(dateKey);
      return {
        ...meta,
        nextMidnightMs: meta.midnightMs + 86400000
      };
    }

    function fnv1aHash(str) {
      let h = 0x811c9dc5;
      for (let i = 0; i < str.length; i++) {
        h ^= str.charCodeAt(i);
        h = Math.imul(h, 0x01000193);
      }
      return h >>> 0;
    }

    function mulberry32(seed) {
      let a = seed >>> 0;
      return function () {
        a |= 0;
        a = (a + 0x6d2b79f5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };
    }

    function seededShuffle(arr, seedStr) {
      const copy = arr.slice();
      const rand = mulberry32(fnv1aHash(seedStr));
      for (let i = copy.length - 1; i > 0; i--) {
        const j = Math.floor(rand() * (i + 1));
        [copy[i], copy[j]] = [copy[j], copy[i]];
      }
      return copy;
    }

    function selectItemsForDayIndex(dayIndex) {
      return GAME_DATA.benchmarks.map((b) => {
        const tierItems = GAME_DATA.items
          .filter((item) => item.tier === b.round)
          .sort((a, c) => a.id.localeCompare(c.id));
        const n = tierItems.length;
        const cycle = Math.floor(dayIndex / n);
        const offset = dayIndex % n;
        const perm = seededShuffle(tierItems, `punchcard:tier:${b.round}:cycle:${cycle}`);
        return perm[offset];
      });
    }

    // =========================================================================
    // MECHANICAL TIMECLOCK SOUND EFFECTS (WEB AUDIO API)
    // =========================================================================
    let audioCtx = null;
    let sfxEnabled = localStorage.getItem(STORAGE_KEYS.SFX) !== "false";

    function playTone(type) {
      if (!sfxEnabled) return;
      try {
        if (!audioCtx) {
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === "suspended") {
          audioCtx.resume();
        }
        const now = audioCtx.currentTime;
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);

        if (type === "tick") {
          osc.type = "triangle";
          osc.frequency.setValueAtTime(520, now);
          osc.frequency.exponentialRampToValueAtTime(180, now + 0.045);
          gain.gain.setValueAtTime(0.11, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.045);
          osc.start(now);
          osc.stop(now + 0.05);
        } else if (type === "stamp-hit") {
          osc.type = "square";
          osc.frequency.setValueAtTime(150, now);
          osc.frequency.setValueAtTime(520, now + 0.055);
          gain.gain.setValueAtTime(0.14, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.24);
          osc.start(now);
          osc.stop(now + 0.25);
        } else if (type === "stamp-miss") {
          osc.type = "sawtooth";
          osc.frequency.setValueAtTime(165, now);
          osc.frequency.linearRampToValueAtTime(95, now + 0.25);
          gain.gain.setValueAtTime(0.13, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.26);
          osc.start(now);
          osc.stop(now + 0.27);
        }
      } catch (e) {
        // Ignore audio errors if blocked
      }
    }

    // =========================================================================
    // PERSISTENCE & LIFETIME STATS (1,000-PT WIN THRESHOLD)
    // =========================================================================
    function loadLifetimeStats() {
      const defaults = {
        gamesPlayed: 0,
        winStreak: 0,
        maxStreak: 0,
        lastCompletedDateKey: null,
        totalScoreSum: 0,
        totalRoundsPlayed: 0,
        totalRoundsCorrect: 0,
        goldAttempts: 0,
        goldHits: 0
      };
      try {
        const raw = localStorage.getItem(STORAGE_KEYS.STATS);
        return raw ? { ...defaults, ...JSON.parse(raw) } : defaults;
      } catch (e) {
        return defaults;
      }
    }

    function saveLifetimeStats(stats) {
      try {
        localStorage.setItem(STORAGE_KEYS.STATS, JSON.stringify(stats));
      } catch (e) {
        // Ignore storage errors
      }
    }

    function recordLiveDailyCompletion(dateKey, runState) {
      const stats = loadLifetimeStats();
      if (stats.lastCompletedDateKey === dateKey) {
        return stats;
      }

      const finalScore = Math.max(0, runState.rawScore);
      const hits = runState.history.filter((h) => h.isCorrect).length;
      const isWin = finalScore >= WIN_SCORE_THRESHOLD;

      const prevDate = new Date(Date.parse(dateKey + "T00:00:00Z") - 86400000);
      const prevKey = formatDateKeyFromUTC(prevDate);

      stats.gamesPlayed += 1;
      if (isWin) {
        stats.winStreak = stats.lastCompletedDateKey === prevKey ? stats.winStreak + 1 : 1;
        stats.maxStreak = Math.max(stats.maxStreak, stats.winStreak);
      } else {
        stats.winStreak = 0;
      }

      stats.lastCompletedDateKey = dateKey;
      stats.totalScoreSum += finalScore;
      stats.totalRoundsPlayed += runState.history.length;
      stats.totalRoundsCorrect += hits;

      for (const h of runState.history) {
        if (h.stampType === "GOLD") {
          stats.goldAttempts += 1;
          if (h.isCorrect) stats.goldHits += 1;
        }
      }

      saveLifetimeStats(stats);
      return stats;
    }

    function shiftStorageKey(dateKey) {
      return `${STORAGE_KEYS.SHIFT_PREFIX}${dateKey}`;
    }

    function loadShiftProgress(dateKey) {
      try {
        const raw = localStorage.getItem(shiftStorageKey(dateKey));
        return raw ? JSON.parse(raw) : null;
      } catch (e) {
        return null;
      }
    }

    function saveShiftProgress(dateKey, runState) {
      try {
        localStorage.setItem(shiftStorageKey(dateKey), JSON.stringify(runState));
      } catch (e) {
        // Ignore storage errors
      }
    }

    // =========================================================================
    // GAME STATE & TIME-PRICE AUDIT HELPERS
    // =========================================================================
    let state = {
      dateKey: "",
      todayDateKey: "",
      isArchive: false,
      puzzleNumber: 1,
      items: [],
      roundIndex: 0,
      rawScore: 0,
      selectedDirection: null, // "OVER" | "UNDER" | null
      selectedStamp: "BASE",   // "BASE" | "SILVER" | "GOLD"
      revealed: false,
      bonusPhase: false,
      bonusRevealed: false,
      bonusDropGuessId: null,
      bonusSurgeGuessId: null,
      bonusResult: null,       // { dropCorrect, surgeCorrect, pointsEarned, dropItemId, surgeItemId }
      completed: false,
      summaryLens: "MEDIAN",   // "MEDIAN" | "MINIMUM" (Final scorecard lens only — zero replay)
      history: []
    };

    function getRemainingStamps() {
      const silverUsed = state.history.filter((h) => h.stampType === "SILVER").length;
      const goldUsed = state.history.filter((h) => h.stampType === "GOLD").length;
      return {
        SILVER: Math.max(0, STAMPS.SILVER.allowance - silverUsed),
        GOLD: Math.max(0, STAMPS.GOLD.allowance - goldUsed)
      };
    }

    function getShiftExtremes(items) {
      const scored = items.map((item) => {
        const exactPctChange = ((item.hours_now - item.hours_then) / item.hours_then) * 100;
        return { item, exactPctChange };
      });
      const sorted = scored.slice().sort((a, b) => a.exactPctChange - b.exactPctChange);
      const dropWinner = sorted[0];
      const surgeWinner = sorted[sorted.length - 1];
      return {
        dropItemId: dropWinner.item.id,
        surgeItemId: surgeWinner.item.id,
        hasPositiveSurge: surgeWinner.exactPctChange > 0
      };
    }

    function formatCurrency(val) {
      if (val >= 1000) {
        return "$" + val.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
      }
      return "$" + val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function formatHours(hrs) {
      if (hrs >= 100) {
        return hrs.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " hrs";
      }
      const rounded = Number(hrs.toFixed(1));
      return `${rounded.toFixed(1)} ${rounded === 1.0 ? "hr" : "hrs"}`;
    }

    function formatBenchmarkCount(val) {
      return Number.isInteger(val) ? String(val) : val.toLocaleString("en-US");
    }

    function formatBenchmarkUnits(hours, benchmark) {
      const units = hours / benchmark.hours;
      const unitName = Math.abs(units - 1.0) < 0.05 ? benchmark.unit_singular : benchmark.unit_plural;
      return `${units.toFixed(2)} ${unitName}`;
    }

    function showToast(msg) {
      const toast = document.getElementById("toast");
      toast.textContent = msg;
      toast.classList.add("show");
      clearTimeout(toast._timer);
      toast._timer = setTimeout(() => toast.classList.remove("show"), 2400);
    }

    // =========================================================================
    // LOAD SHIFT (TODAY OR ARCHIVE DATE)
    // =========================================================================
    function loadShiftByDateKey(targetDateKey) {
      const todayInfo = getTodayUTCInfo();
      const shiftMeta = getShiftMetaForDateKey(targetDateKey);
      const shiftItems = selectItemsForDayIndex(shiftMeta.dayIndex);
      const saved = loadShiftProgress(targetDateKey);

      state = {
        dateKey: targetDateKey,
        todayDateKey: todayInfo.dateKey,
        isArchive: targetDateKey !== todayInfo.dateKey,
        puzzleNumber: shiftMeta.puzzleNumber,
        items: shiftItems,
        roundIndex: saved ? saved.roundIndex : 0,
        rawScore: saved ? saved.rawScore : 0,
        selectedDirection: null,
        selectedStamp: "BASE",
        revealed: saved ? Boolean(saved.revealed && !saved.bonusPhase && !saved.completed) : false,
        bonusPhase: saved ? Boolean(saved.bonusPhase && !saved.completed) : false,
        bonusRevealed: saved ? Boolean(saved.bonusRevealed && saved.bonusPhase && !saved.completed) : false,
        bonusDropGuessId: saved ? saved.bonusDropGuessId || null : null,
        bonusSurgeGuessId: saved ? saved.bonusSurgeGuessId || null : null,
        bonusResult: saved ? saved.bonusResult || null : null,
        completed: saved ? Boolean(saved.completed) : false,
        summaryLens: "MEDIAN",
        history: saved ? saved.history : []
      };

      renderAll();
    }

    // =========================================================================
    // GAMEPLAY ACTIONS
    // =========================================================================
    function selectDirection(dir) {
      if (state.revealed || state.bonusPhase || state.completed) return;
      state.selectedDirection = dir;
      playTone("tick");
      renderControls();
    }

    function selectStamp(stampType) {
      if (state.revealed || state.bonusPhase || state.completed) return;
      const rem = getRemainingStamps();
      if (stampType === "SILVER" && rem.SILVER <= 0) return;
      if (stampType === "GOLD" && rem.GOLD <= 0) return;

      state.selectedStamp = stampType;
      playTone("tick");
      renderControls();
    }

    function submitGuess() {
      if (!state.selectedDirection || state.revealed || state.bonusPhase || state.completed) return;

      const item = state.items[state.roundIndex];
      const benchmark = GAME_DATA.benchmarks[state.roundIndex];
      const isCorrect = state.selectedDirection === item.direction;
      const stampDef = STAMPS[state.selectedStamp];
      const delta = isCorrect ? stampDef.win : stampDef.loss;

      state.rawScore += delta;
      state.revealed = true;

      const record = {
        round: benchmark.round,
        shortLabel: benchmark.short_label,
        benchmarkTitle: benchmark.title,
        benchmarkHours: benchmark.hours,
        item,
        guess: state.selectedDirection,
        stampType: stampDef.type,
        stampName: stampDef.name,
        shortName: stampDef.shortName,
        holes: stampDef.holes,
        multApplied: isCorrect ? stampDef.winMult : stampDef.lossMult,
        isCorrect,
        delta,
        runningScore: Math.max(0, state.rawScore)
      };

      state.history.push(record);
      playTone(isCorrect ? "stamp-hit" : "stamp-miss");
      saveShiftProgress(state.dateKey, state);

      renderAll();
    }

    function advanceRound() {
      if (!state.revealed) return;
      playTone("tick");

      if (state.roundIndex < 4) {
        state.roundIndex += 1;
        state.selectedDirection = null;
        state.selectedStamp = "BASE";
        state.revealed = false;
        saveShiftProgress(state.dateKey, state);
      } else {
        state.revealed = false;
        state.bonusPhase = true;
        state.bonusRevealed = false;
        saveShiftProgress(state.dateKey, state);
      }

      renderAll();
    }

    function selectBonusOption(questionType, itemId) {
      if (!state.bonusPhase || state.bonusRevealed || state.completed) return;
      playTone("tick");
      if (questionType === "DROP") {
        state.bonusDropGuessId = itemId;
      } else {
        state.bonusSurgeGuessId = itemId;
      }
      renderBonusAudit();
    }

    function handleBonusAuditAction() {
      if (!state.bonusPhase || state.completed) return;

      // Step 1: Lock in answers and reveal all 5 swings + verdicts
      if (!state.bonusRevealed) {
        if (!state.bonusDropGuessId || !state.bonusSurgeGuessId) return;

        const extremes = getShiftExtremes(state.items);
        const dropCorrect = state.bonusDropGuessId === extremes.dropItemId;
        const surgeCorrect = state.bonusSurgeGuessId === extremes.surgeItemId;
        const pointsEarned = (dropCorrect ? 100 : 0) + (surgeCorrect ? 100 : 0);

        state.rawScore += pointsEarned;
        state.bonusResult = {
          dropCorrect,
          surgeCorrect,
          pointsEarned,
          dropItemId: extremes.dropItemId,
          surgeItemId: extremes.surgeItemId
        };
        state.bonusRevealed = true;

        playTone(pointsEarned > 0 ? "stamp-hit" : "stamp-miss");
        saveShiftProgress(state.dateKey, state);

        if (!state.isArchive) {
          recordLiveDailyCompletion(state.dateKey, state);
        }

        renderAll();
        return;
      }

      // Step 2: Explicitly advance from Audit reveal to Final Timecard
      playTone("tick");
      state.bonusPhase = false;
      state.bonusRevealed = false;
      state.completed = true;
      saveShiftProgress(state.dateKey, state);
      renderAll();
    }

    // =========================================================================
    // RENDERING
    // =========================================================================
    function renderAll() {
      const puzzleBadge = document.getElementById("puzzleBadge");
      const archiveBtn = document.getElementById("archiveBtn");
      const archiveBanner = document.getElementById("archiveBanner");

      puzzleBadge.textContent = `#${state.puzzleNumber}`;
      if (state.isArchive) {
        archiveBtn.classList.add("archive-active");
        archiveBanner.classList.remove("hidden");
        document.getElementById("archiveBannerText").textContent =
          `ARCHIVE SHIFT #${state.puzzleNumber} • ${formatHumanDateUTC(state.dateKey)}`;
      } else {
        archiveBtn.classList.remove("archive-active");
        archiveBanner.classList.add("hidden");
      }

      const clampedScore = Math.max(0, state.rawScore);
      const clearedWinBar = clampedScore >= WIN_SCORE_THRESHOLD;

      document.getElementById("runningScore").textContent = clampedScore.toLocaleString("en-US");
      document.getElementById("scoreReadout").classList.toggle("cleared", clearedWinBar);

      const goalBadge = document.getElementById("winGoalBadge");
      goalBadge.textContent = clearedWinBar ? "1,000+ WIN ✓" : "1,000 TO WIN";
      goalBadge.classList.toggle("cleared", clearedWinBar);

      const quotaPct = Math.min(100, (clampedScore / MAX_SHIFT_SCORE) * 100);
      const quotaFill = document.getElementById("quotaFill");
      quotaFill.style.width = `${quotaPct.toFixed(1)}%`;
      quotaFill.classList.toggle("cleared", clearedWinBar);

      const track = document.getElementById("roundTrack");
      track.innerHTML = GAME_DATA.benchmarks
        .map((b, idx) => {
          const hist = state.history[idx];
          let cls = "round-pip";
          let statusIcon = "";
          if (hist) {
            cls += hist.isCorrect ? " hit" : " miss";
            statusIcon = hist.isCorrect ? " ✓" : " ✕";
          } else if (!state.completed && !state.bonusPhase && idx === state.roundIndex) {
            cls += " active";
          }
          return `<div class="${cls}">R${b.round}: ${b.title}${statusIcon}</div>`;
        })
        .join("");

      const activeView = document.getElementById("activeRoundView");
      const bonusView = document.getElementById("bonusAuditView");
      const summaryView = document.getElementById("summaryView");

      if (state.completed) {
        activeView.classList.add("hidden");
        bonusView.classList.add("hidden");
        summaryView.classList.remove("hidden");
        renderSummary();
        return;
      }

      if (state.bonusPhase) {
        activeView.classList.add("hidden");
        summaryView.classList.add("hidden");
        bonusView.classList.remove("hidden");
        renderBonusAudit();
        return;
      }

      bonusView.classList.add("hidden");
      summaryView.classList.add("hidden");
      activeView.classList.remove("hidden");

      const item = state.items[state.roundIndex];
      const benchmark = GAME_DATA.benchmarks[state.roundIndex];
      const hrWord = benchmark.hours === 1.0 ? "HOUR" : "HOURS";

      document.getElementById("roundKicker").textContent =
        `ROUND ${benchmark.round} OF 5 • ${formatBenchmarkCount(benchmark.hours)} ${hrWord} MEDIAN US LABOR BENCHMARK`;
      document.getElementById("benchmarkHeadline").innerHTML =
        `OVER OR UNDER <span class="accent-target">${benchmark.question_label}</span>?`;

      const catInfo = CATEGORY_META[item.category] || CATEGORY_META.electronics;
      renderSpecimenVisual(item);
      document.getElementById("itemYear").textContent = String(item.year);
      document.getElementById("itemCategory").textContent = catInfo.label;
      document.getElementById("itemTitle").textContent = item.name;
      document.getElementById("itemDesc").textContent = item.description;

      const subHrWord = benchmark.hours === 1.0 ? "hr" : "hrs";
      const subCount = formatBenchmarkCount(benchmark.hours);
      document.getElementById("subUnder").textContent = `Less than ${subCount} ${subHrWord}`;
      document.getElementById("subOver").textContent = `More than ${subCount} ${subHrWord}`;

      const preControls = document.getElementById("preGuessControls");
      const receiptReveal = document.getElementById("receiptReveal");

      if (!state.revealed) {
        preControls.classList.remove("hidden");
        receiptReveal.classList.add("hidden");
        renderControls();
      } else {
        preControls.classList.add("hidden");
        receiptReveal.classList.remove("hidden");
        renderReceipt();
      }
    }

    function renderControls() {
      const btnUnder = document.getElementById("btnUnder");
      const btnOver = document.getElementById("btnOver");
      btnUnder.classList.toggle("selected-under", state.selectedDirection === "UNDER");
      btnOver.classList.toggle("selected-over", state.selectedDirection === "OVER");

      const rem = getRemainingStamps();
      if (state.selectedStamp === "SILVER" && rem.SILVER <= 0) state.selectedStamp = "BASE";
      if (state.selectedStamp === "GOLD" && rem.GOLD <= 0) state.selectedStamp = "BASE";

      const baseBtn = document.getElementById("stampBaseBtn");
      const silverBtn = document.getElementById("stampSilverBtn");
      const goldBtn = document.getElementById("stampGoldBtn");

      baseBtn.classList.toggle("selected", state.selectedStamp === "BASE");
      silverBtn.classList.toggle("selected", state.selectedStamp === "SILVER");
      goldBtn.classList.toggle("selected", state.selectedStamp === "GOLD");

      silverBtn.disabled = rem.SILVER <= 0;
      goldBtn.disabled = rem.GOLD <= 0;

      document.getElementById("silverCountPill").textContent =
        rem.SILVER > 0 ? `${rem.SILVER} LEFT` : "SPENT";
      document.getElementById("goldCountPill").textContent =
        rem.GOLD > 0 ? `${rem.GOLD} LEFT` : "SPENT";

      const submitBtn = document.getElementById("punchSubmitBtn");
      if (!state.selectedDirection) {
        submitBtn.disabled = true;
        submitBtn.textContent = "PUNCH IN";
      } else {
        const st = STAMPS[state.selectedStamp];
        const stampLabel = st.type === "BASE" ? "STANDARD 1x" : `${st.name} ${st.winMult}`;
        submitBtn.disabled = false;
        submitBtn.textContent = `PUNCH IN: ${state.selectedDirection} (${stampLabel})`;
      }
    }

    function renderReceipt() {
      const record = state.history[state.history.length - 1];
      const item = record.item;
      const benchmark = GAME_DATA.benchmarks[state.roundIndex];

      const holesEl = document.getElementById("receiptPunchHoles");
      holesEl.innerHTML = Array.from({ length: record.holes })
        .map(() => `<span class="die-cut-hole" aria-hidden="true"></span>`)
        .join("");

      const holeWord = record.holes === 1 ? "PUNCH" : "PUNCHES";
      document.getElementById("receiptPunchCaption").textContent =
        `${record.holes} ${holeWord} • ${record.stampName}`;

      const stampEl = document.getElementById("inkStampImpression");
      stampEl.style.animation = "none";
      void stampEl.offsetWidth;
      stampEl.style.animation = "";

      if (record.isCorrect) {
        if (record.stampType === "GOLD") {
          stampEl.textContent = "HOLIDAY PAY • +3x";
          stampEl.className = "ink-stamp-impression ink-hit-gold";
        } else if (record.stampType === "SILVER") {
          stampEl.textContent = "OVERTIME PAY • +2x";
          stampEl.className = "ink-stamp-impression ink-hit-silver";
        } else {
          stampEl.textContent = "STANDARD PAY • 1x";
          stampEl.className = "ink-stamp-impression ink-hit-base";
        }
      } else {
        if (record.stampType === "BASE") {
          stampEl.textContent = "UNPAID PUNCH";
          stampEl.className = "ink-stamp-impression ink-miss-neutral";
        } else {
          stampEl.textContent = `DOCKED (${record.multApplied})`;
          stampEl.className = "ink-stamp-impression ink-miss-docked";
        }
      }

      const ptsEl = document.getElementById("verdictPoints");
      const sign = record.delta > 0 ? "+" : "";
      ptsEl.textContent = `${sign}${record.delta} PTS`;
      ptsEl.className =
        "verdict-points " +
        (record.delta > 0 ? "positive" : record.delta < 0 ? "negative" : "neutral");

      const hrWord = benchmark.hours === 1.0 ? "HR" : "HRS";
      document.getElementById("thresholdCenterLabel").textContent =
        `${formatBenchmarkCount(benchmark.hours)} ${hrWord}`;

      const logPos = 50 + (Math.log(item.ratio) / Math.log(2.8)) * 45;
      const clampedWidth = Math.max(6, Math.min(94, logPos));
      const fillEl = document.getElementById("thresholdFill");
      fillEl.className = "threshold-fill " + (item.direction === "UNDER" ? "under" : "over");
      fillEl.style.width = "0%";
      requestAnimationFrame(() => {
        fillEl.style.width = `${clampedWidth.toFixed(1)}%`;
      });

      document.getElementById("thresholdCaption").textContent =
        `Landed at ${formatHours(item.hours_then)} (${item.pct_diff}% ${item.direction} ${benchmark.question_label})`;

      document.getElementById("stat1Label").textContent = `Sticker Price in ${item.year}`;
      document.getElementById("stat1Value").textContent = formatCurrency(item.price_then);
      document.getElementById("stat1Sub").textContent = `Median wage: $${item.wage_then.toFixed(2)}/hr`;

      document.getElementById("stat2Label").textContent = `Median Work in ${item.year}`;
      document.getElementById("stat2Value").textContent = formatHours(item.hours_then);
      document.getElementById("stat2Sub").textContent =
        `${formatBenchmarkUnits(item.hours_then, benchmark)} → ${item.direction}`;

      document.getElementById("stat3Value").textContent = formatCurrency(item.price_now);
      document.getElementById("stat3Sub").textContent = `2026 median wage: $${item.wage_today.toFixed(2)}/hr`;

      const laborChangePct = Math.round(((item.hours_now - item.hours_then) / item.hours_then) * 100);
      const laborSign = laborChangePct > 0 ? "+" : "";
      document.getElementById("stat4Value").textContent = formatHours(item.hours_now);
      document.getElementById("stat4Sub").textContent =
        `${laborSign}${laborChangePct}% labor time vs. ${item.year}`;

      // Per-Round Federal Minimum Wage Lens Comparison
      const minChangePct = Math.round(((item.min_hours_now - item.min_hours_then) / item.min_hours_then) * 100);
      const minSign = minChangePct > 0 ? "+" : "";
      document.getElementById("minWageCompareText").textContent =
        `In ${item.year} ($${item.min_wage_then.toFixed(2)}/hr): ${formatHours(item.min_hours_then)} ` +
        `(${item.min_pct_diff}% ${item.min_direction}) • Today ($${item.min_wage_today.toFixed(2)}/hr): ` +
        `${formatHours(item.min_hours_now)} (${minSign}${minChangePct}%)`;

      document.getElementById("contextNoteBox").textContent = item.context_note;

      const nextBtn = document.getElementById("nextRoundBtn");
      nextBtn.textContent =
        state.roundIndex < 4
          ? `NEXT ROUND (${state.roundIndex + 2} OF 5) → [ENTER]`
          : "TIME-PRICE BONUS AUDIT → [ENTER]";
    }

    function renderBonusOptionsForQuestion(containerEl, questionType, guessId, winnerId, isRevealed) {
      containerEl.innerHTML = state.items
        .map((item) => {
          const swingPct = Math.round(((item.hours_now - item.hours_then) / item.hours_then) * 100);
          const swingSign = swingPct > 0 ? "+" : "";
          const swingCls = swingPct < 0 ? "drop" : swingPct > 0 ? "surge" : "flat";

          let btnClass = "bonus-opt-btn";
          let rightHtml = `<span class="bonus-opt-year">${item.year}</span>`;

          if (!isRevealed) {
            if (guessId === item.id) btnClass += " selected";
          } else {
            const isWinner = item.id === winnerId;
            const isUserPick = item.id === guessId;
            let roleTagHtml = "";

            if (isWinner && isUserPick) {
              btnClass += " audit-correct";
              roleTagHtml = `<span class="audit-role-tag">✓ YOUR PICK</span>`;
            } else if (isWinner && !isUserPick) {
              btnClass += " audit-winner-reveal";
              roleTagHtml = `<span class="audit-role-tag">ACTUAL WINNER</span>`;
            } else if (!isWinner && isUserPick) {
              btnClass += " audit-wrong";
              roleTagHtml = `<span class="audit-role-tag">✕ YOUR PICK</span>`;
            } else {
              btnClass += " audit-neutral";
            }

            rightHtml = `
              <span class="bonus-opt-right">
                ${roleTagHtml}
                <span class="audit-swing-pill ${swingCls}">${swingSign}${swingPct}%</span>
              </span>
            `;
          }

          return `
            <button
              class="${btnClass}"
              type="button"
              data-q="${questionType}"
              data-id="${item.id}"
              ${isRevealed ? "disabled" : ""}
            >
              <span>${item.name}</span>
              ${rightHtml}
            </button>
          `;
        })
        .join("");
    }

    function renderBonusAudit() {
      const extremes = getShiftExtremes(state.items);
      const isRevealed = Boolean(state.bonusRevealed && state.bonusResult);

      const kickerEl = document.getElementById("bonusAuditKicker");
      const titleEl = document.getElementById("bonusAuditTitle");

      if (isRevealed) {
        const earned = state.bonusResult.pointsEarned;
        kickerEl.textContent = `AUDIT RECEIPT • +${earned} OF 200 BONUS PTS EARNED`;
        titleEl.textContent = "19XX → 2026 MEDIAN LABOR-COST SWINGS";
      } else {
        kickerEl.textContent = "END-OF-SHIFT BONUS AUDIT • UP TO +200 PTS";
        titleEl.textContent = "TIME-PRICE PREDICTION CHECK";
      }

      const surgeLabelEl = document.getElementById("bonusSurgeLabel");
      if (extremes.hasPositiveSurge) {
        surgeLabelEl.innerHTML =
          `<span class="bonus-q-badge">+100 PTS</span> Which item's median labor cost <strong>SURGED</strong> the most by 2026?`;
      } else {
        surgeLabelEl.innerHTML =
          `<span class="bonus-q-badge">+100 PTS</span> Which item's median labor cost <strong>HELD FIRMEST</strong> (dropped least) by 2026?`;
      }

      const dropVerdictEl = document.getElementById("bonusDropVerdict");
      const surgeVerdictEl = document.getElementById("bonusSurgeVerdict");

      if (isRevealed) {
        dropVerdictEl.classList.remove("hidden");
        if (state.bonusResult.dropCorrect) {
          dropVerdictEl.textContent = "✓ CORRECT (+100 PTS)";
          dropVerdictEl.className = "audit-verdict-stamp hit";
        } else {
          dropVerdictEl.textContent = "✕ MISSED (0 PTS)";
          dropVerdictEl.className = "audit-verdict-stamp miss";
        }

        surgeVerdictEl.classList.remove("hidden");
        if (state.bonusResult.surgeCorrect) {
          surgeVerdictEl.textContent = "✓ CORRECT (+100 PTS)";
          surgeVerdictEl.className = "audit-verdict-stamp hit";
        } else {
          surgeVerdictEl.textContent = "✕ MISSED (0 PTS)";
          surgeVerdictEl.className = "audit-verdict-stamp miss";
        }
      } else {
        dropVerdictEl.classList.add("hidden");
        surgeVerdictEl.classList.add("hidden");
      }

      const dropList = document.getElementById("bonusDropOptions");
      const surgeList = document.getElementById("bonusSurgeOptions");

      renderBonusOptionsForQuestion(
        dropList,
        "DROP",
        state.bonusDropGuessId,
        extremes.dropItemId,
        isRevealed
      );
      renderBonusOptionsForQuestion(
        surgeList,
        "SURGE",
        state.bonusSurgeGuessId,
        extremes.surgeItemId,
        isRevealed
      );

      if (!isRevealed) {
        document.querySelectorAll(".bonus-opt-btn").forEach((btn) => {
          btn.addEventListener("click", () => {
            selectBonusOption(btn.dataset.q, btn.dataset.id);
          });
        });
      }

      const submitBtn = document.getElementById("submitBonusAuditBtn");
      if (isRevealed) {
        submitBtn.disabled = false;
        submitBtn.classList.add("ready-teal");
        submitBtn.textContent = "VIEW FINAL TIMECARD → [ENTER]";
      } else {
        submitBtn.classList.remove("ready-teal");
        const ready = Boolean(state.bonusDropGuessId && state.bonusSurgeGuessId);
        submitBtn.disabled = !ready;
        submitBtn.textContent = ready
          ? "LOCK IN AUDIT & REVEAL SWINGS → [ENTER]"
          : "SELECT BOTH ITEMS TO LOCK IN AUDIT";
      }
    }

    function buildShareText() {
      const finalScore = Math.max(0, state.rawScore);
      const formattedScore = finalScore.toLocaleString("en-US");
      const payout = getPayoutTier(finalScore);
      const archTag = state.isArchive ? " (Archive)" : "";
      const header = `PUNCHCARD #${state.puzzleNumber}${archTag} — ${formattedScore} / 2,000 pts [${payout.code}]`;

      const lines = state.history.map((h) => {
        const sq = h.isCorrect ? "🟩" : "🟥";
        const dots = "●".repeat(h.holes);
        return `${h.shortLabel} [${dots} ${h.multApplied}] ${sq} ${h.item.pct_diff}% ${h.item.direction}`;
      });

      const auditPts = state.bonusResult ? state.bonusResult.pointsEarned : 0;
      lines.push(`Time-Price Audit: +${auditPts}/200 pts`);

      return [header, ...lines].join("\n");
    }

    function renderSummary() {
      const finalScore = Math.max(0, state.rawScore);
      const isWin = finalScore >= WIN_SCORE_THRESHOLD;
      const payout = getPayoutTier(finalScore);

      const assetPill = document.getElementById("payoutAssetPill");
      assetPill.textContent = payout.pillText;
      assetPill.className = `payout-asset-pill ${payout.cssClass}`;

      document.getElementById("finalScore").textContent = finalScore.toLocaleString("en-US");
      document.getElementById("summaryThresholdSub").textContent = isWin
        ? `${payout.desc} (+${(finalScore - WIN_SCORE_THRESHOLD).toLocaleString("en-US")} pts over 1,000 quota)`
        : `${payout.desc} (${(WIN_SCORE_THRESHOLD - finalScore).toLocaleString("en-US")} pts short of 1,000 quota)`;

      const hits = state.history.filter((h) => h.isCorrect).length;
      const auditPts = state.bonusResult ? state.bonusResult.pointsEarned : 0;
      const holidayRound = state.history.find((h) => h.stampType === "GOLD");
      const stats = loadLifetimeStats();

      document.getElementById("kpiAccuracy").textContent = `${hits}/5`;
      document.getElementById("kpiBonusAudit").textContent = `+${auditPts} PTS`;
      document.getElementById("kpiHoliday").textContent = holidayRound
        ? holidayRound.isCorrect
          ? "+600 PTS"
          : "DOCKED -300"
        : "UNUSED";
      document.getElementById("kpiStreak").textContent = String(stats.winStreak);

      // Update Summary Wage Lens Buttons (Median vs. Federal Minimum Wage)
      const isMinLens = state.summaryLens === "MINIMUM";
      document.getElementById("lensMedianBtn").classList.toggle("active", !isMinLens);
      document.getElementById("lensMinimumBtn").classList.toggle("active", isMinLens);

      // Compute Time-Price Trends under the active Summary Lens
      const trendItems = state.history.map((h) => {
        const hrsThen = isMinLens ? h.item.min_hours_then : h.item.hours_then;
        const hrsNow = isMinLens ? h.item.min_hours_now : h.item.hours_now;
        const exactPct = ((hrsNow - hrsThen) / hrsThen) * 100;
        const pct = Math.round(exactPct);
        return { item: h.item, hrsThen, hrsNow, exactPct, pct };
      });

      const cheaperCount = trendItems.filter((t) => t.exactPct < 0).length;
      const sortedByTrend = trendItems.slice().sort((a, b) => a.exactPct - b.exactPct);
      const biggestDrop = sortedByTrend[0];
      const biggestSurge = sortedByTrend[sortedByTrend.length - 1];

      const lensName = isMinLens
        ? "Federal Minimum Wage ($7.25/hr today)"
        : "US Median Wage ($32.40/hr today)";
      document.getElementById("trendSynthesisBody").textContent =
        `Under ${lensName}: ${cheaperCount} of 5 items require less work today than at release • ` +
        `Biggest drop: ${biggestDrop.item.name} (${biggestDrop.pct > 0 ? "+" : ""}${biggestDrop.pct}%) • ` +
        `Most costlier/resilient: ${biggestSurge.item.name} (${biggestSurge.pct > 0 ? "+" : ""}${biggestSurge.pct}%)`;

      const recapList = document.getElementById("recapList");
      recapList.innerHTML = state.history
        .map((h) => {
          const badgeCls = h.isCorrect ? "hit" : "miss";
          const sign = h.delta > 0 ? "+" : "";
          const holesStr = "●".repeat(h.holes);

          const hrsThen = isMinLens ? h.item.min_hours_then : h.item.hours_then;
          const hrsNow = isMinLens ? h.item.min_hours_now : h.item.hours_now;
          const dir = isMinLens ? h.item.min_direction : h.item.direction;
          const pctDiff = isMinLens ? h.item.min_pct_diff : h.item.pct_diff;

          const trendPct = Math.round(((hrsNow - hrsThen) / hrsThen) * 100);
          const trendSign = trendPct > 0 ? "+" : "";
          let trendCls = "flat";
          let trendLabel = `◆ ${trendSign}${trendPct}% TIME-PRICE`;
          if (trendPct <= -10) {
            trendCls = "cheaper";
            trendLabel = `▼ ${trendPct}% TIME-PRICE (CHEAPER TODAY)`;
          } else if (trendPct >= 10) {
            trendCls = "costlier";
            trendLabel = `▲ +${trendPct}% TIME-PRICE (COSTLIER TODAY)`;
          }

          return `
            <div class="recap-row">
              <div class="recap-left">
                <div class="recap-item-name">R${h.round} (${h.benchmarkTitle}): ${h.item.name} (${h.item.year})</div>
                <div class="recap-meta">
                  <span>${holesStr} ${h.stampName} (${h.multApplied}) • Then: ${formatHours(hrsThen)} → Now: ${formatHours(hrsNow)}</span>
                  <span class="trend-pill ${trendCls}">${trendLabel}</span>
                </div>
              </div>
              <div class="recap-right">
                <span class="recap-badge ${badgeCls}">${h.isCorrect ? "HIT" : "MISS"} ${sign}${h.delta} PTS</span>
                <div class="recap-margin">${pctDiff}% ${dir}</div>
              </div>
            </div>
          `;
        })
        .join("");

      document.getElementById("sharePreview").textContent = buildShareText();
    }

    // =========================================================================
    // TIMECARD RACK ARCHIVE MODAL
    // =========================================================================
    function renderArchiveModal() {
      const todayInfo = getTodayUTCInfo();
      const rackList = document.getElementById("rackList");
      const cardsHtml = [];

      for (let idx = todayInfo.dayIndex; idx >= 0; idx--) {
        const ms = LAUNCH_UTC_MS + idx * 86400000;
        const dateKey = formatDateKeyFromUTC(new Date(ms));
        const puzzleNum = idx + 1;
        const isToday = dateKey === todayInfo.dateKey;
        const isCurrentLoaded = dateKey === state.dateKey;
        const saved = loadShiftProgress(dateKey);

        let statusHtml = `<span class="status-pill unpunched">UNPUNCHED</span>`;
        let squaresHtml = "";

        if (saved && saved.completed) {
          const score = Math.max(0, saved.rawScore);
          const won = score >= WIN_SCORE_THRESHOLD;
          const payout = getPayoutTier(score);
          const pillCls = won ? "completed-win" : "completed-short";
          statusHtml = `<span class="status-pill ${pillCls}">${payout.code} • ${score.toLocaleString("en-US")}</span>`;
          squaresHtml = `<div class="rack-mini-squares">${saved.history
            .map((h) => (h.isCorrect ? "🟩" : "🟥"))
            .join("")}</div>`;
        } else if (saved && saved.history && saved.history.length > 0) {
          const stage = saved.bonusPhase ? "AUDIT" : `R${saved.history.length}/5`;
          statusHtml = `<span class="status-pill in-progress">IN PROGRESS (${stage})</span>`;
          squaresHtml = `<div class="rack-mini-squares">${saved.history
            .map((h) => (h.isCorrect ? "🟩" : "🟥"))
            .join("")}</div>`;
        }

        cardsHtml.push(`
          <button class="rack-slot ${isCurrentLoaded ? "current-loaded" : ""}" type="button" data-date-key="${dateKey}">
            <div>
              <div class="rack-slot-title">
                PUNCHCARD #${puzzleNum}
                ${isToday ? '<span class="rack-live-tag">TODAY</span>' : ""}
              </div>
              <div class="rack-slot-date">${formatHumanDateUTC(dateKey)} (UTC)</div>
            </div>
            <div class="rack-status">
              ${statusHtml}
              ${squaresHtml}
            </div>
          </button>
        `);
      }

      rackList.innerHTML = cardsHtml.join("");
      rackList.querySelectorAll(".rack-slot").forEach((btn) => {
        btn.addEventListener("click", () => {
          const dk = btn.dataset.dateKey;
          playTone("tick");
          archiveModal.classList.remove("open");
          loadShiftByDateKey(dk);
        });
      });
    }

    function renderStatsModal() {
      const s = loadLifetimeStats();
      document.getElementById("statGamesPlayed").textContent = String(s.gamesPlayed);
      document.getElementById("statWinStreak").textContent = String(s.winStreak);

      const avg = s.gamesPlayed > 0 ? Math.round(s.totalScoreSum / s.gamesPlayed) : 0;
      document.getElementById("statAvgScore").textContent = avg.toLocaleString("en-US");

      const acc =
        s.totalRoundsPlayed > 0
          ? Math.round((s.totalRoundsCorrect / s.totalRoundsPlayed) * 100) + "%"
          : "0%";
      document.getElementById("statOuAccuracy").textContent = acc;

      const holidayRate =
        s.goldAttempts > 0
          ? `${Math.round((s.goldHits / s.goldAttempts) * 100)}% (${s.goldHits}/${s.goldAttempts})`
          : "—";
      document.getElementById("stat3xHitRate").textContent = holidayRate;
    }

    // =========================================================================
    // CLIPBOARD SHARE & COUNTDOWN TIMER
    // =========================================================================
    async function copyScorecardToClipboard() {
      const text = buildShareText();
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text);
          showToast("TIMECARD COPIED TO CLIPBOARD!");
          return;
        }
      } catch (e) {
        // Fall through
      }

      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
        showToast("TIMECARD COPIED TO CLIPBOARD!");
      } catch (e) {
        showToast("SELECT & COPY SCORECARD BELOW");
      } finally {
        document.body.removeChild(ta);
      }
    }

    function updateCountdown() {
      const nowMs = Date.now();
      const todayInfo = getTodayUTCInfo(new Date(nowMs));

      if (state.todayDateKey && todayInfo.dateKey !== state.todayDateKey) {
        loadShiftByDateKey(todayInfo.dateKey);
        showToast(`NEW SHIFT OPEN: PUNCHCARD #${todayInfo.puzzleNumber}`);
        return;
      }

      const remainingMs = Math.max(0, todayInfo.nextMidnightMs - nowMs);
      const totalSec = Math.floor(remainingMs / 1000);
      const hh = String(Math.floor(totalSec / 3600)).padStart(2, "0");
      const mm = String(Math.floor((totalSec % 3600) / 60)).padStart(2, "0");
      const ss = String(totalSec % 60).padStart(2, "0");
      document.getElementById("countdownTimer").textContent = `NEXT SHIFT (UTC): ${hh}:${mm}:${ss}`;
    }

    // =========================================================================
    // EVENT WIRING & KEYBOARD SHORTCUTS
    // =========================================================================
    document.getElementById("btnUnder").addEventListener("click", () => selectDirection("UNDER"));
    document.getElementById("btnOver").addEventListener("click", () => selectDirection("OVER"));

    document.getElementById("stampBaseBtn").addEventListener("click", () => selectStamp("BASE"));
    document.getElementById("stampSilverBtn").addEventListener("click", () => selectStamp("SILVER"));
    document.getElementById("stampGoldBtn").addEventListener("click", () => selectStamp("GOLD"));

    document.getElementById("punchSubmitBtn").addEventListener("click", submitGuess);
    document.getElementById("nextRoundBtn").addEventListener("click", advanceRound);
    document.getElementById("submitBonusAuditBtn").addEventListener("click", handleBonusAuditAction);
    document.getElementById("shareBtn").addEventListener("click", copyScorecardToClipboard);

    // End-of-Shift Summary Wage Lens Switcher (Median Earner vs. Federal Minimum Wage)
    document.getElementById("lensMedianBtn").addEventListener("click", () => {
      if (state.summaryLens === "MEDIAN") return;
      state.summaryLens = "MEDIAN";
      playTone("tick");
      renderSummary();
    });
    document.getElementById("lensMinimumBtn").addEventListener("click", () => {
      if (state.summaryLens === "MINIMUM") return;
      state.summaryLens = "MINIMUM";
      playTone("tick");
      renderSummary();
    });

    document.getElementById("returnTodayBtn").addEventListener("click", () => {
      playTone("tick");
      loadShiftByDateKey(getTodayUTCInfo().dateKey);
    });

    document.getElementById("sfxBtn").textContent = sfxEnabled ? "SFX: ON" : "SFX: OFF";
    document.getElementById("sfxBtn").addEventListener("click", () => {
      sfxEnabled = !sfxEnabled;
      localStorage.setItem(STORAGE_KEYS.SFX, String(sfxEnabled));
      document.getElementById("sfxBtn").textContent = sfxEnabled ? "SFX: ON" : "SFX: OFF";
      if (sfxEnabled) playTone("tick");
    });

    // Rules Modal Wiring + First-Visit Auto-Open
    const rulesModal = document.getElementById("rulesModal");
    function closeRulesModal() {
      localStorage.setItem(STORAGE_KEYS.RULES_SEEN, "true");
      rulesModal.classList.remove("open");
    }
    document.getElementById("rulesBtn").addEventListener("click", () => {
      rulesModal.classList.add("open");
    });
    document.getElementById("closeRulesBtn").addEventListener("click", closeRulesModal);
    document.getElementById("startShiftBtn").addEventListener("click", () => {
      playTone("tick");
      closeRulesModal();
    });
    rulesModal.addEventListener("click", (e) => {
      if (e.target === rulesModal) closeRulesModal();
    });

    const archiveModal = document.getElementById("archiveModal");
    function openArchive() {
      renderArchiveModal();
      archiveModal.classList.add("open");
    }
    document.getElementById("archiveBtn").addEventListener("click", openArchive);
    document.getElementById("openRackFromSummaryBtn").addEventListener("click", openArchive);
    document.getElementById("closeArchiveBtn").addEventListener("click", () => {
      archiveModal.classList.remove("open");
    });
    archiveModal.addEventListener("click", (e) => {
      if (e.target === archiveModal) archiveModal.classList.remove("open");
    });

    const statsModal = document.getElementById("statsModal");
    document.getElementById("statsBtn").addEventListener("click", () => {
      renderStatsModal();
      statsModal.classList.add("open");
    });
    document.getElementById("closeStatsBtn").addEventListener("click", () => {
      statsModal.classList.remove("open");
    });
    statsModal.addEventListener("click", (e) => {
      if (e.target === statsModal) statsModal.classList.remove("open");
    });

    document.addEventListener("keydown", (e) => {
      if (rulesModal.classList.contains("open")) {
        if (e.key === "Escape" || e.key === "Enter") {
          e.preventDefault();
          closeRulesModal();
        }
        return;
      }
      if (archiveModal.classList.contains("open")) {
        if (e.key === "Escape") archiveModal.classList.remove("open");
        return;
      }
      if (statsModal.classList.contains("open")) {
        if (e.key === "Escape") statsModal.classList.remove("open");
        return;
      }
      if (state.completed) return;

      if (state.bonusPhase) {
        if (e.key === "Enter") {
          if (state.bonusRevealed || (state.bonusDropGuessId && state.bonusSurgeGuessId)) {
            e.preventDefault();
            handleBonusAuditAction();
          }
        }
        return;
      }

      const key = e.key.toLowerCase();
      if (!state.revealed) {
        if (key === "u" || e.key === "ArrowLeft") {
          selectDirection("UNDER");
        } else if (key === "o" || e.key === "ArrowRight") {
          selectDirection("OVER");
        } else if (key === "1") {
          selectStamp("BASE");
        } else if (key === "2") {
          selectStamp("SILVER");
        } else if (key === "3") {
          selectStamp("GOLD");
        } else if (e.key === "Enter" && state.selectedDirection) {
          e.preventDefault();
          submitGuess();
        }
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        advanceRound();
      }
    });

    // Boot
    loadShiftByDateKey(getTodayUTCInfo().dateKey);
    updateCountdown();
    setInterval(updateCountdown, 1000);

    if (!localStorage.getItem(STORAGE_KEYS.RULES_SEEN)) {
      rulesModal.classList.add("open");
    }
  </script>
</body>
</html>
"""


# =============================================================================
# 6. BUILD & LOCAL DEV SERVER
# =============================================================================
def build_html(
    output_path: Path,
    skip_image_fetch: bool = False,
    refresh_images: bool = False,
) -> List[Dict[str, Any]]:
    """Process dataset, auto-resolve item images, embed JSON payload, and write HTML."""
    processed_items = process_dataset(RAW_ITEMS)
    cache_path = Path(__file__).resolve().parent / IMAGE_CACHE_FILENAME
    resolve_item_images(
        processed_items,
        cache_path=cache_path,
        skip_fetch=skip_image_fetch,
        refresh=refresh_images,
    )

    payload = {
        "launch_date": LAUNCH_DATE,
        "benchmarks": BENCHMARKS,
        "items": processed_items,
        "default_wage_today": DEFAULT_WAGE_TODAY,
        "default_min_wage_today": DEFAULT_MIN_WAGE_TODAY,
    }
    embedded_json = json.dumps(payload, indent=2)
    final_html = HTML_TEMPLATE.replace("__EMBEDDED_DATA_JSON__", embedded_json)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(final_html, encoding="utf-8")
    return processed_items


def find_available_port(preferred_port: int) -> int:
    """Return preferred_port if free, otherwise find an open local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", preferred_port)) != 0:
            return preferred_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler serving from the output directory with clean request logs."""

    def log_message(self, format: str, *args: Any) -> None:
        sys.stdout.write(f"[HTTP] {self.address_string()} - {format % args}\n")


def serve_directory(directory: Path, filename: str, preferred_port: int) -> None:
    """Launch a local Python HTTP server serving the generated game."""
    port = find_available_port(preferred_port)
    handler = functools.partial(QuietHandler, directory=str(directory.resolve()))

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    url = f"http://127.0.0.1:{port}/{filename}"
    print(f"\nServing PUNCHCARD at: {url}")
    print("Press Ctrl+C to stop the server.\n")

    with ReusableTCPServer(("127.0.0.1", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down PUNCHCARD server.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build standalone PUNCHCARD HTML game and optionally serve it locally."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="index.html",
        help="Output HTML file path (default: index.html)",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Launch a local Python HTTP server after building index.html",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Preferred port for --serve (default: 8000)",
    )
    parser.add_argument(
        "--skip-image-fetch",
        action="store_true",
        help="Skip build-time Wikimedia Commons lookup (browser will still auto-fetch online)",
    )
    parser.add_argument(
        "--refresh-images",
        action="store_true",
        help="Re-query Wikimedia Commons and overwrite .punchcard_image_cache.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    processed_items = build_html(
        output_path,
        skip_image_fetch=args.skip_image_fetch,
        refresh_images=args.refresh_images,
    )

    resolved_photos = sum(1 for x in processed_items if x.get("image_url"))
    print(
        f"Built {output_path.resolve()} ({len(processed_items)} calibrated items, "
        f"{resolved_photos} auto-resolved photos):"
    )
    for b in BENCHMARKS:
        tier_items = [x for x in processed_items if x["tier"] == b["round"]]
        over_med = sum(1 for x in tier_items if x["direction"] == "OVER")
        over_min = sum(1 for x in tier_items if x["min_direction"] == "OVER")
        print(
            f"  Round {b['round']} ({b['title']:<7} | {b['hours']:>6.1f}h): "
            f"{len(tier_items)} items | Median: {over_med} OVER / {len(tier_items)-over_med} UNDER | "
            f"Min Wage: {over_min} OVER / {len(tier_items)-over_min} UNDER"
        )

    if args.serve:
        serve_directory(output_path.parent, output_path.name, args.port)


if __name__ == "__main__":
    main()