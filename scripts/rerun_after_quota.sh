#!/bin/bash
# 配额恢复后补跑脚本
# 补跑 3 个缺失的 variable_tracking 1M cells + 聚合/多文档问答测量
# 用法: bash scripts/rerun_after_quota.sh

set -e
cd "$(dirname "$0")/.."

echo "=== 1. 补跑 variable_tracking 1M 3 cells ==="
timeout 600 python3 scripts/run_benchmark.py \
  --model nvidia/deepseek-ai/deepseek-v4.1-flash \
  --base-url http://127.0.0.1:3425/v1 \
  --seq-lens 1000000 \
  --positions 0.5 0.75 1.0 \
  --task variable_tracking \
  --repeats 1 \
  --max-tokens 300

echo ""
echo "=== 2. 测量 aggregation (聚合) ==="
# 65K/262K/524K/1M × 5 位置
timeout 1800 python3 scripts/run_benchmark.py \
  --model nvidia/deepseek-ai/deepseek-v4.1-flash \
  --base-url http://127.0.0.1:3425/v1 \
  --seq-lens 65536 262144 524288 1000000 \
  --positions 0.0 0.25 0.5 0.75 1.0 \
  --task aggregation \
  --repeats 1 \
  --max-tokens 300

echo ""
echo "=== 3. 测量 multi_doc_qa (多文档问答) ==="
timeout 1800 python3 scripts/run_benchmark.py \
  --model nvidia/deepseek-ai/deepseek-v4.1-flash \
  --base-url http://127.0.0.1:3425/v1 \
  --seq-lens 65536 262144 524288 1000000 \
  --positions 0.0 0.25 0.5 0.75 1.0 \
  --task multi_doc_qa \
  --repeats 1 \
  --max-tokens 300

echo ""
echo "=== 全部补跑完成 ==="
