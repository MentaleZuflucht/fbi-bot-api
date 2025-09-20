"""
GraphQL resolvers module.

Exports all GraphQL resolvers for easy importing.
"""

from .discord import Query as DiscordQuery

__all__ = [
    "DiscordQuery"
]
