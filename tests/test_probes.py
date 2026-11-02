"""探针生成器测试 (RED→GREEN 纪律)."""

import pytest

from effective_context_lab.probes import (
    NIAHConfig,
    generate_needle_in_haystack,
    generate_question,
    expected_answer,
    needle_position,
)


class TestNeedlePosition:
    def test_position_frac_0_is_beginning(self):
        assert needle_position(4096, 0.0) == 1

    def test_position_frac_05_is_middle(self):
        pos = needle_position(4096, 0.5)
        assert 1800 <= pos <= 2200

    def test_position_frac_1_is_end(self):
        assert needle_position(4096, 1.0) == 4094

    def test_invalid_frac_raises(self):
        with pytest.raises(ValueError):
            needle_position(4096, 1.5)


class TestGenerateNeedleInHaystack:
    def test_generates_context(self):
        cfg = NIAHConfig(seq_len=4096, position_frac=0.5, seed=1)
        context, needles, actual_len = generate_needle_in_haystack(cfg)
        assert len(context) > 0
        assert len(needles) == 1
        assert actual_len >= 1000  # 至少千级 token

    def test_needle_contains_subject_and_value(self):
        cfg = NIAHConfig(seq_len=1024, needle_subject="the capital of France", needle_value="Paris", seed=2)
        context, needles, _ = generate_needle_in_haystack(cfg)
        assert "Paris" in context
        assert "France" in context

    def test_multi_needle_creates_multiple(self):
        cfg = NIAHConfig(seq_len=2048, num_needles=3, task="multi_needle", seed=3)
        context, needles, _ = generate_needle_in_haystack(cfg)
        assert len(needles) == 3
        for n in needles:
            assert n.subject in context or n.value in context

    def test_reproducible_with_seed(self):
        cfg1 = NIAHConfig(seq_len=2048, seed=42)
        cfg2 = NIAHConfig(seq_len=2048, seed=42)
        ctx1, _, _ = generate_needle_in_haystack(cfg1)
        ctx2, _, _ = generate_needle_in_haystack(cfg2)
        assert ctx1 == ctx2

    def test_different_seed_differs(self):
        cfg1 = NIAHConfig(seq_len=2048, seed=1)
        cfg2 = NIAHConfig(seq_len=2048, seed=999)
        ctx1, _, _ = generate_needle_in_haystack(cfg1)
        ctx2, _, _ = generate_needle_in_haystack(cfg2)
        assert ctx1 != ctx2

    def test_multi_choice_task_generates_options(self):
        cfg = NIAHConfig(seq_len=1024, task="multi_choice", seed=4)
        context, needles, _ = generate_needle_in_haystack(cfg)
        assert "Choices:" in context
        assert len(needles) == 1

    def test_variable_tracking_task_generates_timestamps(self):
        cfg = NIAHConfig(seq_len=1024, task="variable_tracking", num_variables=4, num_assignments=3, seed=42)
        context, needles, _ = generate_needle_in_haystack(cfg)
        # 时间戳应存在
        assert "(t=" in context
        # 针应指向最后一个变量
        assert needles[0].subject == "variable 4"
        # 值应为数字字符串
        assert needles[0].value.isdigit()

    def test_variable_tracking_expected_answer_is_t_final(self):
        cfg = NIAHConfig(seq_len=1024, task="variable_tracking", num_variables=4, num_assignments=3, seed=42)
        context, needles, _ = generate_needle_in_haystack(cfg)
        exp = expected_answer(cfg, needles)
        assert exp == needles[0].value  # 期望 = 目标变量最终值

    def test_variable_tracking_question_mentions_t(self):
        cfg = NIAHConfig(seq_len=1024, task="variable_tracking", num_variables=4, num_assignments=3, seed=42)
        _, needles, _ = generate_needle_in_haystack(cfg)
        q = generate_question(cfg, needles)
        assert "final value of variable 4" in q
        assert "t=3" in q  # 问题应指明最终时间戳

    def test_aggregation_task_generates_facts(self):
        cfg = NIAHConfig(seq_len=2048, task="aggregation", num_variables=4, seed=7)
        context, needles, _ = generate_needle_in_haystack(cfg)
        assert "The value of item 1 is" in context
        assert len(needles) == 1
        assert needles[0].value.isdigit()  # 聚合结果应为数字

    def test_aggregation_expected_answer_is_sum(self):
        cfg = NIAHConfig(seq_len=2048, task="aggregation", num_variables=4, aggregation_op="sum", seed=7)
        context, needles, _ = generate_needle_in_haystack(cfg)
        exp = expected_answer(cfg, needles)
        assert exp == needles[0].value

    def test_aggregation_question_mentions_sum(self):
        cfg = NIAHConfig(seq_len=2048, task="aggregation", aggregation_op="sum", seed=7)
        _, needles, _ = generate_needle_in_haystack(cfg)
        q = generate_question(cfg, needles)
        assert "sum" in q.lower()

    def test_multi_doc_qa_generates_docs(self):
        cfg = NIAHConfig(seq_len=2048, task="multi_doc_qa", num_docs=4, num_facts_per_doc=2, seed=9)
        context, needles, _ = generate_needle_in_haystack(cfg)
        assert "Document 1:" in context
        assert len(needles) == 1
        assert "value_" in needles[0].value  # 应为 value_d_f 格式

    def test_multi_doc_qa_expected_answer(self):
        cfg = NIAHConfig(seq_len=2048, task="multi_doc_qa", num_docs=4, num_facts_per_doc=2, seed=9)
        _, needles, _ = generate_needle_in_haystack(cfg)
        exp = expected_answer(cfg, needles)
        assert exp == needles[0].value
        assert "value_4_1" in exp  # 目标文档是最后一个 (doc 4)


class TestQuestion:
    def test_single_needle_question(self):
        cfg = NIAHConfig(seq_len=512, needle_subject="the capital of France", needle_value="Paris")
        _, needles, _ = generate_needle_in_haystack(cfg)
        q = generate_question(cfg, needles)
        assert "capital of France" in q

    def test_expected_answer(self):
        cfg = NIAHConfig(seq_len=512, needle_subject="X", needle_value="Y")
        _, needles, _ = generate_needle_in_haystack(cfg)
        assert expected_answer(cfg, needles) == "Y"
