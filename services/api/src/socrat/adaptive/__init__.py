"""Adaptive roadmap: learner profile, stuck detection, suggestions and approved proposals.

The pure parts (``profile``, ``stuck``, ``suggest``) take plain values so every adaptation
can be replayed and explained. ``service`` gathers inputs from the database and
``proposals`` is the only path by which Socrat changes the roadmap: it asks first, and
nothing changes until the learner accepts.
"""
