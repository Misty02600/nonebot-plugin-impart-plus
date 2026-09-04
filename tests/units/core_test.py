import pytest


def test_growth_mode_boundaries_and_signed_delta() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        GrowthMode,
        growth_delta,
        supports_growth_mode,
    )

    assert supports_growth_mode(1.0, GrowthMode.LENGTH)
    assert not supports_growth_mode(0.0, GrowthMode.LENGTH)
    assert supports_growth_mode(0.0, GrowthMode.DEPTH)
    assert supports_growth_mode(-1.0, GrowthMode.DEPTH)
    assert growth_delta(1.25, GrowthMode.LENGTH) == 1.25
    assert growth_delta(1.25, GrowthMode.DEPTH) == -1.25


@pytest.mark.parametrize(
    (
        "requested",
        "requester_length",
        "target_length",
        "roll",
        "actual",
        "actor",
        "recipient",
        "fluid",
        "reversal",
    ),
    [
        ("INJECT", 10.0, 10.0, 0.75, "INJECT", "REQUESTER", "TARGET", "DNA", "NONE"),
        ("INJECT", 10.0, -10.0, 0.75, "INJECT", "REQUESTER", "TARGET", "DNA", "NONE"),
        (
            "INJECT",
            -10.0,
            10.0,
            0.75,
            "INJECT",
            "TARGET",
            "REQUESTER",
            "DNA",
            "WRONG_ACTION",
        ),
        (
            "INJECT",
            -10.0,
            -10.0,
            0.75,
            "SQUEEZE",
            "TARGET",
            "TARGET",
            "GIRL_JUICE",
            "WRONG_ACTION",
        ),
        (
            "SQUEEZE",
            -10.0,
            10.0,
            None,
            "SQUEEZE",
            "REQUESTER",
            "REQUESTER",
            "DNA",
            "NONE",
        ),
        (
            "SQUEEZE",
            -10.0,
            -10.0,
            None,
            "SQUEEZE",
            "REQUESTER",
            "REQUESTER",
            "GIRL_JUICE",
            "NONE",
        ),
        (
            "SQUEEZE",
            10.0,
            10.0,
            None,
            "INJECT",
            "TARGET",
            "REQUESTER",
            "DNA",
            "WRONG_ACTION",
        ),
        (
            "SQUEEZE",
            10.0,
            -10.0,
            None,
            "SQUEEZE",
            "TARGET",
            "TARGET",
            "DNA",
            "WRONG_ACTION",
        ),
        (
            "INJECT",
            3.0,
            10.0,
            0.25,
            "INJECT",
            "TARGET",
            "REQUESTER",
            "DNA",
            "XNN",
        ),
        (
            "INJECT",
            3.0,
            -10.0,
            0.25,
            "SQUEEZE",
            "TARGET",
            "TARGET",
            "DNA",
            "XNN",
        ),
    ],
)
def test_interaction_resolution_is_symmetric(
    requested: str,
    requester_length: float,
    target_length: float,
    roll: float | None,
    actual: str,
    actor: str,
    recipient: str,
    fluid: str,
    reversal: str,
) -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionFluid,
        InteractionParticipant,
        InteractionReversal,
        resolve_interaction,
    )

    resolution = resolve_interaction(
        InteractionAction[requested],
        requester_length,
        target_length,
        reverse_roll=roll,
    )

    assert resolution.action is InteractionAction[actual]
    assert resolution.actor is InteractionParticipant[actor]
    assert resolution.recipient is InteractionParticipant[recipient]
    assert resolution.fluid is InteractionFluid[fluid]
    assert resolution.reversal is InteractionReversal[reversal]


@pytest.mark.parametrize(
    (
        "length",
        "is_challenging",
        "challenge_completed",
        "probability",
        "expected_status",
        "expected_length",
        "expected_probability",
        "expected_challenging",
        "expected_completed",
    ),
    [
        (25.0, False, False, 0.5, "challenge_started_low_win", 25.0, 0.4, True, False),
        (
            -25.0,
            False,
            False,
            0.5,
            "challenge_started_low_win",
            -25.0,
            0.4,
            True,
            False,
        ),
        (30.0, True, False, 0.4, "challenge_success_high_win", 30.0, 0.5, False, True),
        (
            -30.0,
            True,
            False,
            0.4,
            "challenge_success_high_win",
            -30.0,
            0.5,
            False,
            True,
        ),
        (24.9, True, False, 0.4, "challenge_failed_high_win", 19.9, 0.5, False, False),
        (
            -24.9,
            True,
            False,
            0.4,
            "challenge_failed_high_win",
            -19.9,
            0.5,
            False,
            False,
        ),
        (24.9, False, True, 0.5, "challenge_completed_reduce", 19.9, 0.5, False, False),
        (
            -24.9,
            False,
            True,
            0.5,
            "challenge_completed_reduce",
            -19.9,
            0.5,
            False,
            False,
        ),
    ],
)
def test_challenge_state_is_symmetric(
    length: float,
    is_challenging: bool,
    challenge_completed: bool,
    probability: float,
    expected_status: str,
    expected_length: float,
    expected_probability: float,
    expected_challenging: bool,
    expected_completed: bool,
) -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        UserGameState,
        evaluate_user_state,
    )

    evaluation = evaluate_user_state(
        UserGameState(
            length=length,
            win_probability=probability,
            is_challenging=is_challenging,
            challenge_completed=challenge_completed,
            is_near_zero=False,
            is_zero_or_negative=length <= 0,
        )
    )

    assert evaluation.status == expected_status
    assert evaluation.state.length == expected_length
    assert evaluation.state.win_probability == expected_probability
    assert evaluation.state.is_challenging is expected_challenging
    assert evaluation.state.challenge_completed is expected_completed


def test_challenge_threshold_and_titles_are_symmetric() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        LengthState,
        classify_length,
        crossed_challenge_threshold,
    )

    assert crossed_challenge_threshold(24.9, 25.0)
    assert crossed_challenge_threshold(-24.9, -25.0)
    assert not crossed_challenge_threshold(25.0, 25.1)
    assert not crossed_challenge_threshold(-25.0, -25.1)
    assert classify_length(30.0) is LengthState.GOD
    assert classify_length(-30.0) is LengthState.ABYSS_LORD


def test_pk_settlement_applies_base_changes_before_challenge_updates() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        GrowthMode,
        UserGameState,
        resolve_pk_settlement,
    )

    attacker = UserGameState(25.1, 0.4, True, False, False, False)
    defender = UserGameState(25.1, 0.5, False, False, False, False)

    settlement = resolve_pk_settlement(
        attacker,
        defender,
        win_roll=1.0,
        random_num=0.5,
    )

    assert settlement.mode is GrowthMode.LENGTH
    assert settlement.resolution.won is False
    assert (
        settlement.attacker.base.length,
        settlement.attacker.base.win_probability,
        settlement.attacker.status,
        settlement.attacker.final.length,
        settlement.attacker.final.win_probability,
        settlement.attacker.final.is_challenging,
    ) == (24.6, 0.41, "challenge_failed_high_win", 19.6, 0.5125, False)
    assert (
        settlement.defender.status,
        settlement.defender.final.length,
        settlement.defender.final.win_probability,
        settlement.defender.final.is_challenging,
    ) == (
        "challenge_started_low_win",
        25.35,
        0.392,
        True,
    )
