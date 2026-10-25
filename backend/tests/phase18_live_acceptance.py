"""Synthetic candidate-gap acceptance using bounded related-public discovery."""
from tests.phase15_live_acceptance import run
from tests.phase16_live_acceptance import check


def gaps_check(owner, other, private_id, public_id, passed):
    return check(owner, other, private_id, public_id, passed, focus="candidate_gaps")


if __name__ == "__main__":
    run(extra_acceptance=gaps_check, phase="phase18")
