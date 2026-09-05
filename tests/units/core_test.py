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
    ("requester_length", "target_length", "expected"),
    [
        (5, 5, (("INJECT", "A>B", 100, "DNA"), ("INJECT", "B>A", 100, "DNA"))),
        (5, 4.999, (("INJECT", "A>B", 100, "DNA"), ("SQUEEZE", "A>B", 100, "DNA"))),
        (5, -10, (("INJECT", "A>B", 100, "DNA"), ("SQUEEZE", "A>B", 100, "DNA"))),
        (4.999, 5, (("INJECT", "B>A", 100, "DNA"), ("SQUEEZE", "B>A", 100, "DNA"))),
        (
            4.999,
            4.999,
            (("CUDDLE", "A>B,B>A", 10, "DNA"), ("CUDDLE", "A>B,B>A", 10, "DNA")),
        ),
        (4.999, -10, (("INJECT", "A>B", 10, "DNA"), ("SQUEEZE", "A>B", 100, "DNA"))),
        (-10, 5, (("INJECT", "B>A", 100, "DNA"), ("SQUEEZE", "B>A", 100, "DNA"))),
        (-10, 4.999, (("INJECT", "B>A", 10, "DNA"), ("SQUEEZE", "B>A", 100, "DNA"))),
        (
            -10,
            -10,
            (
                ("SQUEEZE", "A>B", 100, "GIRL_JUICE"),
                ("SQUEEZE", "B>A", 100, "GIRL_JUICE"),
            ),
        ),
    ],
)
def test_interaction_resolution_is_symmetric(
    requester_length: float, target_length: float, expected: tuple
) -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        InteractionAction,
        InteractionParticipant,
        resolve_interaction,
    )

    people = {InteractionParticipant.REQUESTER: "A", InteractionParticipant.TARGET: "B"}
    for requested, (action, directions, maximum, fluid) in zip(
        (InteractionAction.INJECT, InteractionAction.SQUEEZE), expected, strict=True
    ):
        resolution = resolve_interaction(requested, requester_length, target_length)
        assert resolution.action.name == action
        assert (
            ",".join(
                f"{people[flow.source]}>{people[flow.recipient]}"
                for flow in resolution.transfers
            )
            == directions
        )
        assert all(flow.max_volume == maximum for flow in resolution.transfers)
        assert all(flow.fluid.name == fluid for flow in resolution.transfers)


def test_challenge_transitions_are_derived_from_tier_and_length() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        LengthState,
        UserGameState,
        active_challenge,
        classify_length,
        evaluate_state_transition,
        resolve_pk_settlement,
    )

    cases = (
        (24.9, 25.0, 0, 0.5, "challenge_started_low_win", 25.0, 0.4, 0),
        (-24.9, -25.0, 0, 0.5, "challenge_started_low_win", -25.0, 0.4, 0),
        (25.0, 30.0, 0, 0.4, "challenge_success_high_win", 30.0, 0.5, 1),
        (-25.0, -30.0, 0, 0.4, "challenge_success_high_win", -30.0, 0.5, 1),
        (25.1, 24.9, 0, 0.4, "challenge_failed_high_win", 19.9, 0.5, 0),
        (-25.1, -24.9, 0, 0.4, "challenge_failed_high_win", -19.9, 0.5, 0),
        (25.1, 24.9, 1, 0.5, "challenge_completed_reduce", 19.9, 0.5, 0),
        (24.8, 30.1, 0, 0.5, "challenge_completed", 30.1, 0.5, 1),
    )
    for (
        before_length,
        base_length,
        tier,
        probability,
        status,
        length,
        final_probability,
        final_tier,
    ) in cases:
        before = UserGameState(before_length, probability, tier)
        evaluation = evaluate_state_transition(
            before,
            UserGameState(base_length, probability, tier),
        )
        assert (
            evaluation.status,
            evaluation.state.length,
            evaluation.state.win_probability,
            evaluation.state.challenge_tier,
        ) == (status, length, final_probability, final_tier)

    assert active_challenge(UserGameState(25, 0.4, 0))
    assert active_challenge(UserGameState(-29.999, 0.4, 0))
    assert active_challenge(UserGameState(25, 0.5, 1)) is None
    restored = evaluate_state_transition(
        UserGameState(25.1, 0.4),
        UserGameState(24.9, 0.41),
    )
    assert restored.state.win_probability == pytest.approx(0.5125)
    assert classify_length(27, challenge_tier=1) is LengthState.GOD
    assert classify_length(-27, challenge_tier=1) is LengthState.ABYSS_LORD
    assert classify_length(30, challenge_tier=0) is LengthState.NORMAL

    # 保留乘1.25的浮点路径；改成除0.8会使下一局舍入为0.477。
    completed = resolve_pk_settlement(
        UserGameState(29.9, 0.4),
        (UserGameState(40, 0.5, 1),),
        win_roll=0,
        random_num=0.2,
    )
    following = resolve_pk_settlement(
        completed.attacker.final,
        tuple(target.final for target in completed.defenders),
        win_roll=0,
        random_num=0.2,
    )
    assert completed.attacker.final.challenge_tier == 1
    assert following.attacker.final.win_probability == 0.478


