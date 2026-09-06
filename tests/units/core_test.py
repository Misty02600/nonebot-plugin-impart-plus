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
        CHALLENGE_TIERS,
        UserGameState,
        active_challenge,
        evaluate_state_transition,
        resolve_pk_settlement,
    )

    assert [
        (r.entry, r.target, r.penalty, r.win_multiplier) for r in CHALLENGE_TIERS
    ] == [
        (25, 30, 5, 0.9),
        (300, 320, 20, 0.8),
        (1000, 1050, 50, 0.7),
    ]
    for rule in CHALLENGE_TIERS:
        tier = rule.tier
        reduced = 0.5 * rule.win_multiplier
        cases = (
            (
                rule.entry - 0.1,
                rule.entry,
                tier - 1,
                0.5,
                "challenge_started_low_win",
                rule.entry,
                reduced,
                tier - 1,
            ),
            (
                rule.entry,
                rule.target - 0.001,
                tier - 1,
                reduced,
                "is_challenging",
                rule.target - 0.001,
                reduced,
                tier - 1,
            ),
            (
                rule.target - 0.1,
                rule.target,
                tier - 1,
                reduced,
                "challenge_success_high_win",
                rule.target,
                0.5,
                tier,
            ),
            (
                rule.entry + 0.1,
                rule.entry - 0.1,
                tier - 1,
                reduced,
                "challenge_failed_high_win",
                rule.entry - 0.1 - rule.penalty,
                0.5,
                tier - 1,
            ),
            (
                rule.entry + 0.1,
                rule.entry - 0.1,
                tier,
                0.5,
                "challenge_completed_reduce",
                rule.entry - 0.1 - rule.penalty,
                0.5,
                tier - 1,
            ),
            (
                rule.entry - 0.1,
                rule.target + 0.1,
                tier - 1,
                0.5,
                "challenge_completed",
                rule.target + 0.1,
                0.5,
                tier,
            ),
        )
        for sign in (1, -1):
            for (
                old,
                new,
                held,
                probability,
                status,
                final,
                final_probability,
                final_tier,
            ) in cases:
                result = evaluate_state_transition(
                    UserGameState(sign * old, probability, held),
                    UserGameState(sign * new, probability, held),
                )
                assert result.status == status
                assert result.state.length == pytest.approx(sign * final)
                assert result.state.win_probability == pytest.approx(final_probability)
                assert result.state.challenge_tier == final_tier
                assert result.challenge == (
                    None if status == "is_challenging" else rule
                )
            assert (
                active_challenge(UserGameState(sign * rule.entry, reduced, tier - 1))
                == rule
            )
            held_state = UserGameState(sign * rule.entry, 0.5, tier)
            assert active_challenge(held_state) is None
            assert evaluate_state_transition(held_state, held_state).state == held_state

    # 二阶仍保留乘1.25的浮点路径，改为除0.8会让下一局舍入为0.477。
    completed = resolve_pk_settlement(
        UserGameState(319.9, 0.4, 1),
        (UserGameState(350, 0.5, 2),),
        win_roll=0,
        random_num=0.1,
    )
    following = resolve_pk_settlement(
        completed.attacker.final,
        tuple(p.final for p in completed.defenders),
        win_roll=0,
        random_num=0.1,
    )
    assert completed.attacker.final.challenge_tier == 2
    assert following.attacker.final.win_probability == 0.478


def test_growth_multiplier_uses_the_tier_before_settlement() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        GrowthMode,
        UserGameState,
        resolve_growth_settlement,
    )

    completed = resolve_growth_settlement(
        UserGameState(29.8, 0.45),
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

    assert (
        completed.amount,
        completed.final.length,
        completed.final.challenge_tier,
    ) == (
        0.3,
        30.1,
        1,
    )
    assert (boosted.amount, boosted.final.length) == (0.6, 30.7)
    assert (depth.amount, depth.final.length) == (0.6, -30.6)


def test_higher_tier_pk_and_growth_use_personal_starting_multipliers() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        GrowthMode,
        UserGameState,
        resolve_growth_settlement,
        resolve_pk_settlement,
    )

    for tier, length, count, gain, loss in (
        (2, 500, 3, 2.7, -5.4),
        (3, 1500, 4, 4.8, -9.6),
    ):
        for sign, mode in ((1, GrowthMode.LENGTH), (-1, GrowthMode.DEPTH)):
            actor = UserGameState(sign * length, 0.5, tier)
            for targets in (1, count):
                opponents = tuple(UserGameState(sign * 10, 0.5) for _ in range(targets))
                for roll, expected in (
                    (0, gain * targets / count),
                    (1, loss * targets / count),
                ):
                    result = resolve_pk_settlement(
                        actor, opponents, win_roll=roll, random_num=0.6
                    )
                    assert result.attacker.length_change == pytest.approx(expected)
                    assert result.attacker.final.win_probability == (
                        0.49 if roll == 0 else 0.51
                    )
                    assert all(
                        p.length_change == (-0.6 if roll == 0 else 0.3)
                        for p in result.defenders
                    )
            growth = resolve_growth_settlement(actor, mode, 0.3)
            assert growth.amount == pytest.approx(0.3 * (tier + 1))

    dropped = resolve_pk_settlement(
        UserGameState(1001, 0.5, 3),
        tuple(UserGameState(10, 0.5) for _ in range(4)),
        win_roll=1,
        random_num=0.1,
    )
    assert (
        dropped.attacker.base.length,
        dropped.attacker.final.length,
        dropped.attacker.final.challenge_tier,
    ) == (999.4, 949.4, 2)
    assert dropped.attacker.challenge is not None
    assert dropped.attacker.challenge.penalty == 50


