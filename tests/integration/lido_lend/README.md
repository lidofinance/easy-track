# Lido Lend EasyTrack scenarios

The suite has two modes:

- without `LIDO_LEND_ARTIFACTS_DIR`, it deploys strict local stubs and checks the complete EasyTrack motion flow;
- with `LIDO_LEND_ARTIFACTS_DIR`, it attaches to an existing Anvil mainnet fork, reads the Lido Lend deployment
  protocol and `markets/*.toml` artifacts, and exercises the deployed contracts
  through the real mainnet EasyTrack and EVMScriptExecutor.

The fork loader is fail-closed: it checks the connected chain ID, `[artifact]`/`[protocol]` metadata,
market parameters, bytecode for every market component, both exit books, each
controller/CircuitBreaker role binding, and the executor read from the actual EasyTrack. Every market in the
deployment is parameterized through the scenarios, and the cross-market scenario executes one motion over two
market IDs. GuardianSignals and CircuitBreaker instances may be shared by multiple markets. Missing acceptance
artifacts are usage errors in artifact mode, not skips.

The activation scenario deploys and funds a Preseeder automatically. On a mainnet fork it impersonates a
token funder; override it with `LIDO_LEND_PRESEED_FUNDER` when the default account does not hold a market's loan
token. `LIDO_LEND_PRESEEDER` may still point to an already funded Preseeder bound to the artifact core and the
real EasyTrack executor.

## Local stub scenarios

From the EasyTrack repository:

```bash
poetry run brownie test tests/integration/lido_lend --network mainnet-fork -s
```

Do not set `LIDO_LEND_ARTIFACTS_DIR` for this run.

## Anvil fork scenarios

Start Anvil in terminal 1:

```bash
anvil \
  --fork-url "$MAINNET_RPC_URL" \
  --chain-id 1 \
  --port 8545
```

Deploy Lido Lend to that node from its repository in terminal 2. Use a fresh `RUN` directory:

```bash
cd /path/to/lido-lend-market

make deploy-run \
  CONFIG=mainnet \
  RUN=anvil-easy-track \
  RPC_URL=http://127.0.0.1:8545 \
  DEPLOYER_PRIVATE_KEY="$ANVIL_DEPLOYER_PRIVATE_KEY" \
  VERIFY=false
```

Use a temporary deployment config whose market `pausers` list contains its intended CircuitBreaker; do not
edit the committed config merely to run a rehearsal.

No separate activation artifact is generated or required. Each `deployed/<RUN>/markets/<market-name>.toml`
contains the resolved market, curve, role, and CircuitBreaker values. The market steward, pauser committee,
and settlement flag remain runtime motion choices: the scenarios use deterministic nonzero addresses and
exercise both settlement values.

Then run the EasyTrack scenarios in terminal 2:

```bash
cd /path/to/easy-track

ATTACH_EXTERNAL_NODE=true \
LIDO_LEND_ARTIFACTS_DIR=/path/to/lido-lend-market/deployed/anvil-easy-track \
poetry run brownie test tests/integration/lido_lend --network mainnet-fork -s
```

Brownie attaches to the already-listening Anvil because `mainnet-fork` points at port 8545. Keep Anvil running;
otherwise Brownie starts the network command configured for `mainnet-fork`, which is a different test setup.
`ATTACH_EXTERNAL_NODE` accepts `1`, `true`, `yes`, or `on`, case-insensitive. Leave it unset for the local stub
run, where Brownie owns the node.

## Useful focused run

Activation only:

```bash
poetry run brownie test \
  tests/integration/lido_lend/test_activate_market_scenario.py \
  --network mainnet-fork -s
```
