"""Watchlist service and endpoint regression tests."""

from datetime import datetime, timedelta, timezone
from uuid import UUID
import pytest
from app import create_app, db
from models import Film, User, WatchlistEntry
from services.collection_service import FilmNotFoundError
from services.watchlist_service import (
    add_to_watchlist, get_watchlist, remove_from_watchlist,
    AlreadyInWatchlistError, NotInWatchlistError,
)


@pytest.fixture
def app():
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    with app.app_context():
        film = Film(title="Paddington 2", year=2017, genre="Comedy")
        db.session.add(film)
        db.session.commit()
        return film.id


def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):
    with app.app_context():
        fake_film_id = "00000000-0000-0000-0000-000000000000"

        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=fake_film_id)

        assert WatchlistEntry.query.count() == 0


def test_add_to_watchlist_persists_uuid_and_public_default(app, sample_user, sample_film):
    with app.app_context():
        entry = add_to_watchlist(sample_user, sample_film)
        assert str(UUID(entry.film_id)) == sample_film
        entry_id = entry.id
        db.session.expire_all()
        persisted = db.session.get(WatchlistEntry, entry_id)
        assert persisted.user_id == sample_user
        assert persisted.film_id == sample_film
        assert persisted.public is True


def test_add_to_watchlist_duplicate_raises(app, sample_user, sample_film):
    with app.app_context():
        add_to_watchlist(sample_user, sample_film)
        with pytest.raises(AlreadyInWatchlistError):
            add_to_watchlist(sample_user, sample_film)
        assert WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).count() == 1


def test_same_film_can_belong_to_two_users(app, sample_user, sample_film):
    """Deduplication must be scoped to the owner, not the whole catalog."""
    with app.app_context():
        other = User(username="other", email="other@example.com")
        db.session.add(other)
        db.session.commit()
        add_to_watchlist(sample_user, sample_film)
        add_to_watchlist(other.id, sample_film)
        assert WatchlistEntry.query.filter_by(film_id=sample_film).count() == 2


def test_remove_from_watchlist_preserves_other_users_entry(app, sample_user, sample_film):
    with app.app_context():
        other = User(username="other", email="other@example.com")
        db.session.add(other)
        db.session.commit()
        add_to_watchlist(sample_user, sample_film)
        add_to_watchlist(other.id, sample_film)

        assert remove_from_watchlist(sample_user, sample_film) is True
        assert get_watchlist(sample_user) == []
        assert len(get_watchlist(other.id)) == 1
        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(sample_user, sample_film)


def test_watchlist_returns_newest_first_with_title_tiebreak(app, sample_user):
    with app.app_context():
        films = [Film(title=title) for title in ["Alien", "Zodiac", "Arrival"]]
        db.session.add_all(films)
        db.session.commit()
        now = datetime.now(timezone.utc)
        for film, added in zip(films, [now - timedelta(days=1), now, now]):
            db.session.add(WatchlistEntry(
                user_id=sample_user, film_id=film.id, date_added=added
            ))
        db.session.commit()
        assert [film["title"] for film in get_watchlist(sample_user)] == [
            "Arrival", "Zodiac", "Alien"
        ]


@pytest.mark.parametrize("public", [True, False])
def test_add_endpoint_honors_explicit_visibility(app, sample_user, sample_film, public):
    client = app.test_client()
    response = client.post(f"/watchlist/{sample_user}/add", json={
        "film_id": sample_film, "public": public,
    })
    assert response.status_code == 201
    assert response.get_json()["public"] is public
    result = client.get(f"/watchlist/{sample_user}")
    assert result.status_code == 200
    assert result.get_json()[0]["id"] == sample_film
    assert result.get_json()[0]["public"] is public


@pytest.mark.parametrize("public", ["false", 0, 1, None])
def test_add_endpoint_rejects_non_boolean_visibility(app, sample_user, sample_film, public):
    response = app.test_client().post(f"/watchlist/{sample_user}/add", json={
        "film_id": sample_film, "public": public,
    })
    assert response.status_code == 400
    with app.app_context():
        assert WatchlistEntry.query.count() == 0


def test_endpoint_add_duplicate_missing_and_remove(app, sample_user, sample_film):
    client = app.test_client()
    endpoint = f"/watchlist/{sample_user}"
    assert client.post(f"{endpoint}/add", json={}).status_code == 400
    missing = client.post(f"{endpoint}/add", json={
        "film_id": "00000000-0000-0000-0000-000000000000",
    })
    assert missing.status_code == 404
    created = client.post(f"{endpoint}/add", json={"film_id": sample_film})
    assert created.status_code == 201
    assert created.get_json()["public"] is True
    duplicate = client.post(f"{endpoint}/add", json={"film_id": sample_film})
    assert duplicate.status_code == 409
    assert len(client.get(endpoint).get_json()) == 1
    assert client.delete(f"{endpoint}/remove", json={}).status_code == 400
    removed = client.delete(f"{endpoint}/remove", json={"film_id": sample_film})
    assert removed.status_code == 200
    assert removed.get_json() == {"removed": True}
    assert client.get(endpoint).get_json() == []
    assert client.delete(
        f"{endpoint}/remove", json={"film_id": sample_film}
    ).status_code == 404
