"""PHASE17_LIVE_ACCEPTANCE=1 python -m tests.phase17_live_acceptance

Uses only fabricated papers, including an intentionally conflicting result.
Exercises disconnected-request recovery and the existing comparison regression.
"""
from tests.phase15_live_acceptance import run
from tests.phase16_live_acceptance import check


def interpretation_check(owner, other, private_id, public_id, passed):
    check(owner, other, private_id, public_id, passed, focus="contradictions")


if __name__ == "__main__":
    run(extra_acceptance=interpretation_check, phase="phase17")
