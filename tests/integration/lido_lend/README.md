# Lido Lend EasyTrack scenarios

The suite has two modes:

- without `LIDO_LEND_REGISTRY`, it deploys strict local stubs and checks the complete EasyTrack motion flow;
- with `LIDO_LEND_REGISTRY`, it attaches to an existing Anvil mainnet fork, reads the Lido Lend deployment
  registry plus `activation-<market>.toml`, and exercises the deployed contracts through the real mainnet
  EasyTrack and EVMScriptExecutor.

The fork loader rejects mismatched registry/activation market parameters, addresses without bytecode, or an
executor different from the configured EasyTrack executor. It deliberately does not compare the artifact chain
ID with `eth_chainId`: a local Hardhat/Anvil fork may report `31337` while hosting an Ethereum deployment whose
artifacts correctly identify chain ID `1`.

## Local stub scenarios

From the EasyTrack repository:

```bash
poetry run brownie test tests/integration/lido_lend --network mainnet-fork -s
```

Do not set `LIDO_LEND_REGISTRY` for this run.

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
  DEPLOYER_PRIVATE_KEY="$ANVIL_DEPLOYER_PRIVATE_KEY"
```

The generated activation plan intentionally contains a zero `pauser_committee` TODO. Fill
`deployed/anvil-easy-track/activation-<market>.toml` with the committee address that the activation scenarios
should register. Management scenarios can run before this is filled; activation-dependent scenarios will
skip with an explicit reason.

Then run the EasyTrack scenarios in terminal 2:

```bash
cd /path/to/easy-track

LIDO_LEND_ATTACH=1 \
LIDO_LEND_REGISTRY=/path/to/lido-lend-market/deployed/anvil-easy-track/registry.toml \
LIDO_LEND_MARKET=weth-wsteth \
poetry run brownie test tests/integration/lido_lend --network mainnet-fork -s
```

Brownie attaches to the already-listening Anvil because `mainnet-fork` points at port 8545. Keep Anvil running;
otherwise Brownie starts the network command configured for `mainnet-fork`, which is a different test setup.

## Useful focused run

Activation only:

```bash
poetry run brownie test \
  tests/integration/lido_lend/test_activate_market_scenario.py \
  --network mainnet-fork -s
```