def test_possession_assigns_tier_by_half_and_handles_active_challenge() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        PossessionSettlement,
        PossessionStatus,
        UserGameState,
        resolve_possession,
    )

    actor = UserGameState(-70, 0.6, 1)
    lost_title = resolve_possession(actor, UserGameState(49.998, 0.4, 1))
    kept_title = resolve_possession(actor, UserGameState(49.999, 0.4, 1))
    gained_title = resolve_possession(actor, UserGameState(60, 0.4, 1))

    assert isinstance(lost_title, PossessionSettlement)
    assert (lost_title.half, lost_title.actor.challenge_tier) == (24.999, 0)
    assert (
        lost_title.target.length,
        lost_title.target.challenge_tier,
    ) == (19.999, 0)
    assert lost_title.target_challenge is not None
    assert lost_title.target_challenge.tier == 1
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

    for actor, target, half, actor_tier, target_length, target_tier, probability in (
        (UserGameState(-302, 0.4, 1), UserGameState(280, 0.5, 1), 140, 1, 140, 1, 0.5),
        (UserGameState(-700, 0.5, 2), UserGameState(640, 0.5, 2), 320, 2, 320, 2, 0.5),
        (
            UserGameState(-1020, 0.35, 2),
            UserGameState(900, 0.5, 2),
            450,
            2,
            450,
            2,
            0.5,
        ),
        (
            UserGameState(-2500, 0.5, 3),
            UserGameState(2000, 0.5, 3),
            1000,
            3,
            1000,
            3,
            0.5,
        ),
        (
            UserGameState(-2500, 0.5, 3),
            UserGameState(1500, 0.5, 3),
            750,
            2,
            700,
            2,
            0.5,
        ),
    ):
        result = resolve_possession(actor, target)
        assert isinstance(result, PossessionSettlement)
        assert (
            result.half,
            result.actor.challenge_tier,
            result.target.length,
            result.target.challenge_tier,
        ) == (half, actor_tier, target_length, target_tier)
        assert result.actor.win_probability == pytest.approx(probability)
        if result.target_challenge:
            assert result.target_challenge.tier == target.challenge_tier
        assert (
            resolve_possession(actor, UserGameState(1001, 0.35, 2))
            is PossessionStatus.TARGET_CHALLENGING
        )


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


def test_xnn_pk_uses_personal_reduction_and_starting_state() -> None:
    from nonebot_plugin_impart_plus.impart.core import (
        UserGameState,
        effective_pk_probability,
        resolve_pk_settlement,
    )

    xnn = UserGameState(4.0, 0.5)
    normal = UserGameState(10.0, 0.5)
    won = resolve_pk_settlement(xnn, (normal,), win_roll=0.249, random_num=1.0)
    lost = resolve_pk_settlement(xnn, (normal,), win_roll=0.25, random_num=1.0)
    targeted = resolve_pk_settlement(normal, (xnn,), win_roll=0.3, random_num=1.0)
    defended = resolve_pk_settlement(normal, (xnn,), win_roll=0.5, random_num=1.0)
    assert won.won
    assert not lost.won
    assert (won.attacker.length_change, won.defenders[0].length_change) == (0.25, -1)
    assert (lost.attacker.length_change, lost.defenders[0].length_change) == (-0.5, 0.5)
    assert lost.attacker.final.win_probability == 0.51
    assert effective_pk_probability(3.5, 0.51) == 0.255
    assert targeted.won
    assert (targeted.attacker.length_change, targeted.defenders[0].length_change) == (
        0.5,
        -0.5,
    )
    assert not defended.won
    assert defended.defenders[0].length_change == 0.25

    entered = resolve_pk_settlement(
        UserGameState(5.2, 0.5), (normal,), win_roll=0.9, random_num=1.0
    )
    escaped = resolve_pk_settlement(
        UserGameState(4.75, 0.5), (normal,), win_roll=0.0, random_num=1.0
    )
    assert entered.attacker.length_change == -1.0
    assert entered.attacker.final.length == 4.2
    assert escaped.attacker.length_change == 0.25
    assert escaped.attacker.final.length == 5.0
    assert (
        effective_pk_probability(
            escaped.attacker.final.length, escaped.attacker.final.win_probability
        )
        == 0.49
    )


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
