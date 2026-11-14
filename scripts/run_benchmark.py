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
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from effective_context_lab.clients import OpenAICompatClient
from effective_context_lab.runner import BenchmarkConfig, run_benchmark


def parse_args():
    p = argparse.ArgumentParser(description="长上下文有效利用率 benchmark")
    p.add_argument("--model", default="opencode-go/deepseek-v4.1-flash",
                   help="Magpie 模型 id (默认 deepseek-v4.1-flash, 声称 1M)")
    p.add_argument("--base-url", default="http://127.0.0.1:3425/v1")
    p.add_argument("--seq-lens", type=int, nargs="+",
                   default=[4096, 8192, 16384, 32768, 65536, 131072])
    p.add_argument("--positions", type=float, nargs="+", default=[0.0, 0.5, 1.0])
    p.add_argument("--repeats", type=int, default=2)
    p.add_argument("--threshold", type=float, default=0.856)
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--max-tokens", type=int, default=32)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--task", default="single_needle",
                   choices=["single_needle", "multi_needle", "multi_choice",
                            "variable_tracking", "aggregation", "multi_doc_qa"],
                   help="任务类型 (默认 single_needle)")
    p.add_argument("--dry-run", action="store_true",
                   help="不实际请求，只打印将要跑的计划")
    return p.parse_args()


def main():
    args = parse_args()

    client = OpenAICompatClient(
        model=args.model,
        base_url=args.base_url,
        timeout=args.timeout,
        max_tokens=args.max_tokens,
        context_length=1_000_000,  # 声称窗口 (从 Magpie /models 读, 此处固定 1M)
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
    print("声称窗口: 1,000,000 tokens")
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
    os.makedirs("data", exist_ok=True)
    os.makedirs("reports", exist_ok=True)

    json_path = f"data/{slug}-benchmark-{ts}.json"
    with open(json_path, "w") as f:
        f.write(result.to_json())
    print(f"\n原始结果: {json_path}")

    # 报告
    report_path = write_report(result, slug, ts)
    print(f"报告: {report_path}")


def write_report(result, slug, ts):
    """生成可读报告."""
    lines = []
    lines.append(f"# 长上下文有效利用率报告 — {result.model}")
    lines.append("")
    lines.append(f"- **生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **声称窗口**: {result.claimed_context:,} tokens")
    lines.append(f"- **阈值**: {result.config.threshold}")
    lines.append(f"- **探针数**: {len(result.cells)}")
    lines.append("")

    lines.append("## 准确率矩阵")
    lines.append("")
    lines.append("| seq_len | 位置0.0(最前) | 位置0.5(中间) | 位置1.0(最后) |")
    lines.append("|---------|--------------|---------------|---------------|")
    for c in sorted(result.cells, key=lambda x: (x.seq_len, x.position_frac)):
        # 每行聚合
        pass

    # 按 seq_len 聚合
    seq_lens = sorted(set(c.seq_len for c in result.cells))
    pos_fracs = sorted(set(c.position_frac for c in result.cells))
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
    lines.append(
        "- 若有效窗口 << 声称窗口, 印证「窗口大 ≠ 能用窗口」(RULER 结论)."
    )
    lines.append("")
    lines.append("## 复现")
    lines.append("")
    lines.append("```bash")
    lines.append(f"python3 scripts/run_benchmark.py --model {result.model} --repeats {result.config.repeats}")
    lines.append("```")

    os.makedirs("reports", exist_ok=True)
    path = f"reports/{slug}-report-{ts}.md"
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    main()