def test_growth_multiplier_uses_the_tier_before_settlement() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        GrowthMode,
        UserGameState,
        resolve_growth_settlement,
    )

    completed = resolve_growth_settlement(
        UserGameState(29.8, 0.4),
        GrowthMode.LENGTH,
        0.3,
    )
    boosted = resolve_growth_settlement(
        completed.final,
        GrowthMode.LENGTH,
        0.3,
    )
    depth = resolve_growth_settlement(
        UserGameState(-30.0, 0.5, 1),
        GrowthMode.DEPTH,
        0.3,
    )

    assert (completed.amount, completed.final.length, completed.completed_tier) == (
        0.3,
        30.1,
        1,
    )
    assert (boosted.amount, boosted.final.length) == (0.6, 30.7)
    assert (depth.amount, depth.final.length) == (0.6, -30.6)


def test_temporary_second_tier_keeps_lower_reward_and_drops_once() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        CHALLENGE_TIERS,
        ChallengeTier,
        UserGameState,
        evaluate_state_transition,
        personal_length_multiplier,
    )

    tiers = (
        *CHALLENGE_TIERS,
        ChallengeTier(2, 300, 305, 0.7, 10 / 7, 20),
    )
    challenger = UserGameState(301, 0.35, 1)
    success = evaluate_state_transition(
        challenger,
        UserGameState(305, 0.35, 1),
        tiers,
    )
    failure = evaluate_state_transition(
        challenger,
        UserGameState(299, 0.35, 1),
        tiers,
    )

    assert personal_length_multiplier(challenger) == 2
    assert (success.status, success.state.challenge_tier) == (
        "challenge_success_high_win",
        2,
    )
    assert success.state.win_probability == pytest.approx(0.5)
    assert (
        failure.status,
        failure.state.length,
        failure.state.challenge_tier,
        failure.state.win_probability,
    ) == ("challenge_failed_high_win", 279, 1, pytest.approx(0.5))


def test_possession_assigns_tier_by_half_and_handles_active_challenge() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        CHALLENGE_TIERS,
        ChallengeTier,
        PossessionSettlement,
        PossessionStatus,
        UserGameState,
        resolve_possession,
    )

    actor = UserGameState(-70, 0.6, 1)
    lost_title = resolve_possession(actor, UserGameState(49.998, 0.4, 1))
    kept_title = resolve_possession(actor, UserGameState(49.999, 0.4, 1))
    gained_title = resolve_possession(actor, UserGameState(60, 0.4))

    assert isinstance(lost_title, PossessionSettlement)
    assert (lost_title.half, lost_title.actor.challenge_tier) == (24.999, 0)
    assert (
        lost_title.target.length,
        lost_title.target.challenge_tier,
        lost_title.target_status,
    ) == (19.999, 0, "challenge_completed_reduce")
    assert isinstance(kept_title, PossessionSettlement)
    assert (kept_title.half, kept_title.target.challenge_tier) == (25, 1)
    assert isinstance(gained_title, PossessionSettlement)
    assert (gained_title.half, gained_title.target.challenge_tier) == (30, 1)

    assert (
        resolve_possession(
            actor,
            UserGameState(26, 0.4),
        )
        is PossessionStatus.TARGET_CHALLENGING
    )
    assert (
        resolve_possession(
            UserGameState(-70, 0.6),
            UserGameState(20, 0.4),
        )
        is PossessionStatus.LOCKED
    )

    tiers = (
        *CHALLENGE_TIERS,
        ChallengeTier(2, 300, 305, 0.7, 10 / 7, 20),
    )
    active_actor = resolve_possession(
        UserGameState(-302, 0.35, 1),
        UserGameState(280, 0.5, 1),
        tiers,
    )
    high_actor = resolve_possession(
        UserGameState(-700, 0.5, 2),
        UserGameState(640, 0.5, 2),
        tiers,
    )
    assert isinstance(active_actor, PossessionSettlement)
    assert (
        active_actor.half,
        active_actor.actor.challenge_tier,
        active_actor.actor.win_probability,
    ) == (140, 1, pytest.approx(0.5))
    assert isinstance(high_actor, PossessionSettlement)
    assert (high_actor.half, high_actor.actor.challenge_tier) == (320, 2)
    assert high_actor.target.challenge_tier == 2


