"""Golden-set regression check for the Rewriter+Critic loop.

Run with:  uv run python evals/run_evals.py

Exits non-zero if any case fails its minimum score bar -- wire this into
CI so swapping models or editing prompts can't silently degrade quality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from echoverse.agents.rewriter import rewrite_with_critique
from evals.golden_set import GOLDEN_SET


def main() -> int:
    failures = 0
    print(f"Running {len(GOLDEN_SET)} golden-set case(s)...\n")

    for case in GOLDEN_SET:
        rewritten, result, attempts = rewrite_with_critique(case["text"], case["tone"], max_revisions=2)
        meets_meaning = result.meaning_score >= case["min_meaning"]
        meets_tone = result.tone_score >= case["min_tone"]
        ok = meets_meaning and meets_tone and result.safety_ok

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {case['name']} (tone={case['tone']})")
        print(f"   meaning={result.meaning_score} (min {case['min_meaning']}), "
              f"tone={result.tone_score} (min {case['min_tone']}), revisions={attempts}")
        if not ok:
            failures += 1
            print(f"   rewritten: {rewritten[:150]}...")
        print()

    print(f"{len(GOLDEN_SET) - failures}/{len(GOLDEN_SET)} passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
