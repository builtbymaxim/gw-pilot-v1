"""Tests verifying all pipeline bug fixes (#1–#23)."""
import sys, os, yaml
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import numpy as np

# Load real config
with open(os.path.join(os.path.dirname(__file__), "..", "config.yml")) as f:
    CFG = yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Fix #1 & #2: VUI word boundaries and no overlapping double-count
# ---------------------------------------------------------------------------
class TestVUI:
    def _make_sents(self, texts):
        return [{"text": t} for t in texts]

    def test_may_does_not_match_mayor(self):
        from src.vui import compute_vui
        result = compute_vui(self._make_sents(["The mayor announced new policy."]), CFG)
        assert result["vui_hits"] == 0, "'may' should not match inside 'mayor'"

    def test_may_does_not_match_maybe(self):
        from src.vui import compute_vui
        result = compute_vui(self._make_sents(["Maybe we will improve."]), CFG)
        assert result["vui_hits"] == 0, "'may' should not match inside 'maybe'"

    def test_aim_does_not_match_claim(self):
        from src.vui import compute_vui
        result = compute_vui(self._make_sents(["We claim this is accurate."]), CFG)
        assert result["vui_hits"] == 0, "'aim' should not match inside 'claim'"

    def test_plan_does_not_match_airplane(self):
        from src.vui import compute_vui
        result = compute_vui(self._make_sents(["The airplane landed safely."]), CFG)
        assert result["vui_hits"] == 0, "'plan' should not match inside 'airplane'"

    def test_material_does_not_match_immaterial(self):
        from src.vui import compute_vui
        # "immaterial" should not be matched by \bmaterial\b
        result = compute_vui(self._make_sents(["This is immaterial to the discussion."]), CFG)
        assert result["vui_hits"] == 0, "'material' should not match inside 'immaterial'"

    def test_expected_counted_once(self):
        from src.vui import compute_vui
        result = compute_vui(self._make_sents(["We expected strong results."]), CFG)
        assert result["vui_hits"] == 1, "'expected' should be counted exactly once"

    def test_planning_counted_once(self):
        from src.vui import compute_vui
        result = compute_vui(self._make_sents(["We are planning ahead."]), CFG)
        assert result["vui_hits"] == 1, "'planning' should be counted exactly once"

    def test_genuine_hedge_detected(self):
        from src.vui import compute_vui
        result = compute_vui(self._make_sents(["This may potentially lead to uncertainty."]), CFG)
        assert result["vui_hits"] == 3  # may, potentially, uncertainty

    def test_target_removed_from_hedges(self):
        """Fix #14: 'target' should NOT be in VUI hedges."""
        from src.vui import compute_vui
        result = compute_vui(self._make_sents(["We set a target of 50%."]), CFG)
        assert result["vui_hits"] == 0, "'target' should not be a VUI hedge"


# ---------------------------------------------------------------------------
# Fix #3 & #9: CI formula — signed change + division by zero
# ---------------------------------------------------------------------------
class TestCI:
    def test_emission_reduction_gets_high_ci(self):
        """Fix #3: Emissions going down (200K→100K) = good = CI near 1.0."""
        from src.ci import ci_light
        result = ci_light({2022: 200000, 2023: 100000})
        ci_val = result["ci_by_year"][2023]
        assert ci_val == 1.0, f"Emission reduction should give CI=1.0, got {ci_val}"

    def test_emission_increase_gets_low_ci(self):
        """Fix #3: Emissions going up (100K→200K) = bad = CI < 1.0."""
        from src.ci import ci_light
        result = ci_light({2022: 100000, 2023: 200000})
        ci_val = result["ci_by_year"][2023]
        assert ci_val == pytest.approx(0.5, abs=0.02), f"Emission doubling should give CI≈0.5, got {ci_val}"

    def test_no_change_gives_ci_one(self):
        from src.ci import ci_light
        result = ci_light({2022: 150000, 2023: 150000})
        assert result["ci_by_year"][2023] == 1.0

    def test_both_zero_no_division_error(self):
        """Fix #9: Both values zero should not crash."""
        from src.ci import ci_light
        result = ci_light({2022: 0, 2023: 0})
        assert result["ci_by_year"][2023] == 1.0


