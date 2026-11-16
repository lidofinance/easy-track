#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
: "${LENDING_DIR:?Set LENDING_DIR to a disposable lending checkout}"
: "${MAINNET_RPC_URL:?Set MAINNET_RPC_URL to an archive RPC}"
LENDING_DIR="$(cd "$LENDING_DIR" && pwd)"
FORK_BLOCK="${FORK_BLOCK:-26369828}"
LOCAL_RPC=http://127.0.0.1:8545
DEPLOYER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
REPORT_DIR="${REPORT_DIR:-$ROOT/reports/lido-lend}"
mkdir -p "$REPORT_DIR"
export LENDING_DIR REPORT_DIR

if cast block-number --rpc-url "$LOCAL_RPC" >/dev/null 2>&1; then
    echo 'Port 8545 is already in use; stop that node before running this suite.' >&2
    exit 1
fi
anvil_log="$(mktemp)"
anvil --fork-url "$MAINNET_RPC_URL" --fork-block-number "$FORK_BLOCK" \
    --chain-id 1 --port 8545 --steps-tracing --silent >"$anvil_log" 2>&1 &
anvil_pid=$!
cleanup() {
    kill "$anvil_pid" 2>/dev/null || true
    wait "$anvil_pid" 2>/dev/null || true
    rm -f "$anvil_log"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
ready=false
for attempt in {1..60}; do
    kill -0 "$anvil_pid" 2>/dev/null || { echo 'Anvil failed to start' >&2; exit 1; }
    if cast block-number --rpc-url "$LOCAL_RPC" >/dev/null 2>&1; then
        ready=true
        break
    fi
    sleep 1
done
"$ready" || { echo 'Anvil startup timed out' >&2; exit 1; }

mkdir -p "$LENDING_DIR/script/ci"
cp "$ROOT/scripts/ci/DeployLendingMarkets.s.sol" "$LENDING_DIR/script/ci/"
for recipe in DeployFirstMarket DeploySecondMarket; do
    make -C "$LENDING_DIR" deploy-script \
        SCRIPT="script/ci/DeployLendingMarkets.s.sol:$recipe" \
        RUN=mainnet BROADCAST=true VERIFY=false \
        RPC_URL="$LOCAL_RPC" DEPLOYER_SENDER="$DEPLOYER" DEPLOYER_ACCOUNT=
done

cd "$ROOT"
poetry run brownie networks import network-config.yaml true
unset LIDO_LEND_PRESEEDER
export ATTACH_EXTERNAL_NODE=true
export LIDO_LEND_ARTIFACTS_DIR="$LENDING_DIR/deployed/mainnet"
poetry run brownie test tests/integration/lido_lend tests/evm_script_factories \
    tests/scripts/test_lido_lend_artifacts.py \
    -k lido_lend --network mainnet-fork -q --tb=short \
    --junitxml="$REPORT_DIR/results.xml"

poetry run python - "$REPORT_DIR/results.xml" <<'PYTHON'
import sys
import xml.etree.ElementTree as ET

cases = ET.parse(sys.argv[1]).getroot().findall(".//testcase")
activation = [case for case in cases if case.get("name", "").startswith("test_activate_market_scenario[")]
if len(activation) < 4 or any(case.find("skipped") is not None for case in activation):
    raise SystemExit("Expected successful activation motions for both inert markets and both settlement modes")
regressions = [case for case in cases if case.get("name", "").startswith("test_lending_integrations_after_easy_track_activation[")]
if len(regressions) < 2 or any(case.find("skipped") is not None for case in regressions):
    raise SystemExit("Expected lending integration runs against both Easy Track activation cases")
PYTHON
