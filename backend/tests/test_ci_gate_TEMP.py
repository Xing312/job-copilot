# TEMPORARY — used to verify that branch protection blocks merging a PR with a
# failing CI check. Delete this file (and its branch) after confirming.
def test_ci_gate_should_block_merge():
    assert False, "Intentional failure to confirm the CI gate blocks merges"
