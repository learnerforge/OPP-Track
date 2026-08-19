"""
OPP-Track Scrapers
Scrapes hackathon, internship, and certification data from various platforms
using Scrapling's adaptive web scraping framework.
"""

from .base import ScrapeItem, parse_deadline, clean_text, deduplicate
from .devfolio import scrape_devfolio
from .devpost import scrape_devpost
from .unstop import scrape_unstop
from .hackerearth import scrape_hackerearth
from .internshala import scrape_internshala

__all__ = [
    "ScrapeItem",
    "parse_deadline",
    "clean_text",
    "deduplicate",
    "scrape_devfolio",
    "scrape_devpost",
    "scrape_unstop",
    "scrape_hackerearth",
    "scrape_internshala",
]
