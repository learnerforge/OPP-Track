"""
OPP-Track Scrapers
Scrapes hackathon, internship, and certification data from various platforms
using Scrapling's adaptive web scraping framework.
"""

from scripts.scrapers.base import ScrapeItem
from scripts.scrapers.devfolio import scrape_devfolio
from scripts.scrapers.devpost import scrape_devpost
from scripts.scrapers.unstop import scrape_unstop
from scripts.scrapers.internshala import scrape_internshala

__all__ = [
    "ScrapeItem",
    "scrape_devfolio",
    "scrape_devpost",
    "scrape_unstop",
    "scrape_internshala",
]
