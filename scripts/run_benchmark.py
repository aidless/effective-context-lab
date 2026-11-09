#!/usr/bin/env python3
"""运行长上下文有效利用率 benchmark.

用法:
    python3 scripts/run_benchmark.py [--model MODEL] [--seq-lens ...] [--repeats N]

默认使用 Magpie 网关的 opencode-go/deepseek-v4.1-flash (声称 1M 上下文)。

产出:
    data/<model-slug>-benchmark-<timestamp>.json  原始结果
    reports/<model-slug>-report.md                 可读报告
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from effective_context_lab.clients import MockClient, OpenAICompatClient
from effective_context_lab.runner import BenchmarkConfig, run_benchmark

LIVE_MODEL_DEFAULT = "opencode-go/deepseek-v4.1-flash"
FIXTURE_BANNER = (
    "FIXTURE: mock client, not a live measurement. "
    "Scores are not comparable to data/*.json."
)


def build_parser():
    p = argparse.ArgumentParser(
        description="长上下文有效利用率 benchmark",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--model", default=LIVE_MODEL_DEFAULT,
                   help="Live endpoint model id. Mock runs record fixture-model unless --model is set.")
    p.add_argument("--base-url", default="http://127.0.0.1:3425/v1",
                   help="OpenAI-compatible base URL. Unused by --client mock.")
    p.add_argument("--client", choices=["openai", "mock"], default="openai",
                   help="openai calls the live endpoint; mock is an offline fixture.")
    p.add_argument("--oracle", action="store_true",
                   help="With --client mock, return the probe expected answer. Fixture only.")
    p.add_argument("--api-key", default=None,
                   help="Bearer token for the live client. Defaults to EFFECTIVE_CONTEXT_API_KEY if set, else empty. Never logged.")
    p.add_argument("--claimed-context", type=int, default=None,
                   help="Recorded claimed window. Not read from the endpoint. Live default 1000000. Mock default 0.")
    p.add_argument("--output-dir", default=None,
                   help="Where to write JSON and the markdown note. Live default data/. Mock default artifacts/offline.")
    p.add_argument("--seq-lens", type=int, nargs="+",
                   default=[4096, 8192, 16384, 32768, 65536, 131072])
    p.add_argument("--positions", type=float, nargs="+", default=[0.0, 0.5, 1.0])
    p.add_argument("--repeats", type=int, default=2)
    p.add_argument("--threshold", type=float, default=0.856)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument(
        "--max-tokens",
        type=int,
        default=300,
        help="Output budget. 32 collapses reasoning models to empty content.",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--task", default="single_needle",
                   choices=["single_needle", "multi_needle", "multi_choice",
                            "variable_tracking", "aggregation", "multi_doc_qa"],
                   help="任务类型 (默认 single_needle)")
    p.add_argument("--dry-run", action="store_true",
                   help="不实际请求，只打印将要跑的计划")
    return p


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.oracle and args.client != "mock":
        parser.error("--oracle is only valid with --client mock")

    fixture = args.client == "mock"
    if fixture and args.model == LIVE_MODEL_DEFAULT:
        args.model = "fixture-model"
    elif fixture and not str(args.model).startswith("fixture"):
        args.model = "fixture-" + args.model.replace("/", "-")

    if args.claimed_context is None:
        args.claimed_context = 0 if fixture else 1_000_000
    if args.output_dir is None:
        args.output_dir = "artifacts/offline" if fixture else "data"
    if args.api_key is None:
        args.api_key = os.environ.get("EFFECTIVE_CONTEXT_API_KEY", "")

    if fixture:
        print(FIXTURE_BANNER)
        client = MockClient(
            model=args.model,
            base_url=args.base_url,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
            context_length=args.claimed_context,
            oracle=args.oracle,
        )
    else:
        client = OpenAICompatClient(
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            timeout=args.timeout,
            max_tokens=args.max_tokens,
            context_length=args.claimed_context,
        )

    cfg = BenchmarkConfig(
        seq_lens=args.seq_lens,
        position_fracs=args.positions,
        densities=[1.0],
        task=args.task,
        repeats=args.repeats,
        threshold=args.threshold,
        max_tokens=args.max_tokens,
        seed=args.seed,
    )

    total_cases = (
        len(args.seq_lens) * len(args.positions) * args.repeats
    )
    print(f"模型: {args.model}")
    print(f"client: {args.client}")
    print(
        f"claimed_context flag: {args.claimed_context} "
        "(not queried from the endpoint)"
    )
    print(f"任务: {args.task}")
    print(f"扫描: {len(args.seq_lens)} 长度 × {len(args.positions)} 位置 × {args.repeats} 重复")
    print(f"总探针数: {total_cases}")
    print(f"阈值: {args.threshold}")
    print()

    if args.dry_run:
        print("DRY RUN - 不实际请求. 计划:")
        for sl in args.seq_lens:
            for pos in args.positions:
                print(f"  seq={sl} pos={pos} x{args.repeats}")
        return

    # 估计成本 (每探针约 seq_len tokens 输入)
    total_input_tokens = sum(args.seq_lens) * len(args.positions) * args.repeats
    print(f"预计输入 token 总量: ~{total_input_tokens:,}")
    print()

    result = run_benchmark(client, cfg, progress=True)

    # 落盘
    ts = time.strftime("%Y%m%d-%H%M%S")
    slug = args.model.replace("/", "-").replace(":", "-")
    os.makedirs(args.output_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, f"{slug}-benchmark-{ts}.json")
    payload = json.loads(result.to_json())
    if fixture:
        payload["fixture"] = True
        payload["provenance"] = "mock_client_not_a_measurement"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\n原始结果: {json_path}")

    report_path = write_report(result, slug, ts, args.output_dir, fixture=fixture)
    print(f"报告: {report_path}")


def write_report(result, slug, ts, output_dir, fixture=False):
    """生成可读报告."""
    lines = []
    if fixture:
        lines.append(FIXTURE_BANNER)
        lines.append("")
    lines.append(f"# 长上下文有效利用率报告 — {result.model}")
    lines.append("")
    lines.append(f"- **生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **声称窗口**: {result.claimed_context:,} tokens")
    lines.append(f"- **阈值**: {result.config.threshold}")
    lines.append(f"- **探针数**: {len(result.cells)}")
    lines.append("")

    seq_lens = sorted(set(c.seq_len for c in result.cells))
    pos_fracs = sorted(set(c.position_frac for c in result.cells))
    lines.append("## 准确率矩阵")
    lines.append("")
    header = " | ".join(f"位置{pf}" for pf in pos_fracs)
    lines.append(f"| seq_len | {header} |")
    lines.append("|" + " --- |" * (len(pos_fracs) + 1))
    for sl in seq_lens:
        row = []
        for pf in pos_fracs:
            c = result.cell(sl, pf, 1.0)
            if c:
                row.append(f"{c.accuracy:.2f}")
            else:
                row.append("-")
        lines.append(f"| {sl:,} | " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## 有效窗口 (按位置)")
    lines.append("")
    lines.append("| 位置 | 有效窗口 | 声称 | 效率比 | 鸿沟 |")
    lines.append("|------|---------|------|--------|------|")
    for pf in pos_fracs:
        gap = result.claimed_vs_effective(position_frac=pf, density=1.0)
        lines.append(
            f"| {pf} | {gap['effective']:,} | {gap['claimed']:,} | "
            f"{gap['ratio']:.1%} | {gap['gap']:,} |"
        )

    lines.append("")
    lines.append("## 结论")
    lines.append("")
    best_ratio = max(
        (result.claimed_vs_effective(position_frac=pf)["ratio"] for pf in pos_fracs),
        default=0.0,
    )
    lines.append(
        f"- **最佳位置的有效窗口/声称窗口 = {best_ratio:.1%}**"
    )
    if fixture:
        lines.append("- This file is a mock fixture. It is not evidence about a live model.")
    else:
        lines.append(
            "- claimed_context is the CLI flag, not a value read from the endpoint."
        )
    lines.append("")
    lines.append("## 复现")
    lines.append("")
    lines.append("```bash")
    if fixture:
        lines.append(
            "python3 scripts/run_benchmark.py --client mock --oracle "
            f"--repeats {result.config.repeats}"
        )
    else:
        lines.append(
            "python3 scripts/run_benchmark.py --client openai "
            f"--model {result.model} --repeats {result.config.repeats} --max-tokens 300"
        )
    lines.append("```")

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{slug}-report-{ts}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    main()
