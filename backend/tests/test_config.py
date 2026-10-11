"""Tests for deployment configuration handling.

The URL normalisation is the one thing between a working first deploy and an
afternoon of reading SQLAlchemy stack traces, so it is pinned here.
"""

from __future__ import annotations

import pytest

from app.config import Settings, normalize_database_url


class TestNormalizeDatabaseUrl:
    def test_rewrites_heroku_style_postgres_scheme(self):
        """Render and Railway still hand out postgres://, which SQLAlchemy rejects."""
        assert normalize_database_url("postgres://u:p@host:5432/db") == (
            "postgresql+psycopg://u:p@host:5432/db"
        )

    def test_rewrites_bare_postgresql_scheme(self):
        """Neon and Supabase give postgresql://, which resolves to psycopg2 (not installed)."""
        assert normalize_database_url("postgresql://u:p@host:5432/db") == (
            "postgresql+psycopg://u:p@host:5432/db"
        )

    def test_leaves_an_explicit_driver_alone(self):
        url = "postgresql+psycopg://u:p@host:5432/db"
        assert normalize_database_url(url) == url

    def test_does_not_touch_a_psycopg2_url_the_user_chose_deliberately(self):
        url = "postgresql+psycopg2://u:p@host:5432/db"
        assert normalize_database_url(url) == url

    def test_preserves_query_parameters(self):
        """Managed Postgres almost always appends ?sslmode=require."""
        assert normalize_database_url("postgres://u:p@host/db?sslmode=require") == (
            "postgresql+psycopg://u:p@host/db?sslmode=require"
        )

    def test_only_rewrites_the_scheme_not_the_body(self):
        """A password or hostname containing 'postgres' must survive intact."""
        assert normalize_database_url("postgres://u:postgres@postgres.example/db") == (
            "postgresql+psycopg://u:postgres@postgres.example/db"
        )

    def test_leaves_other_databases_alone(self):
        url = "sqlite:///./local.db"
        assert normalize_database_url(url) == url


class TestSettings:
    def test_sqlalchemy_url_applies_normalisation(self):
        settings = Settings(database_url="postgres://u:p@host/db")
        assert settings.sqlalchemy_url.startswith("postgresql+psycopg://")

    def test_origins_default_to_wildcard(self):
        assert Settings().origin_list == ["*"]

    def test_origins_split_on_commas_and_strip_whitespace(self):
        settings = Settings(allowed_origins="https://a.com, https://b.com")
        assert settings.origin_list == ["https://a.com", "https://b.com"]

    def test_empty_entries_are_dropped(self):
        assert Settings(allowed_origins="https://a.com,,  ,").origin_list == ["https://a.com"]

    @pytest.mark.parametrize("value", ["", "   "])
    def test_blank_origins_yield_an_empty_list(self, value):
        assert Settings(allowed_origins=value).origin_list == []
