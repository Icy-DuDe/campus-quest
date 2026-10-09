from datetime import datetime, timezone, timedelta
from math import radians, sin, cos, asin, sqrt

from config import GAME_CONFIG


class GameError(Exception):
    pass


def utc_now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.isoformat()


def parse_iso(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def distance_m(lat1, lon1, lat2, lon2):
    """Return great-circle distance between two GPS points in metres."""
    earth_radius = 6_371_000.0

    p1 = radians(lat1)
    p2 = radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)

    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    a = min(1.0, max(0.0, a))
    return 2 * earth_radius * asin(sqrt(a))


def checkpoint_config(checkpoint_id):
    try:
        return GAME_CONFIG["checkpoints"][int(checkpoint_id)]
    except (KeyError, ValueError, TypeError):
        raise GameError(f"Unknown checkpoint: {checkpoint_id}")


def start_game(game):
    now = utc_now()

    game["phase"] = "WAITING_FOR_CHECKPOINT_3"
    game["started_at"] = iso(now)
    game["deadline"] = None
    game["reached"] = []
    game["boosts"] = {}
    game["message_queue"] = [
        {
            "type": "story",
            "text": (
                "The campus is quiet. Your first clue has appeared: "
                "Let's play cricket."
            ),
        }
    ]
    game["last_location"] = None
    game.pop("_newly_reached", None)

    return game


def set_phase(game, phase, deadline=None):
    game["phase"] = phase
    game["deadline"] = iso(deadline) if deadline else None


def add_message(game, message_type, text):
    game.setdefault("message_queue", []).append({
        "type": message_type,
        "text": text,
    })


def deadline_expired(game, now):
    deadline = parse_iso(game.get("deadline"))
    return deadline is not None and now >= deadline


def activate_phase_one(game, now):
    deadline = now + timedelta(
        seconds=GAME_CONFIG["death_eater_duration_seconds"]
    )
    set_phase(game, "FIND_WAND_AND_BROOM", deadline)

    add_message(
        game,
        "story",
        (
            "Hermione: I have detected Death Eaters approaching IET-DAVV. "
            "They will reach the campus in seven minutes. Find the wand "
            "at Checkpoint 4 and the broom at Checkpoint 2."
        ),
    )
    add_message(
        game,
        "objective",
        "Reach Checkpoints 4 and 2 before the seven-minute timer ends.",
    )


def activate_phase_two(game, now):
    deadline = now + timedelta(
        seconds=GAME_CONFIG["voldemort_duration_seconds"]
    )
    set_phase(game, "FIND_SHIELD_AND_ARTIFACTS", deadline)

    add_message(
        game,
        "story",
        (
            "Death Eater: This changes nothing. In six minutes, "
            "Voldemort will attack this campus."
        ),
    )
    add_message(
        game,
        "story",
        (
            "Hermione: Find the old protection spell at Checkpoint 1 "
            "and the protection artifacts at Checkpoint 5."
        ),
    )
    add_message(
        game,
        "objective",
        "Reach Checkpoints 1 and 5 before the six-minute timer ends.",
    )


def activate_boost_for_other(game, reached_checkpoint, now):
    other = 2 if reached_checkpoint == 4 else 4
    expires = now + timedelta(
        seconds=GAME_CONFIG["boost_duration_seconds"]
    )

    game.setdefault("boosts", {})[str(other)] = {
        "expires_at": iso(expires),
    }

    add_message(
        game,
        "powerup",
        (
            f"Checkpoint {reached_checkpoint} reached. "
            f"Checkpoint {other} has a 3-minute radius boost."
        ),
    )


def effective_radius(game, checkpoint_id, now):
    radius = GAME_CONFIG["checkpoint_radius_m"]
    boost = game.get("boosts", {}).get(str(checkpoint_id))

    if boost:
        expires = parse_iso(boost["expires_at"])
        if now < expires:
            radius += GAME_CONFIG["boost_radius_extra_m"]

    return radius


