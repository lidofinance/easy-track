# Lido Lend Easy Track scenarios

Without `LIDO_LEND_ARTIFACTS_DIR`, the suite uses local lending stubs. With it, the suite reads deployment
artifacts and exercises lending contracts through mainnet Easy Track and its EVMScriptExecutor on Anvil.
Every recorded market is parameterized through the scenarios; cross-market tests use two market IDs.

## CI and local fork run

The `Lido Lend fork tests` workflow runs on pushes to `feat/ll-factories-mainnet-deployment` and supports
manual dispatch with a mainnet block number. It checks out lending at `refactor/solidity-deployment`, installs
its pinned Foundry version and runs the same command available locally:

```sh
LENDING_DIR=/path/to/disposable/lend-markets \
MAINNET_RPC_URL=<archive-rpc> \
FORK_BLOCK=26369828 \
bash scripts/ci/test_lido_lend.sh
```

Use a clean, disposable lending checkout with initialized submodules. Install this repository's Python
dependencies with `poetry install` first. Port 8545 must be free.

The runner starts Anvil with step tracing, reuses the recorded mainnet protocol and Exit Books, and deploys
two inert WETH/wstETH markets through an inherited Solidity recipe and `make deploy-script`. It records
native lending artifacts after receipt validation. Brownie performs activation, preseed and subsequent
operations through Easy Track motions. The runner stops its Anvil on exit and writes JUnit results to
`reports/lido-lend/results.xml`.

After each market's activation and Exit Book allowlist motions, an integration test runs lending's
`make test-fork` with the same artifact run and Anvil RPC. Lending forks that node, preserves the active market and prepares the remaining
inert market. Its output is saved under `reports/lido-lend/`. Skipped activation or lending regression cases fail CI.

The loader accepts historical protocol/market artifacts and version-1 typed market artifacts from Solidity
recipes. It checks deployment identity, chain, core, market parameters and market ID; fork fixtures additionally
check contract code and governance bindings.

## Attach to a prepared Anvil

```sh
ATTACH_EXTERNAL_NODE=true \
LIDO_LEND_ARTIFACTS_DIR=/path/to/lend-markets/deployed/mainnet \
poetry run brownie test tests/integration/lido_lend --network mainnet-fork -q
```

The artifacts must describe the contracts on that node. Keep markets inert to exercise activation:
activation scenarios skip already-active markets. `ATTACH_EXTERNAL_NODE` enables Brownie's Anvil backend
and trace compatibility. The node must run with `--steps-tracing`.

Activation deploys and funds a Preseeder. `LIDO_LEND_PRESEEDER` selects an existing one;
`LIDO_LEND_PRESEED_FUNDER` overrides the impersonated token funder. The CI runner clears the Preseeder override.

## Local stub scenarios

```sh
poetry run brownie test tests/integration/lido_lend --network mainnet-fork -q
```

Leave `LIDO_LEND_ARTIFACTS_DIR` and `ATTACH_EXTERNAL_NODE` unset for this mode.