# ---------------------------------------------------------------------------
# Fix #6: SPI strict_excludes should not discard forward-looking targets
# ---------------------------------------------------------------------------
class TestSPI:
    def test_forward_target_not_excluded(self):
        """'In 2023, we aim to reduce emissions by 50% by 2030' should be specific."""
        from src.spi import is_specific
        text = "In 2023, we aim to reduce emissions by 50% by 2030."
        assert is_specific(text, CFG) is True, "Forward-looking target should not be excluded"

    def test_purely_backward_excluded(self):
        """'In 2023, emissions were 500 tCO2e' — backward-looking, no forward target."""
        from src.spi import is_specific
        text = "In 2023, emissions were 500 tCO2e."
        # has num + unit, but strict_exclude fires and no target/baseline
        # Actually this has num=True, unit=True (tCO2e), and strict_exclude for "in 2023"
        # but no target_pattern or baseline_pattern → should be excluded
        assert is_specific(text, CFG) is False

    def test_baseline_overrides_exclude(self):
        """Sentence with baseline year reference should not be excluded."""
        from src.spi import is_specific
        text = "In 2023 we reduced 30% vs. base year 2019."
        assert is_specific(text, CFG) is True

    def test_specific_with_target_year(self):
        from src.spi import is_specific
        text = "We will reduce emissions by 50% by 2030."
        assert is_specific(text, CFG) is True

    def test_vague_sentence_not_specific(self):
        from src.spi import is_specific
        text = "We are committed to sustainability and environmental stewardship."
        assert is_specific(text, CFG) is False


# ---------------------------------------------------------------------------
# Fix #4: Sectioning — heading aliases should not match body text
# ---------------------------------------------------------------------------
class TestSectioning:
    def test_strategy_in_body_not_matched(self):
        """A page that mentions 'Strategy' only in body text should not be classified."""
        from src.sectioning import section_by_headings
        pages = [{"page": 1, "text": (
            "Financial Overview\n\n"
            "Our investment strategy focuses on long-term growth. "
            "The strategy has been to diversify across asset classes. "
            "We believe this strategy will yield positive results."
        )}]
        buckets = section_by_headings(pages, CFG)
        assert 1 not in [p["page"] for p in buckets.get("strategy", [])], \
            "'Strategy' in body text should not assign page to strategy section"

    def test_heading_at_top_is_matched(self):
        """A page with 'Strategy' as a heading at the top should be classified."""
        from src.sectioning import section_by_headings
        pages = [{"page": 1, "text": "Sustainability Strategy\n\nOur approach to ESG..."}]
        buckets = section_by_headings(pages, CFG)
        assert 1 in [p["page"] for p in buckets.get("strategy", [])]


# ---------------------------------------------------------------------------
# Fix #5: normalize_year_tokens handles OCR artifacts
# ---------------------------------------------------------------------------
class TestNormalizeYearTokens:
    def test_standard_split(self):
        from src.text_utils import normalize_year_tokens
        assert "2030" in normalize_year_tokens("by 20 30")

    def test_non_breaking_space(self):
        from src.text_utils import normalize_year_tokens
        assert "2030" in normalize_year_tokens("by 20\u00a030")

    def test_en_dash(self):
        from src.text_utils import normalize_year_tokens
        assert "2030" in normalize_year_tokens("by 20\u201330")

    def test_soft_hyphen(self):
        from src.text_utils import normalize_year_tokens
        assert "2030" in normalize_year_tokens("by 20\u00ad30")

    def test_zero_width_space(self):
        from src.text_utils import normalize_year_tokens
        assert "2030" in normalize_year_tokens("by 20\u200b30")

    def test_already_correct(self):
        from src.text_utils import normalize_year_tokens
        assert "by 2030" == normalize_year_tokens("by 2030")


# ---------------------------------------------------------------------------
# Fix #12: summarize_buckets page counts
# ---------------------------------------------------------------------------
class TestSummarizeBuckets:
    def test_deduped_counts(self):
        from src.pilot import summarize_buckets
        buckets = {
            "strategy": [
                {"page": 1, "text": "..."},
                {"page": 1, "text": "...", "fallback": True},  # same page, fallback
                {"page": 2, "text": "...", "fallback": True},
            ]
        }
        result = summarize_buckets(buckets)
        assert result["strategy"]["count_pages"] == 2
        assert result["strategy"]["fallback_pages"] == 2  # pages 1 and 2 have fallback entries
        assert result["strategy"]["heading_pages"] == 1   # page 1 has a heading entry


# ---------------------------------------------------------------------------
# Fix #11: Keyword fallback word boundaries
# ---------------------------------------------------------------------------
class TestKeywordFallback:
    def test_target_not_in_targeting(self):
        """'targeting' should not match \\btarget\\b."""
        from src.sectioning import keyword_fallback
        pages = [{"page": 1, "text": "We are targeting improvements in our operations across all divisions."}]
        result = keyword_fallback(pages, CFG)
        # Should not be assigned to metrics_targets via the word "targeting"
        mt_pages = [p["page"] for p in result.get("metrics_targets", [])]
        assert 1 not in mt_pages, "'targeting' should not match \\btarget\\b"
