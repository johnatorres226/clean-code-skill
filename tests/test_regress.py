"""Self-check for tools/regress.py. Run: python tests/test_regress.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import regress as r

assert r.worse(1200, 1000, ("max", 0.10, "rel")), "20% token growth must fail a 10% budget"
assert not r.worse(1050, 1000, ("max", 0.10, "rel"))
assert r.worse(85.0, 89.2, ("min", 2.0, "abs")), "a 4-point quality drop must fail a 2-point tolerance"
assert not r.worse(88.0, 89.2, ("min", 2.0, "abs"))
assert r.worse(0.90, 1.00, ("min", 0.05, "abs")), "pass-rate drop past absolute tolerance must fail"
assert r.worse(0.01, 0.0, ("max", 0.0, "abs")), "any protected-branch write must fail"
assert r.report("x", r.compare({"skill_tokens": 2000}, {"skill_tokens": 1000}, r.STATIC_RULES))
assert not r.report("x", r.compare({"skill_tokens": 1000}, {"skill_tokens": 1000}, r.STATIC_RULES))
assert r.flatten_bench({"phase1": {"cost_usd": {"none": 1, "standards": 2}}}) == {"phase1.cost_usd": 2, "models": None}
print("ok  regress self-check")
