"""
routes/watchlist.py — CineLog (feature/watchlist branch)

Endpoints for the watchlist feature.
"""

from flask import Blueprint, jsonify, request
from services.watchlist_service import (
    add_to_watchlist, get_watchlist, remove_from_watchlist,
    AlreadyInWatchlistError, NotInWatchlistError,
)
from services.collection_service import FilmNotFoundError

watchlist_bp = Blueprint("watchlist", __name__)


@watchlist_bp.route("/<user_id>", methods=["GET"])
def view_watchlist(user_id):
    """GET /watchlist/<user_id> — Return the user's watchlist."""
    films = get_watchlist(user_id)
    return jsonify(films)


@watchlist_bp.route("/<user_id>/add", methods=["POST"])
def add_film(user_id):
    """
    POST /watchlist/<user_id>/add

    Body: { "film_id": "<film UUID>", "public": true }
    The public field is optional and defaults to true.
    """
    data = request.get_json()
    if not isinstance(data, dict) or "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400

    public = data.get("public", True)
    if not isinstance(public, bool):
        return jsonify({"error": "public must be a JSON boolean"}), 400

    try:
        entry = add_to_watchlist(user_id=user_id, film_id=data["film_id"], public=public)
    except FilmNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    except AlreadyInWatchlistError as error:
        return jsonify({"error": str(error)}), 409
    return jsonify(entry.to_dict()), 201


@watchlist_bp.route("/<user_id>/remove", methods=["DELETE"])
def remove_film(user_id):
    """DELETE /watchlist/<user_id>/remove with a film_id JSON field."""
    data = request.get_json()
    if not isinstance(data, dict) or "film_id" not in data:
        return jsonify({"error": "film_id is required"}), 400

    try:
        remove_from_watchlist(user_id=user_id, film_id=data["film_id"])
    except NotInWatchlistError as error:
        return jsonify({"error": str(error)}), 404
    return jsonify({"removed": True}), 200
