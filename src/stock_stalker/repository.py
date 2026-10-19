import json
from pathlib import Path

from platformdirs import user_data_dir

DEFAULT_TICKERS = ("AAPL", "NVDA", "GOOG")
APP_NAME = "Stock Stalker"
THEME_NAME_MAX_LEN = 20
THEME_PATH_SEP = "/"


def default_csv_path() -> Path:
    data_dir = Path(user_data_dir(appname=APP_NAME, appauthor=False))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "my_stock_list.csv"


def default_themes_path() -> Path:
    data_dir = Path(user_data_dir(appname=APP_NAME, appauthor=False))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "themes.json"


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def normalize_theme_name(name: str) -> str:
    return name.strip().upper()


def validate_theme_name(name: str) -> str:
    normalized = normalize_theme_name(name)
    if not normalized or len(normalized) > THEME_NAME_MAX_LEN:
        raise ValueError(f"invalid theme name {name!r}")
    if not all(c.isalnum() or c in "_-" for c in normalized):
        raise ValueError(f"invalid theme name {name!r}")
    return normalized


def split_theme_path(key: str) -> list[str]:
    """Split a stored ``TECH/FAANG`` key into ``["TECH", "FAANG"]``."""
    return [seg for seg in str(key).split(THEME_PATH_SEP) if seg.strip()]


def validate_theme_path(path: str | list[str]) -> list[str]:
    """Normalize a theme path (str ``"TECH/FAANG"`` or list) to validated segments."""
    segments = split_theme_path(path) if isinstance(path, str) else [str(s) for s in path]
    validated = [validate_theme_name(s) for s in segments if str(s).strip()]
    if not validated:
        raise ValueError(f"invalid theme path {path!r}")
    return validated


def format_theme_path(segments: list[str]) -> str:
    """Join validated path segments into the stored ``TECH/FAANG`` key."""
    return THEME_PATH_SEP.join(segments)


def parse_theme_spec(spec: str) -> tuple[list[str], list[str]]:
    """Parse a ``TECH:FAANG:GOOG,NVDA`` spec into ``(path, members)``.

    The final ``:``-separated segment holds the members; the segments before it
    form the theme path (i.e. subfolders). ``=`` may be used in place of the
    final ``:`` to disambiguate, e.g. ``TECH:FAANG=GOOG,NVDA``.
    Members may be comma- and/or whitespace-separated. An empty member list
    (e.g. ``"TECH:"`` or ``"TECH:FAANG:"``) means "delete this (sub)theme".
    """
    if "=" in spec:
        path_part, members_part = spec.split("=", 1)
        path_segments = path_part.split(":")
    else:
        if ":" not in spec:
            raise ValueError(
                f"invalid theme spec {spec!r}, expected 'NAME:TICKER,TICKER,...'"
            )
        parts = spec.split(":")
        path_segments, members_part = parts[:-1], parts[-1]
    path = validate_theme_path(path_segments)
    raw_members = members_part.replace(",", " ").split()
    members: list[str] = []
    for raw in raw_members:
        symbol = normalize_ticker(raw)
        if not symbol or len(symbol) > 12:
            raise ValueError(f"invalid ticker {raw!r} in theme spec {spec!r}")
        if not all(c.isalnum() or c in ".-" for c in symbol):
            raise ValueError(f"invalid ticker {raw!r} in theme spec {spec!r}")
        if symbol not in members:
            members.append(symbol)
    return path, members


class TickerRepository:
    def __init__(self, path: Path | None = None):
        self.path = path or default_csv_path()

    def load(self) -> list[str]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return list(DEFAULT_TICKERS)
        tickers: list[str] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            symbol = normalize_ticker(line)
            if symbol and symbol not in tickers:
                tickers.append(symbol)
        return tickers or list(DEFAULT_TICKERS)

    def save(self, tickers: list[str]) -> list[str]:
        cleaned = [normalize_ticker(t) for t in tickers if t.strip()]
        deduped = list(dict.fromkeys(cleaned))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(deduped), encoding="utf-8")
        return deduped


