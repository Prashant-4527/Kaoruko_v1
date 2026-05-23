"""
tests/unit/test_language_detector.py
"""
import pytest
from kaoruko.nlu.language_detector import LanguageDetector


@pytest.fixture
def detector():
    d = LanguageDetector()
    d.initialize()
    return d


class TestLanguageDetector:
    def test_english(self, detector):
        assert detector.detect("Open Chrome browser") == "en"

    def test_japanese_hiragana(self, detector):
        assert detector.detect("クロームを開いて") == "ja"

    def test_japanese_katakana(self, detector):
        assert detector.detect("ユーチューブを開いて") == "ja"

    def test_hinglish_kholo(self, detector):
        assert detector.detect("Chrome kholo") == "hi-en"

    def test_hinglish_karo(self, detector):
        assert detector.detect("VS Code open karo") == "hi-en"

    def test_hinglish_band_karo(self, detector):
        assert detector.detect("Discord band karo") == "hi-en"

    def test_empty_string(self, detector):
        assert detector.detect("") == "en"

    def test_stt_hint_hinglish(self, detector):
        lang = detector.normalize_for_stt("hi-en")
        assert lang is None   # Auto-detect for Hinglish

    def test_stt_hint_japanese(self, detector):
        lang = detector.normalize_for_stt("ja")
        assert lang == "ja"

    def test_stt_hint_english(self, detector):
        lang = detector.normalize_for_stt("en")
        assert lang == "en"

    def test_multilingual_detection(self, detector):
        assert detector.is_multilingual("Open YouTube ユーチューブ")
