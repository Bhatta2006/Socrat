"""Adaptive quiz engine (Content Master Plan §8.5, §8.8, §8.9), behind ``adaptive_quiz_enabled``.

The engine is pure: ``rating``, ``pools``, ``selection`` and ``modes`` take plain values and
return plain values. ``service`` and ``routes`` load state from the database, call the engine
and write responses, ratings and mastery evidence back.
"""
