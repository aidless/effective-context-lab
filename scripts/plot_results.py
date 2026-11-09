"""可视化 benchmark 结果: 准确率热力图 + 延迟曲线."""
import json
import glob
import os
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# 中文字体设置 (Noto Sans CJK SC)
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False


def load_latest(pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    with open(files[-1]) as f:
        return json.load(f)


def get_results(data):
    """兼容两种数据结构: 'results' 或 'cells'."""
    if "results" in data:
        return data["results"]
    if "cells" in data:
        # cells 用 accuracy 而非 score
        cells = []
        for c in data["cells"]:
            nc = dict(c)
            nc["score"] = c.get("accuracy", c.get("score", 0))
            nc["latency_ms"] = c.get("avg_latency_ms", c.get("latency_ms", 0))
            cells.append(nc)
        return cells
    return []


def plot_heatmap(data, title, outfile, seqs, pfs):
    """绘制准确率热力图 (seq_len × position_frac)."""
    results = get_results(data)
    matrix = np.zeros((len(seqs), len(pfs)))
    for i, seq in enumerate(seqs):
        for j, pf in enumerate(pfs):
            cells = [r for r in results if r["seq_len"] == seq and abs(r["position_frac"] - pf) < 1e-9]
            if cells:
                matrix[i, j] = statistics.mean(r["score"] for r in cells)
            else:
                matrix[i, j] = np.nan

    fig, ax = plt.subplots(figsize=(12, 6))
    im = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(pfs)))
    ax.set_xticklabels([f"{pf}" for pf in pfs])
    ax.set_yticks(range(len(seqs)))
    ax.set_yticklabels([f"{seq:,}" for seq in seqs])
    ax.set_xlabel("针位置 (0.0=最前, 1.0=最末)")
    ax.set_ylabel("上下文长度 (tokens)")
    ax.set_title(title)

    # 数值标注
    for i in range(len(seqs)):
        for j in range(len(pfs)):
            if not np.isnan(matrix[i, j]):
                ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=9)

    plt.colorbar(im, ax=ax, label="准确率")
    plt.tight_layout()
    plt.savefig(outfile, dpi=150)
    plt.close()
    print(f"已存 {outfile}")


def plot_latency(data, title, outfile):
    """绘制延迟 vs 上下文长度 (log-log)."""
    results = get_results(data)
    seq_lat = {}
    for r in results:
        seq = r["seq_len"]
        lat = r.get("latency_ms", 0)
        if seq not in seq_lat:
            seq_lat[seq] = []
        if lat > 0:
            seq_lat[seq].append(lat)

    seqs = sorted(seq_lat.keys())
    lats = [statistics.mean(seq_lat[s]) for s in seqs]
    errs = [statistics.stdev(seq_lat[s]) if len(seq_lat[s]) > 1 else 0 for s in seqs]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.errorbar(seqs, lats, yerr=errs, fmt="o-", capsize=5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("上下文长度 (tokens, log)")
    ax.set_ylabel("平均延迟 (ms, log)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(outfile, dpi=150)
    plt.close()
    print(f"已存 {outfile}")


def main():
    outdir = "reports/figures"
    os.makedirs(outdir, exist_ok=True)

    # 1M 完整矩阵热力图
    d = load_latest("data/1m-full-matrix-*.json")
    if d:
        plot_heatmap(d, "1M 完整矩阵准确率 (单针 NIAH)", f"{outdir}/heatmap-1m.png",
                     [4096, 65536, 262144, 524288, 1000000],
                     [0.0, 0.25, 0.5, 0.75, 1.0])

    # 多针检索热力图
    d = load_latest("data/multi-needle-2-*.json")
    if d:
        plot_heatmap(d, "多针检索准确率 (2 针)", f"{outdir}/heatmap-multineedle.png",
                     [65536, 262144, 524288, 1000000],
                     [0.0, 0.25, 0.5, 0.75, 1.0])

    # 多项选择热力图
    d = load_latest("data/multi-choice-*.json")
    if d:
        plot_heatmap(d, "多项选择准确率", f"{outdir}/heatmap-multichoice.png",
                     [4096, 65536, 262144, 524288, 1000000],
                     [0.0, 0.25, 0.5, 0.75, 1.0])

    # 变量追踪热力图
    # Exclude variable-tracking-1m-*.json. sorted()[-1] on the wider glob
    # is an accident of filenames, not a union of the two files.
    d = load_latest("data/variable-tracking-20*.json")
    if d:
        plot_heatmap(d, "变量追踪准确率 (带时间戳)", f"{outdir}/heatmap-variable-tracking.png",
                     [4096, 65536, 262144, 524288, 1000000],
                     [0.0, 0.25, 0.5, 0.75, 1.0])

    # 延迟曲线 (单针)
    d = load_latest("data/1m-full-matrix-*.json")
    if d:
        plot_latency(d, "延迟 vs 上下文长度 (单针)", f"{outdir}/latency.png")


if __name__ == "__main__":
    main()
