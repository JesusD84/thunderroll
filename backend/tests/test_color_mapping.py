"""Tests for foreign-language color normalization used by the Excel import."""

import pytest

from app.services.color_mapping import normalize_color


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("black", "NEGRO"),
        ("Black", "NEGRO"),
        ("BLACK", "NEGRO"),
        ("  Red  ", "ROJO"),
        ("grey", "GRIS"),
        ("gray", "GRIS"),
        ("Pink", "ROSA"),
        ("黑色", "NEGRO"),
        ("蓝色", "AZUL"),
    ],
)
def test_foreign_color_names_are_translated(raw, expected):
    assert normalize_color(raw) == expected


@pytest.mark.parametrize("raw", ["rojo", "ROJO", "Azul", "Morado"])
def test_spanish_and_unknown_colors_are_kept_as_written(raw):
    assert normalize_color(raw) == raw.strip()


def test_none_is_preserved():
    assert normalize_color(None) is None
