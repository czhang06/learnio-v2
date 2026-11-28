"""Accounts: tokens from the frontend, enrolment, saved questions, admin role."""

import pytest

from app.config import settings
from app.models import User


def test_guests_have_no_account(client):
    assert client.get("/api/me").status_code == 401


def test_first_request_creates_the_user(client, token, db_session):
    r = client.get("/api/me", headers=token("google-1", "ada@example.com", name="Ada"))
    assert r.status_code == 200
    body = r.json()
    assert (body["email"], body["name"], body["is_admin"], body["courses"]) == ("ada@example.com", "Ada", False, [])
    assert db_session.query(User).count() == 1
    client.get("/api/me", headers=token("google-1", "ada@example.com", name="Ada"))
    assert db_session.query(User).count() == 1


def test_profile_changes_are_picked_up(client, token):
    client.get("/api/me", headers=token("g", "old@example.com"))
    assert client.get("/api/me", headers=token("g", "new@example.com")).json()["email"] == "new@example.com"


@pytest.mark.parametrize(
    "headers",
    [
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer not-a-jwt"},
    ],
)
def test_malformed_tokens_are_rejected(client, headers):
    assert client.get("/api/me", headers=headers).status_code == 401


def test_tokens_must_be_signed_with_the_shared_secret(client, token):
    assert client.get("/api/me", headers=token(secret="someone-else-0123456789abcdef-0123456789")).status_code == 401


def test_expired_tokens_are_rejected(client, token):
    r = client.get("/api/me", headers=token(expires_in=-10))
    assert r.status_code == 401
    assert "expired" in r.json()["detail"].lower()


def test_without_a_secret_everyone_is_a_guest(client, token, monkeypatch):
    monkeypatch.setattr(settings, "auth_api_secret", None)
    assert client.get("/api/me", headers=token()).status_code == 401


def test_admin_emails_get_the_admin_role(client, token, monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "Boss@Example.com, other@example.com")
    assert client.get("/api/me", headers=token("b", "boss@example.com")).json()["is_admin"] is True
    monkeypatch.setattr(settings, "admin_emails", "")
    assert client.get("/api/me", headers=token("b", "boss@example.com")).json()["is_admin"] is False


def test_admin_accounts_can_write_in_a_locked_demo(client, token, monkeypatch):
    monkeypatch.setattr(settings, "admin_key", "s3cret")
    monkeypatch.setattr(settings, "admin_emails", "boss@example.com")
    body = {"code": "CS101"}
    assert client.post("/api/courses", json=body, headers=token("u", "user@example.com")).status_code == 403
    assert client.post("/api/courses", json=body, headers=token("b", "boss@example.com")).status_code == 201
    assert client.post("/api/courses", json={"code": "CS102"}, headers={"X-Admin-Key": "s3cret"}).status_code == 201


def test_enrolment(client, token, make_course):
    make_course("CS101")
    make_course("MATH200")
    me = token()
    assert client.put("/api/me/courses/MATH200", headers=me).status_code == 204
    assert client.put("/api/me/courses/MATH200", headers=me).status_code == 204  # idempotent
    assert client.put("/api/me/courses/CS101", headers=me).status_code == 204
    assert [c["code"] for c in client.get("/api/me", headers=me).json()["courses"]] == ["CS101", "MATH200"]
    assert client.delete("/api/me/courses/CS101", headers=me).status_code == 204
    assert [c["code"] for c in client.get("/api/me", headers=me).json()["courses"]] == ["MATH200"]
    assert client.put("/api/me/courses/NOPE", headers=me).status_code == 404


def test_two_accounts_see_different_home_pages(client, token, make_course):
    """Phase 3 done-when, part 1: each account has its own courses."""
    make_course("CS101")
    make_course("MATH200")
    ada, bob = token("ada", "ada@example.com"), token("bob", "bob@example.com")
    client.put("/api/me/courses/CS101", headers=ada)
    client.put("/api/me/courses/MATH200", headers=bob)
    assert [c["code"] for c in client.get("/api/me", headers=ada).json()["courses"]] == ["CS101"]
    assert [c["code"] for c in client.get("/api/me", headers=bob).json()["courses"]] == ["MATH200"]


def test_saved_questions(client, token, make_course, add_questions):
    cs = make_course("CS101")
    other = make_course("MATH200")
    q1, q2 = add_questions(cs, 2)
    (q3,) = add_questions(other, 1)
    me = token()
    for q in (q1, q3, q1):
        assert client.put(f"/api/me/saved/{q}", headers=me).status_code == 204
    assert {q["id"] for q in client.get("/api/me/saved", headers=me).json()} == {q1, q3}
    assert [q["id"] for q in client.get("/api/me/saved", params={"course_code": "CS101"}, headers=me).json()] == [q1]
    assert client.delete(f"/api/me/saved/{q1}", headers=me).status_code == 204
    assert [q["id"] for q in client.get("/api/me/saved", headers=me).json()] == [q3]
    assert client.put("/api/me/saved/99999", headers=me).status_code == 404
    assert client.get("/api/me/saved", headers=token("someone-else")).json() == []
