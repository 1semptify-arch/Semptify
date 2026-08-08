"""Tests for app.core.i18n."""

import json
from pathlib import Path

import pytest

from app.core.i18n import I18n, SUPPORTED_LOCALES, _jinja2_gettext, get_locale, gettext, ngettext


class _FakeRequest:
    """Minimal request stand-in for locale detection tests."""

    def __init__(self, cookies=None, headers=None):
        self.cookies = cookies or {}
        self.headers = headers or {}


def _make_i18n(tmp_path, catalog):
    """Create a fresh I18n instance pointing at a temporary catalog."""
    # Reset singleton so each test gets a clean loader.
    I18n._instance = None
    locales_dir = tmp_path / "translations"
    locales_dir.mkdir()
    for locale, data in catalog.items():
        (locales_dir / f"{locale}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    return I18n(locales_dir=locales_dir)


def test_supported_locales_includes_priority_languages():
    assert "en" in SUPPORTED_LOCALES
    assert "es" in SUPPORTED_LOCALES
    assert "so" in SUPPORTED_LOCALES
    assert "hmn" in SUPPORTED_LOCALES
    assert "ar" in SUPPORTED_LOCALES


def test_loads_english_catalog(tmp_path):
    i18n = _make_i18n(tmp_path, {
        "en": {"welcome.cta": "Get Started", "nav.record": "Record"},
    })
    assert i18n.translate("welcome.cta") == "Get Started"
    assert i18n.translate("nav.record") == "Record"


def test_falls_back_to_english_for_missing_key(tmp_path):
    i18n = _make_i18n(tmp_path, {
        "en": {"welcome.cta": "Get Started"},
        "es": {"_meta": {"locale": "es", "status": "stub"}},
    })
    assert i18n.translate("welcome.cta", locale="es") == "Get Started"


def test_uses_spanish_translation_when_available(tmp_path):
    i18n = _make_i18n(tmp_path, {
        "en": {"welcome.cta": "Get Started"},
        "es": {"welcome.cta": "Comenzar"},
    })
    assert i18n.translate("welcome.cta", locale="es") == "Comenzar"


def test_locale_from_cookie(tmp_path):
    i18n = _make_i18n(tmp_path, {"en": {}, "so": {}})
    request = _FakeRequest(cookies={"semptify_locale": "so"})
    assert i18n.get_locale(request) == "so"


def test_locale_from_accept_language_header(tmp_path):
    i18n = _make_i18n(tmp_path, {"en": {}, "es": {}})
    request = _FakeRequest(headers={"accept-language": "es-US,es;q=0.9,en;q=0.8"})
    assert i18n.get_locale(request) == "es"


def test_unsupported_locale_defaults_to_english(tmp_path):
    i18n = _make_i18n(tmp_path, {"en": {}})
    request = _FakeRequest(headers={"accept-language": "xx-XX"})
    assert i18n.get_locale(request) == "en"


def test_translate_with_format_kwargs(tmp_path):
    i18n = _make_i18n(tmp_path, {
        "en": {"greeting": "Hello, {name}!"},
    })
    assert i18n.translate("greeting", name="Ada") == "Hello, Ada!"


def test_ntranslate_singular_and_plural(tmp_path):
    i18n = _make_i18n(tmp_path, {
        "en": {
            "items.one": "One item",
            "items.other": "{count} items",
        },
    })
    assert i18n.ntranslate("items.one", "items.other", 1, count=1) == "One item"
    assert i18n.ntranslate("items.one", "items.other", 5, count=5) == "5 items"


def test_jinja2_global_reads_request_locale(tmp_path):
    i18n = _make_i18n(tmp_path, {
        "en": {"welcome.cta": "Get Started"},
        "es": {"welcome.cta": "Comenzar"},
    })
    request = _FakeRequest(cookies={"semptify_locale": "es"})
    context = {"request": request}
    assert _jinja2_gettext(context, "welcome.cta") == "Comenzar"


def test_module_level_helpers_use_singleton(tmp_path):
    I18n._instance = None
    locales_dir = tmp_path / "translations"
    locales_dir.mkdir()
    (locales_dir / "en.json").write_text(
        json.dumps({"welcome.cta": "Get Started"}), encoding="utf-8"
    )
    I18n(locales_dir=locales_dir)
    assert gettext("welcome.cta") == "Get Started"
    assert get_locale() == "en"
    assert ngettext("one", "many", 2) == "many"


@pytest.mark.anyio
async def test_get_current_locale_endpoint(client):
    response = await client.get("/api/i18n/locale")
    assert response.status_code == 200
    data = response.json()
    assert data["locale"] == "en"
    assert "en" in data["supported_locales"]
    assert "es" in data["supported_locales"]


@pytest.mark.anyio
async def test_set_locale_endpoint_sets_cookie_and_redirects(client):
    response = await client.post(
        "/api/i18n/set-locale",
        data={"locale": "es"},
        headers={"referer": "http://test/portal"},
    )
    assert response.status_code == 302
    assert "semptify_locale=es" in response.headers.get("set-cookie", "")
    assert response.headers["location"] == "/portal"


@pytest.mark.anyio
async def test_set_locale_endpoint_rejects_unsupported_locale(client):
    response = await client.post(
        "/api/i18n/set-locale",
        data={"locale": "xx"},
        headers={"referer": "http://test/portal"},
    )
    assert response.status_code == 400
