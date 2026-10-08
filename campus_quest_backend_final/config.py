import os

# FINAL GAME SETTINGS
GAME_CONFIG = {
    # Normal geofence = 25 m.
    "checkpoint_radius_m": 25.0,

    # When one of checkpoints 2/4 is reached, the OTHER one gets
    # +25 m for 3 minutes, so its temporary radius becomes 50 m.
    "boost_radius_extra_m": 25.0,
    "boost_duration_seconds": 180,

    # Phase 1: wand + broom.
    "death_eater_duration_seconds": 420,

    # Phase 2: shield + artifacts.
    "voldemort_duration_seconds": 300,

    # Ignore very poor GPS readings rather than falsely completing a checkpoint.
    "max_location_accuracy_m": 100.0,

    "checkpoints": {
        1: {
            "name": "Ancient Ruins of Akshank",
            "clue": "Ancient ruins of Akshank",
            "latitude": 22.681686603215834,
            "longitude": 75.87866723631592,
        },
        2: {
            "name": "Seasonal Island View",
            "clue": "View of a seasonal island",
            "latitude": 22.681073904231067,
            "longitude": 75.878925999408,
        },
        3: {
            "name": "Cricket Ground",
            "clue": "Let's play cricket",
            "latitude": 22.68041805437934,
            "longitude": 75.88003275723203,
        },
        4: {
            "name": "C-Shaped Building",
            "clue": "'C' shaped building",
            "latitude": 22.681496434563755,
            "longitude": 75.88100346491773,
        },
        5: {
            "name": "Vishesh Jupiter Corner",
            "clue": "Closest corner to Vishesh Jupiter Hospital",
            "latitude": 22.682554447540795,
            "longitude": 75.88115789942242,
        },
    },
}

# Set this environment variable before deployment.
# The fallback is intentionally only for local development.
ADMIN_TOKEN = os.getenv(
    "CAMPUS_QUEST_ADMIN_TOKEN",
    "local-dev-change-this-token",
)
