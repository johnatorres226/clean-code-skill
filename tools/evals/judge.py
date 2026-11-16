"""Blind pairwise code review by an LLM judge, controlled for position bias.

Each pair is judged twice with the presentation order swapped; a verdict counts only when both
orders agree (Zheng et al. 2023, "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena").
The caller supplies `ask(prompt) -> (reply_text, cost_usd)`, so this module has no CLI coupling.
"""
from __future__ import annotations

import json
import re
import statistics
from typing import Callable

JUDGE_PROMPT = """You are reviewing two solutions to the same task. Both pass the same unit tests.
Judge which one a maintainer would rather own: readability, naming, function size and
complexity, duplication, structure that would absorb the next requirement, and efficiency.
Do not reward length or comments for their own sake. Use no tools.

Task:
{task}

=== Solution A ===
{a}

=== Solution B ===
{b}

Reply with only a JSON object: {{"better": "A" or "B" or "tie", "score_A": 1-10, "score_B": 1-10, "reason": "<one sentence>"}}"""

Ask = Callable[[str], "tuple[str, float]"]


def parse_verdict(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


def pairwise(ask: Ask, task: str, first_code: str, second_code: str,
             labels: tuple[str, str] = ("none", "standards")) -> dict:
    """Judge `first_code` (labels[0]) against `second_code` (labels[1]) in both orders."""
    a_label, b_label = labels
    reply1, cost1 = ask(JUDGE_PROMPT.format(task=task, a=first_code, b=second_code))
    reply2, cost2 = ask(JUDGE_PROMPT.format(task=task, a=second_code, b=first_code))
    v1, v2 = parse_verdict(reply1), parse_verdict(reply2)
    pick1 = {"A": a_label, "B": b_label}.get(v1.get("better"), "tie")
    pick2 = {"A": b_label, "B": a_label}.get(v2.get("better"), "tie")
    if not v1.get("better") or not v2.get("better"):  # an unparseable reply is no verdict, not a tie
        return {"valid": False, "replies": [reply1[-300:], reply2[-300:]], "cost_usd": cost1 + cost2}
    return {
        "order1": pick1, "order2": pick2,
        "winner": pick1 if pick1 == pick2 else "tie",  # disagreement across orders = position bias
        f"score_{a_label}": statistics.mean([v1.get("score_A", 0), v2.get("score_B", 0)]),
        f"score_{b_label}": statistics.mean([v1.get("score_B", 0), v2.get("score_A", 0)]),
        "reasons": [v1.get("reason"), v2.get("reason")],
        "cost_usd": cost1 + cost2,
    }


if __name__ == "__main__":
    # Self-check with a scripted judge that always prefers whichever solution is shown first:
    # pure position bias must collapse to a tie.
    biased = lambda prompt: ('{"better": "A", "score_A": 8, "score_B": 5, "reason": "x"}', 0.0)
    assert pairwise(biased, "t", "x", "y")["winner"] == "tie"
    consistent = lambda prompt: (
        '{"better": "%s", "score_A": 5, "score_B": 5}' % ("A" if prompt.index("good()") <
                                                          prompt.index("bad()") else "B"), 0.0)
    assert pairwise(consistent, "t", "bad()", "good()")["winner"] == "standards"
    assert pairwise(lambda prompt: ("garbled", 0.0), "t", "a", "b")["valid"] is False
    print("ok  judge self-check")
