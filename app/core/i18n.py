"""
Semptify internationalization (i18n) layer.

Loads per-locale JSON catalogs from app/translations/ and exposes:
  - gettext(key, locale=None, request=None, **kwargs)
  - ngettext(singular, plural, n, locale=None, request=None, **kwargs)
  - get_locale(request=None)

Locale resolution order:
  1. Explicit locale argument
  2. Cookie: semptify_locale
  3. Accept-Language header (base code only)
  4. DEFAULT_LOCALE env var
  5. "en"

Missing translations fall back to English. Translators can mark a catalog
with {"_meta": {"status": "human_reviewed"}} once reviewed.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from jinja2 import pass_context

logger = logging.getLogger(__name__)

LOCALES_DIR = Path(__file__).resolve().parent.parent / "translations"

DEFAULT_LOCALE = "en"

SUPPORTED_LOCALES: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "so": "Somali",
    "hmn": "Hmong",
    "ar": "Arabic",
    "am": "Amharic",
    "ti": "Tigrinya",
    "zh": "Mandarin",
    "fr": "French",
    "de": "German",
    "ko": "Korean",
    "ja": "Japanese",
    "pt": "Portuguese",
    "it": "Italian",
}


class I18n:
    """Singleton JSON-based catalog loader and translation helper."""

    _instance: "I18n | None" = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "I18n":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        locales_dir: Path | None = None,
        default_locale: str = DEFAULT_LOCALE,
    ) -> None:
        if self._initialized:
            return
        self.locales_dir = locales_dir or LOCALES_DIR
        self.default_locale = default_locale
        self._catalogs: dict[str, dict[str, Any]] = {}
        self._load_catalogs()
        self._initialized = True

    def _load_catalogs(self) -> None:
        """Load all supported locale files; missing files become empty catalogs."""
        for locale in SUPPORTED_LOCALES:
            path = self.locales_dir / f"{locale}.json"
            catalog: dict[str, Any] = {}
            if path.exists():
                try:
                    catalog = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Failed to load locale %s: %s", locale, exc)
                    catalog = {}
            self._catalogs[locale] = catalog
        self._catalogs.setdefault(self.default_locale, {})

    def reload(self) -> None:
        """Reload catalogs from disk; useful in dev and tests."""
        self._initialized = False
        self._load_catalogs()

    @staticmethod
    def _base_locale(locale: str) -> str:
        """Return the base language code for regional variants (es-US -> es)."""
        return locale.split("-", 1)[0].lower()

    def get_locale(self, request: Any | None = None) -> str:
        """Resolve the best locale for the current request."""
        if request is not None:
            cookie = request.cookies.get("semptify_locale")
            if cookie and cookie in SUPPORTED_LOCALES:
                return cookie

            header = request.headers.get("accept-language", "")
            if header:
                # Accept-Language: es-US,es;q=0.9,en;q=0.8
                primary = header.split(",")[0].strip().split(";")[0].strip()
                base = self._base_locale(primary)
                if base in SUPPORTED_LOCALES:
                    return base

        env_locale = os.getenv("DEFAULT_LOCALE", "")
        if env_locale in SUPPORTED_LOCALES:
            return env_locale

        return self.default_locale

    def translate(
        self,
        key: str,
        locale: str | None = None,
        request: Any | None = None,
        **kwargs: Any,
    ) -> str:
        """Return the translated string for key, falling back to English."""
        if locale is None:
            locale = self.get_locale(request)

        value: Any = None
        for loc in (locale, self._base_locale(locale), self.default_locale):
            catalog = self._catalogs.get(loc, {})
            value = catalog.get(key)
            if value is not None:
                break

        if value is None:
            value = key

        if kwargs and isinstance(value, str):
            try:
                value = value.format(**kwargs)
            except (KeyError, ValueError, IndexError):
                pass

        return str(value)

    def ntranslate(
        self,
        singular: str,
        plural: str,
        n: int,
        locale: str | None = None,
        request: Any | None = None,
        **kwargs: Any,
    ) -> str:
        """Return singular or plural translation based on n."""
        key = singular if n == 1 else plural
        return self.translate(key, locale=locale, request=request, **kwargs)

    def list_locales(self) -> list[str]:
        """Return supported locale codes."""
        return list(SUPPORTED_LOCALES.keys())

    def catalog_status(self, locale: str) -> str:
        """Return the review status of a catalog ('human_reviewed', 'machine', 'stub')."""
        catalog = self._catalogs.get(locale, {})
        meta = catalog.get("_meta", {})
        return meta.get("status", "stub")


def get_locale(request: Any | None = None) -> str:
    return I18n().get_locale(request)


def gettext(key: str, locale: str | None = None, request: Any | None = None, **kwargs: Any) -> str:
    return I18n().translate(key, locale=locale, request=request, **kwargs)


def ngettext(
    singular: str,
    plural: str,
    n: int,
    locale: str | None = None,
    request: Any | None = None,
    **kwargs: Any,
) -> str:
    return I18n().ntranslate(singular, plural, n, locale=locale, request=request, **kwargs)


@pass_context
def _jinja2_gettext(context: Any, key: str, **kwargs: Any) -> str:
    """Jinja2 global `_()` that reads the request from template context."""
    request = context.get("request")
    return I18n().translate(key, request=request, **kwargs)


# Module-level singleton — kept for callers that want to import the instance directly.
i18n = I18n()