def expire_if_needed(game, now=None):
    now = now or utc_now()
    if game.get("phase") in {"WON", "GAME_OVER"}:
        return False
    if not deadline_expired(game, now):
        return False
    phase = game.get("phase")
    if phase == "FIND_WAND_AND_BROOM":
        set_phase(game, "GAME_OVER")
        add_message(game, "game_over", "The seven minutes are over. The Death Eaters reached the campus. Game over.")
        return True
    if phase == "FIND_SHIELD_AND_ARTIFACTS":
        set_phase(game, "GAME_OVER")
        add_message(game, "game_over", "The five minutes are over. The campus protection failed. Game over.")
        return True
    return False


def process_location(game, latitude, longitude, accuracy):
    now = utc_now()

    game["last_location"] = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy,
        "received_at": iso(now),
    }

    # Terminal states are immutable.
    if game["phase"] in {"WON", "GAME_OVER"}:
        return game

    # Timer expiry is also applied on GET requests.
    if expire_if_needed(game, now):
        return game

    # Very poor GPS should not accidentally trigger a checkpoint.
    if accuracy > GAME_CONFIG["max_location_accuracy_m"]:
        add_message(
            game,
            "gps_warning",
            (
                "GPS accuracy is currently too low. Move to an open area "
                "and wait for a better location signal."
            ),
        )
        return game

    phase = game["phase"]

    if phase == "WAITING_FOR_CHECKPOINT_3":
        reached = check_and_reach(game, 3, latitude, longitude, now)
        if reached:
            activate_phase_one(game, now)

    elif phase == "FIND_WAND_AND_BROOM":
        newly_reached = []

        for checkpoint_id in (4, 2):
            if checkpoint_id not in game["reached"]:
                if check_and_reach(
                    game,
                    checkpoint_id,
                    latitude,
                    longitude,
                    now,
                ):
                    newly_reached.append(checkpoint_id)

        # Only newly reached checkpoints can activate a boost.
        for checkpoint_id in newly_reached:
            activate_boost_for_other(game, checkpoint_id, now)

        if 2 in game["reached"] and 4 in game["reached"]:
            add_message(
                game,
                "fight",
                (
                    "You raise the wand and take the broom. The Death "
                    "Eaters charge. You hold your ground and defeat them."
                ),
            )
            activate_phase_two(game, now)

    elif phase == "FIND_SHIELD_AND_ARTIFACTS":
        for checkpoint_id in (1, 5):
            if checkpoint_id not in game["reached"]:
                check_and_reach(
                    game,
                    checkpoint_id,
                    latitude,
                    longitude,
                    now,
                )

        if 1 in game["reached"] and 5 in game["reached"]:
            set_phase(game, "WON")
            add_message(
                game,
                "victory",
                (
                    "You speak the ancient protection spell and place the "
                    "artifacts. A shield rises around IET-DAVV. The campus "
                    "is safe. You win!"
                ),
            )

    return game


def check_and_reach(game, checkpoint_id, latitude, longitude, now):
    if checkpoint_id in game["reached"]:
        return False

    cp = checkpoint_config(checkpoint_id)

    if cp["latitude"] == 0.0 and cp["longitude"] == 0.0:
        raise GameError(
            f"Checkpoint {checkpoint_id} coordinates are not configured."
        )

    distance = distance_m(
        latitude,
        longitude,
        cp["latitude"],
        cp["longitude"],
    )

    radius = effective_radius(game, checkpoint_id, now)

    if distance > radius:
        return False

    game["reached"].append(checkpoint_id)

    add_message(
        game,
        "checkpoint",
        f"Checkpoint {checkpoint_id} reached: {cp['name']}.",
    )

    if checkpoint_id == 3:
        add_message(
            game,
            "clue",
            "Hermione appears. The seven-minute countdown begins.",
        )
    elif checkpoint_id == 4:
        add_message(
            game,
            "item",
            "You found the wand: Aetheris.",
        )
    elif checkpoint_id == 2:
        add_message(
            game,
            "item",
            "You found the broom: Vayun.",
        )
    elif checkpoint_id == 1:
        add_message(
            game,
            "item",
            "You found the old protection spell: Kavacha Nivara.",
        )
    elif checkpoint_id == 5:
        add_message(
            game,
            "item",
            "You found the protection artifacts: the Astra Seal and Guardian Ring.",
        )

    return True


