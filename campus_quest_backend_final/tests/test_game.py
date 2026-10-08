import config
import pytest

from game import distance_m, process_location, public_state


def make_game():
    return {
        "game_id": "test-game",
        "player_name": "Tester",
        "phase": "WAITING_FOR_CHECKPOINT_3",
        "reached": [],
        "boosts": {},
        "deadline": None,
        "message_queue": [],
        "last_location": None,
        "started_at": None,
    }


@pytest.fixture(autouse=True)
def restore_config():
    original = {
        i: (
            config.GAME_CONFIG["checkpoints"][i]["latitude"],
            config.GAME_CONFIG["checkpoints"][i]["longitude"],
        )
        for i in config.GAME_CONFIG["checkpoints"]
    }
    yield
    for i, (lat, lon) in original.items():
        config.GAME_CONFIG["checkpoints"][i]["latitude"] = lat
        config.GAME_CONFIG["checkpoints"][i]["longitude"] = lon


def test_distance_same_point_is_zero():
    assert distance_m(22.0, 75.0, 22.0, 75.0) == pytest.approx(0.0)


def test_checkpoint_3_starts_seven_minute_phase():
    game = make_game()

    process_location(
        game,
        22.68041805437934,
        75.88003275723203,
        5,
    )

    assert game["phase"] == "FIND_WAND_AND_BROOM"
    assert game["deadline"] is not None
    assert game["reached"] == [3]


def test_checkpoint_2_gets_boost_when_reached():
    game = make_game()

    process_location(
        game,
        22.68041805437934,
        75.88003275723203,
        5,
    )
    process_location(
        game,
        22.681073904231067,
        75.878925999408,
        5,
    )

    assert 2 in game["reached"]
    assert "4" in game["boosts"]


def test_checkpoint_4_gets_boost_when_reached():
    game = make_game()

    process_location(
        game,
        22.68041805437934,
        75.88003275723203,
        5,
    )
    process_location(
        game,
        22.681496434563755,
        75.88100346491773,
        5,
    )

    assert 4 in game["reached"]
    assert "2" in game["boosts"]


def test_both_2_and_4_start_five_minute_phase():
    game = make_game()

    process_location(game, 22.68041805437934, 75.88003275723203, 5)
    process_location(game, 22.681073904231067, 75.878925999408, 5)
    process_location(game, 22.681496434563755, 75.88100346491773, 5)

    assert set(game["reached"]) == {2, 3, 4}
    assert game["phase"] == "FIND_SHIELD_AND_ARTIFACTS"
    assert game["deadline"] is not None


def test_both_1_and_5_win():
    game = make_game()

    process_location(game, 22.68041805437934, 75.88003275723203, 5)
    process_location(game, 22.681073904231067, 75.878925999408, 5)
    process_location(game, 22.681496434563755, 75.88100346491773, 5)
    process_location(game, 22.681686603215834, 75.87866723631592, 5)
    process_location(game, 22.682554447540795, 75.88115789942242, 5)

    assert game["phase"] == "WON"


def test_poor_accuracy_does_not_trigger_checkpoint():
    game = make_game()

    process_location(
        game,
        22.68041805437934,
        75.88003275723203,
        101,
    )

    assert game["phase"] == "WAITING_FOR_CHECKPOINT_3"
    assert game["reached"] == []


def test_public_state_does_not_expose_coordinates():
    game = make_game()
    state = public_state(game)

    text = repr(state)

    # Coordinates are not present in the public checkpoint payload.
    assert "22.68041805437934" not in text
    assert "75.88003275723203" not in text


def test_normal_radius_is_25m():
    assert config.GAME_CONFIG["checkpoint_radius_m"] == 25.0


def test_boost_radius_is_50m():
    assert (
        config.GAME_CONFIG["checkpoint_radius_m"]
        + config.GAME_CONFIG["boost_radius_extra_m"]
        == 50.0
    )
