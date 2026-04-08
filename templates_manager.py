"""Centralized Jinja2 template management to prevent cache corruption.

This module provides a single Jinja2Templates instance shared across the entire
application, preventing issues with multiple template instances and cache corruption.
"""

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

# Create a custom Jinja2Templates that disables caching
class CachedisabledJinja2Templates(Jinja2Templates):
    def __init__(self, directory: str):
        super().__init__(directory=directory)
        # Disable caching by setting cache_size to 0
        self.env.cache = None
        self.env.cache_size = 0

# Single shared templates instance with caching disabled
templates = CachedisabledJinja2Templates(directory="templates")

__all__ = ["templates"]


