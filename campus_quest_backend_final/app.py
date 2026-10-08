from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import ADMIN_TOKEN
from db import init_db, create_game, get_game, save_game
from game import (
    GameError,
    start_game,
    process_location,
    public_state,
    reset_game,
    list_checkpoints,
    update_checkpoint,
)

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)
init_db()


def get_existing_game(game_id):
    game = get_game(game_id)
    if game is None:
        return None, (jsonify({"error": "Game not found"}), 404)
    from game import expire_if_needed
    if expire_if_needed(game):
        save_game(game)
    return game, None


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "campus-quest-backend"})


@app.post("/api/game/start")
def start():
    body = request.get_json(silent=True) or {}
    player_name = str(body.get("player_name", "")).strip()

    if not player_name:
        return jsonify({"error": "player_name is required"}), 400
    if len(player_name) > 40:
        return jsonify({"error": "player_name must be 40 characters or fewer"}), 400

    game_id = create_game(player_name)
    game = start_game(get_game(game_id))
    state = public_state(game)
    save_game(game)
    return jsonify(state), 201


@app.get("/api/game/<game_id>")
def get_state(game_id):
    game, error = get_existing_game(game_id)
    if error:
        return error

    # Calling public_state may consume queued messages. Persist that change.
    state = public_state(game)
    save_game(game)
    return jsonify(state)


@app.post("/api/game/<game_id>/location")
def location(game_id):
    game, error = get_existing_game(game_id)
    if error:
        return error

    body = request.get_json(silent=True) or {}

    try:
        latitude = float(body["latitude"])
        longitude = float(body["longitude"])
        accuracy = float(body.get("accuracy", 0))
    except (KeyError, TypeError, ValueError):
        return jsonify({
            "error": "latitude and longitude are required numbers"
        }), 400

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return jsonify({"error": "Invalid latitude/longitude"}), 400

    if accuracy < 0:
        return jsonify({"error": "accuracy cannot be negative"}), 400

    try:
        game = process_location(
            game,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
        )
        state = public_state(game)
        save_game(game)
        return jsonify(state)
    except GameError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/game/<game_id>/reset")
def reset(game_id):
    game, error = get_existing_game(game_id)
    if error:
        return error

    game = reset_game(game)
    state = public_state(game)
    save_game(game)
    return jsonify(state)


def admin_ok():
    return bool(ADMIN_TOKEN) and request.headers.get("X-Admin-Token") == ADMIN_TOKEN


@app.get("/api/admin/checkpoints")
def admin_checkpoints():
    if not admin_ok():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"checkpoints": list_checkpoints()})


@app.put("/api/admin/checkpoints/<int:checkpoint_id>")
def admin_update_checkpoint(checkpoint_id):
    if not admin_ok():
        return jsonify({"error": "Unauthorized"}), 401

    body = request.get_json(silent=True) or {}

    try:
        result = update_checkpoint(checkpoint_id, body)
        return jsonify(result)
    except GameError as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
