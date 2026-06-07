"""Tests for phcc_matrix helpers (no PyPI)."""

from pathlib import Path
import sys

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from phcc_matrix import (  # noqa: E402
    PYCARES_CONSTRAINT_LEGACY,
    PYCARES_CONSTRAINT_MODERN,
    pycares_constraint_for_ha_month,
    write_uv_pycares_override,
)


def test_pycares_constraint_for_ha_month():
    """Legacy pycares 4.x through HA 2026.1; modern 5.x from 2026.2 onward."""
    assert pycares_constraint_for_ha_month("2025.10") == PYCARES_CONSTRAINT_LEGACY
    assert pycares_constraint_for_ha_month("2026.1") == PYCARES_CONSTRAINT_LEGACY
    assert pycares_constraint_for_ha_month("2026.3") == PYCARES_CONSTRAINT_MODERN
    assert pycares_constraint_for_ha_month("2024.12") is None


def test_write_uv_pycares_override_replaces_existing(tmp_path, monkeypatch):
    """write_uv_pycares_override updates override-dependencies via regex."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\nname = 'x'\n\n[tool.uv]\n"
        'override-dependencies = ["pycares>=4.0.0,<5"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "phcc_matrix.PYPROJECT_PATH",
        pyproject,
    )
    monkeypatch.setattr(
        "phcc_matrix.dev_pycares_constraint",
        lambda refresh=False: PYCARES_CONSTRAINT_MODERN,
    )
    assert write_uv_pycares_override() == PYCARES_CONSTRAINT_MODERN
    text = pyproject.read_text(encoding="utf-8")
    assert f'override-dependencies = ["{PYCARES_CONSTRAINT_MODERN}"]' in text
    assert "pycares>=4" not in text


def test_write_uv_pycares_override_inserts_after_uv_section(tmp_path, monkeypatch):
    """write_uv_pycares_override inserts override-dependencies under [tool.uv]."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.uv]\n\n[tool.uv.sources]\n", encoding="utf-8")
    monkeypatch.setattr("phcc_matrix.PYPROJECT_PATH", pyproject)
    monkeypatch.setattr(
        "phcc_matrix.dev_pycares_constraint",
        lambda refresh=False: PYCARES_CONSTRAINT_LEGACY,
    )
    write_uv_pycares_override()
    text = pyproject.read_text(encoding="utf-8")
    assert f'override-dependencies = ["{PYCARES_CONSTRAINT_LEGACY}"]' in text
    assert text.index("override-dependencies") < text.index("[tool.uv.sources]")
