# This is a Python file for Experiment 2-5 Prime (attempt 4).
# It contains a comment line that is deliberately too long to pass flake8 checks (E501).
# With E501 now enabled in pre-commit, this should fail the local commit if pre-commit runs, and then fail CI.
# This_comment_is_intentionally_made_extremely_long_to_ensure_that_it_violates_the_maximum_line_length_restriction_enforced_by_flake8_specifically_the_E501_error_code_now_that_it_is_no_longer_ignored_in_the_pre_commit_configuration_even_after_black_has_had_a_chance_to_reformat_the_rest_of_the_file_as_black_typically_does_not_alter_long_comment_lines_which_is_precisely_the_behavior_we_are_relying_on_for_this_test_case_to_succeed_in_generating_a_CI_failure_condition.


def another_short_function():
    pass