def public_checkpoints_for_phase(phase):
    if phase == "WAITING_FOR_CHECKPOINT_3":
        ids = [3]
    elif phase == "FIND_WAND_AND_BROOM":
        ids = [2, 4]
    elif phase == "FIND_SHIELD_AND_ARTIFACTS":
        ids = [1, 5]
    elif phase in {"WON", "GAME_OVER"}:
        ids = [1, 2, 3, 4, 5]
    else:
        ids = []

    return [
        {
            "id": checkpoint_id,
            "name": GAME_CONFIG["checkpoints"][checkpoint_id]["name"],
            "clue": GAME_CONFIG["checkpoints"][checkpoint_id]["clue"],
            "base_radius_m": GAME_CONFIG["checkpoint_radius_m"],
        }
        for checkpoint_id in ids
    ]


def public_state(game):
    now = utc_now()

    remaining = None
    deadline = parse_iso(game.get("deadline"))
    if deadline:
        remaining = max(0, int((deadline - now).total_seconds()))

    boosts = {}
    for checkpoint_id, boost in game.get("boosts", {}).items():
        expires = parse_iso(boost["expires_at"])
        seconds = max(0, int((expires - now).total_seconds()))
        if seconds > 0:
            boosts[int(checkpoint_id)] = {
                "seconds_remaining": seconds,
                "extra_radius_m": GAME_CONFIG["boost_radius_extra_m"],
            }

    messages = list(game.get("message_queue", []))
    game["message_queue"] = []

    return {
        "game_id": game["game_id"],
        "player_name": game["player_name"],
        "phase": game["phase"],
        "reached_checkpoints": sorted(game["reached"]),
        "deadline": game.get("deadline"),
        "seconds_remaining": remaining,
        "boosts": boosts,
        "messages": messages,
        "last_location": game.get("last_location"),
        "checkpoints": public_checkpoints_for_phase(game["phase"]),
    }


def reset_game(game):
    return start_game(game)


def list_checkpoints():
    return [
        {
            "id": checkpoint_id,
            "name": data["name"],
            "clue": data["clue"],
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "radius_m": GAME_CONFIG["checkpoint_radius_m"],
        }
        for checkpoint_id, data in GAME_CONFIG["checkpoints"].items()
    ]


def update_checkpoint(checkpoint_id, body):
    checkpoint_id = int(checkpoint_id)
    cp = checkpoint_config(checkpoint_id)

    allowed = {"name", "clue", "latitude", "longitude"}
    unknown = set(body) - allowed

    if unknown:
        raise GameError(
            f"Unknown fields: {', '.join(sorted(unknown))}"
        )

    name = str(body.get("name", cp["name"])).strip()
    clue = str(body.get("clue", cp["clue"])).strip()

    if not name or not clue:
        raise GameError("name and clue cannot be empty")

    try:
        latitude = float(body.get("latitude", cp["latitude"]))
        longitude = float(body.get("longitude", cp["longitude"]))
    except (TypeError, ValueError):
        raise GameError("latitude and longitude must be numbers")

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise GameError("Invalid latitude/longitude")

    # This endpoint changes the running server's configuration.
    # For the actual competition build, config.py remains the source of truth.
    cp.update({
        "name": name,
        "clue": clue,
        "latitude": latitude,
        "longitude": longitude,
    })

    return {
        "id": checkpoint_id,
        "name": name,
        "clue": clue,
        "latitude": latitude,
        "longitude": longitude,
        "radius_m": GAME_CONFIG["checkpoint_radius_m"],
    }
