# This is a Python file for Experiment 2-5 Prime (attempt 5 - Bandit B101).
# It contains an assert statement, which should trigger Bandit B101 error.


def function_with_assert():
    x = 1
    assert x == 1, "This is a test assert for Bandit B101"
    print("Assertion passed locally, but Bandit should flag it.")


function_with_assert()
