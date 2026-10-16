"""Pattern-in-a-story items (content.md §8.6): a template story with slots, pattern fixed.

The pattern is decided by the template, never by wording, so the answer is right by
construction. ``fill`` refuses stories with unfilled or unknown slots.
"""

import random
import re
import string

SLOT = re.compile(r"\{([a-z_]+)\}")


def fill(template: str, slots: dict[str, list[str]], rng: random.Random) -> tuple[str, dict]:
    """The story with one value per slot, and the values chosen."""
    names = SLOT.findall(template)
    unknown = sorted(set(names) - set(slots))
    if unknown:
        raise ValueError(f"story has no values for {unknown}")
    chosen = {name: rng.choice(slots[name]) for name in sorted(set(names))}
    text = string.Formatter().vformat(template, (), chosen)
    if "{" in text or "}" in text:
        raise ValueError("story still has an unfilled slot")
    return text, chosen
