"""The statistics, held to textbook values and to the dataset's own limits."""

import pytest

from agent_eval_lab.statistics import (
    minimum_detectable_flips,
    paired_delta,
    pass_rate,
    sign_test_exact,
    wilson,
)


def test_wilson_matches_the_textbook_interval():
    interval = wilson(5, 10)
    assert interval.estimate == 0.5
    assert interval.low == pytest.approx(0.2366, abs=1e-3)
    assert interval.high == pytest.approx(0.7634, abs=1e-3)
    assert wilson(0, 0).high == 1.0


def test_repeats_of_a_scenario_do_not_narrow_the_interval():
    """Three identical repeats of two scenarios are two observations, not six."""
    outcomes = {"a": [True, True, True], "b": [False, False, False]}
    interval = pass_rate(outcomes)
    assert interval.estimate == 0.5
    assert interval == wilson(1, 2)
    assert interval.high - interval.low > wilson(3, 6).high - wilson(3, 6).low


def test_a_scenario_that_flips_between_repeats_counts_as_part_of_a_pass():
    outcomes = {"a": [True, False], "b": [True, True], "c": [False, False], "d": [True, True]}
    interval = pass_rate(outcomes)
    assert interval.estimate == pytest.approx(0.625)
    assert interval.low < 0.625 < interval.high


@pytest.mark.parametrize(
    ("improved", "regressed", "expected"),
    [(0, 0, 1.0), (3, 3, 1.0), (5, 0, 0.0625), (6, 0, 0.03125), (0, 6, 0.03125)],
)
def test_sign_test_matches_the_exact_binomial(improved, regressed, expected):
    assert sign_test_exact(improved, regressed) == pytest.approx(expected)


def test_six_scenarios_must_move_before_a_difference_can_be_called():
    """The floor this dataset cannot go below: 6 of 27 development scenarios."""
    assert minimum_detectable_flips() == 6
    assert minimum_detectable_flips(alpha=0.01) == 8


def test_paired_delta_points_the_right_way_and_resamples_scenarios():
    before = {f"case-{i}": [True, True, True] for i in range(20)}
    after = {f"case-{i}": [i >= 10] * 3 for i in range(20)}
    delta = paired_delta(before, after)
    assert delta.estimate == pytest.approx(-0.5)
    assert delta.high < 0, "a change this large must not include zero"
    assert paired_delta(before, before).estimate == 0
    assert paired_delta({}, {}).estimate == 0