def test_pk_uses_one_roll_and_personal_multiplier_for_all_participants() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        UserGameState,
        resolve_pk_settlement,
    )

    attacker = UserGameState(100, 0.5, 1)
    defenders = (UserGameState(10, 0.5), UserGameState(10, 0.5))
    won = resolve_pk_settlement(
        attacker,
        defenders,
        win_roll=0,
        random_num=0.6,
    )
    lost = resolve_pk_settlement(
        attacker,
        defenders,
        win_roll=1,
        random_num=0.6,
    )
    single = resolve_pk_settlement(
        attacker,
        defenders[:1],
        win_roll=0,
        random_num=0.6,
    )
    precise = resolve_pk_settlement(
        attacker,
        defenders[:1],
        win_roll=0,
        random_num=0.101,
    )
    mixed_targets = resolve_pk_settlement(
        attacker,
        (UserGameState(100, 0.5, 1), defenders[1]),
        win_roll=0,
        random_num=0.6,
    )
    lost_title = resolve_pk_settlement(
        UserGameState(25.4, 0.5, 1),
        defenders[:1],
        win_roll=1,
        random_num=0.3,
    )

    assert (
        won.attacker.length_change,
        tuple(p.length_change for p in won.defenders),
    ) == (
        1.2,
        (-0.6, -0.6),
    )
    assert won.attacker.final.win_probability == 0.49
    assert [item.final.win_probability for item in won.defenders] == [0.51, 0.51]
    assert (
        lost.attacker.length_change,
        tuple(p.length_change for p in lost.defenders),
    ) == (
        -2.4,
        (0.3, 0.3),
    )
    assert single.attacker.length_change == 0.6
    assert precise.attacker.length_change == 0.101
    assert tuple(p.length_change for p in mixed_targets.defenders) == (-1.2, -0.6)
    for battle in (won, lost, single, precise):
        assert all(
            p.final.challenge_tier == 0 and not p.status for p in battle.defenders
        )
    assert (
        lost_title.attacker.base.length,
        lost_title.attacker.final.length,
        lost_title.attacker.final.challenge_tier,
    ) == (24.8, 19.8, 0)


def test_xnn_probability_and_world_boundaries() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        LengthState,
        apply_world_locked_delta,
        classify_length,
        feminization_probability,
        is_xnn,
    )

    assert classify_length(5.0) is LengthState.NORMAL
    assert all(is_xnn(length) for length in (4.999, 1.0, 0.001))
    assert classify_length(4.999) is LengthState.XNN
    assert classify_length(-0.001) is LengthState.GIRL
    assert [
        feminization_probability(total) for total in (0.0, 200.0, 400.0, 1000.0, 1200.0)
    ] == [0.0, 0.0, 0.25, 1.0, 1.0]
    assert apply_world_locked_delta(0.5, -1.5) == 0.001
    assert apply_world_locked_delta(-0.5, 1.5) == -0.001


def test_interaction_volume_resolves_warning_and_feminization() -> None:
    from nonebot_plugin_impart_plus.impart.core import resolve_interaction_volume

    warning = resolve_interaction_volume(
        4.0,
        190.0,
        20.0,
        feminization_roll=0.5,
    )
    converted_on_crossing = resolve_interaction_volume(
        4.0,
        190.0,
        20.0,
        feminization_roll=0.0,
    )
    probability_boundary = [
        resolve_interaction_volume(
            4.0,
            300.0,
            100.0,
            feminization_roll=roll,
        ).feminized
        for roll in (0.249, 0.25)
    ]
    feminized_low = resolve_interaction_volume(
        0.001,
        990.0,
        20.0,
        feminization_roll=0.999,
    )
    feminized_high = resolve_interaction_volume(
        4.999,
        990.0,
        20.0,
        feminization_roll=0.999,
    )
    ignored = resolve_interaction_volume(
        5.0,
        990.0,
        20.0,
        feminization_roll=None,
    )

    assert warning.risk_warning
    assert not warning.feminized
    assert warning.total == 210.0
    assert converted_on_crossing.feminized
    assert not converted_on_crossing.risk_warning
    assert probability_boundary == [True, False]
    assert feminized_low.feminized
    assert feminized_low.length == -4.999
    assert feminized_high.feminized
    assert feminized_high.length == -0.001
    assert ignored.length == 5.0
    assert not ignored.feminized


def test_pk_world_lock_reports_actual_loss_and_xnn_entry() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        UserGameState,
        resolve_pk_settlement,
    )

    locked = resolve_pk_settlement(
        UserGameState(6.0, 0.5),
        (UserGameState(0.5, 0.5),),
        win_roll=0.0,
        random_num=1.5,
    )
    entered = resolve_pk_settlement(
        UserGameState(10.0, 0.5),
        (UserGameState(6.0, 0.5),),
        win_roll=0.0,
        random_num=1.5,
    )

    assert locked.defenders[0].base.length == 0.001
    assert locked.defenders[0].status == ""
    assert locked.defenders[0].length_change == -0.499
    assert entered.defenders[0].base.length == 4.5
    assert entered.defenders[0].status == "length_near_zero"