class ThemeRepository:
    """Persist ``{theme_name: [tickers...]}`` to ``themes.json``.

    Insertion order of the dict defines theme display order.
    Each ticker may belong to at most one theme (enforced here).
    """

    def __init__(self, path: Path | None = None):
        self.path = path or default_themes_path()

    def load(self) -> dict[str, list[str]]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        themes: dict[str, list[str]] = {}
        if isinstance(payload, dict) and isinstance(payload.get("themes"), dict):
            raw_themes = payload["themes"]
            order = payload.get("order")
            names: list[str] = []
            if isinstance(order, list):
                names.extend(str(n) for n in order)
            names.extend(str(n) for n in raw_themes if str(n) not in names)
            for raw_name in names:
                raw_members = raw_themes.get(raw_name, [])
                if not isinstance(raw_members, list):
                    continue
                try:
                    theme = format_theme_path(validate_theme_path(str(raw_name)))
                except ValueError:
                    continue
                members: list[str] = []
                for raw in raw_members:
                    symbol = normalize_ticker(str(raw))
                    if not symbol or len(symbol) > 12:
                        continue
                    if not all(c.isalnum() or c in ".-" for c in symbol):
                        continue
                    # Enforce single membership on load: first theme wins.
                    if symbol not in members and not any(
                        symbol in existing for existing in themes.values()
                    ):
                        members.append(symbol)
                if members and theme not in themes:
                    themes[theme] = members
        return themes

    def save(self, themes: dict[str, list[str]]) -> dict[str, list[str]]:
        cleaned: dict[str, list[str]] = {}
        for raw_name, raw_members in themes.items():
            theme = format_theme_path(validate_theme_path(raw_name))
            members: list[str] = []
            for raw in raw_members:
                symbol = normalize_ticker(str(raw))
                if not symbol:
                    continue
                if symbol not in members and not any(
                    symbol in existing for existing in cleaned.values()
                ):
                    members.append(symbol)
            if members and theme not in cleaned:
                cleaned[theme] = members
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"order": list(cleaned.keys()), "themes": cleaned}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return cleaned

    @staticmethod
    def _remove_members_from_others(
        themes: dict[str, list[str]], key: str, member_set: set[str]
    ) -> None:
        """Enforce single membership: drop these tickers from every other leaf."""
        for other in list(themes.keys()):
            if other == key:
                continue
            remaining = [t for t in themes[other] if t not in member_set]
            if remaining:
                themes[other] = remaining
            else:
                del themes[other]

    def _delete_subtree(
        self, themes: dict[str, list[str]], key: str
    ) -> dict[str, list[str]]:
        prefix = key + THEME_PATH_SEP
        for other in list(themes.keys()):
            if other == key or other.startswith(prefix):
                del themes[other]
        return self.save(themes)

    def set_theme(
        self, path: str | list[str], members: list[str]
    ) -> dict[str, list[str]]:
        themes = self.load()
        key = format_theme_path(validate_theme_path(path))
        cleaned_members = list(
            dict.fromkeys(normalize_ticker(m) for m in members if str(m).strip())
        )
        if not cleaned_members:
            return self._delete_subtree(themes, key)
        self._remove_members_from_others(themes, key, set(cleaned_members))
        # Re-assigning an existing key keeps its position; new keys append.
        themes[key] = cleaned_members
        return self.save(themes)

    def append_to_theme(
        self, path: str | list[str], members: list[str]
    ) -> dict[str, list[str]]:
        themes = self.load()
        key = format_theme_path(validate_theme_path(path))
        cleaned_members = list(
            dict.fromkeys(normalize_ticker(m) for m in members if str(m).strip())
        )
        if not cleaned_members:
            return self.save(themes)
        self._remove_members_from_others(themes, key, set(cleaned_members))
        existing = themes.get(key, [])
        themes[key] = list(dict.fromkeys([*existing, *cleaned_members]))
        return self.save(themes)

    def delete_theme(self, path: str | list[str]) -> dict[str, list[str]]:
        themes = self.load()
        key = format_theme_path(validate_theme_path(path))
        return self._delete_subtree(themes, key)

    def clear(self) -> dict[str, list[str]]:
        return self.save({})

    def remove_ticker(self, ticker: str) -> dict[str, list[str]]:
        symbol = normalize_ticker(ticker)
        themes = self.load()
        changed = False
        for name in list(themes.keys()):
            if symbol in themes[name]:
                themes[name] = [t for t in themes[name] if t != symbol]
                changed = True
                if not themes[name]:
                    del themes[name]
        if changed:
            return self.save(themes)
        return themes
