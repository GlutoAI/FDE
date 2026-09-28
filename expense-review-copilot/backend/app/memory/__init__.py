"""Agent memory: bounded conversation history per thread and approved long-term preferences.

Memory is context for style and continuity. It never overrides expense amounts, receipt status,
permissions, or approval requirements, which are always read fresh from their sources.
"""
