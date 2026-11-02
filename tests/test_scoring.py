"""评分器测试."""

from effective_context_lab.scoring import (
    exact_match,
    f1_score,
    multi_choice_accuracy,
    is_correct,
)


class TestExactMatch:
    def test_exact_match_same(self):
        assert exact_match("Paris", "Paris") == 1.0

    def test_exact_match_case_insensitive(self):
        assert exact_match("paris", "Paris") == 1.0

    def test_exact_match_different(self):
        assert exact_match("Berlin", "Paris") == 0.0

    def test_exact_match_whitespace(self):
        assert exact_match("  Paris  ", "Paris") == 1.0


class TestF1:
    def test_f1_perfect(self):
        assert f1_score("Paris", "Paris") == 1.0

    def test_f1_partial(self):
        # 预测含"the capital of France"的部分
        score = f1_score("capital France", "capital of France")
        assert 0.0 < score < 1.0

    def test_f1_zero(self):
        assert f1_score("Berlin", "Paris") == 0.0


class TestMultiChoice:
    def test_choice_correct(self):
        assert multi_choice_accuracy("Paris", "Paris", ["Paris", "Berlin", "Rome"]) == 1.0

    def test_choice_wrong(self):
        assert multi_choice_accuracy("Berlin", "Paris", ["Paris", "Berlin", "Rome"]) == 0.0

    def test_choice_substring(self):
        assert multi_choice_accuracy("The answer is Paris", "Paris", ["Paris", "Berlin"]) == 1.0


class TestIsCorrect:
    def test_dispatch_exact(self):
        assert is_correct("Paris", "Paris", "exact_match") == 1.0

    def test_dispatch_f1(self):
        assert is_correct("Paris", "Paris", "f1") == 1.0

    def test_unknown_method_raises(self):
        try:
            is_correct("a", "b", "unknown")
            assert False
        except ValueError:
            assert True
