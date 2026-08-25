# Lido Lend EasyTrack factories deployment

This runbook covers deployment of the Lido Lend EVMScript factories from the EasyTrack repository.
It does not deploy the Lido Lend protocol and does not register the deployed factories in EasyTrack.

The workflow has three separate stages:

1. deploy the Lido Lend protocol;
2. deploy the selected EasyTrack factories;
3. register the desired factories in EasyTrack through the governance process.

This document covers stage 2 and the inputs it requires from stage 1.

## Inputs to preserve

Record these items for every deployment:

- EasyTrack and Lido Lend git commits;
- network and chain ID;
- RPC fork block for a rehearsal, or the production block range;
- Lido Lend deployment directory containing `protocol.toml`, `markets/`, and optional `exit-books.toml`;
- trusted caller address;
- selected factory names;
- deployer address;
- `et-lido-lend-deployed-<network>-<chain-id>-<block>.json`;
- deployment transaction hashes and the final block number.

Do not copy addresses from a deployment on another node merely because it uses the same network name. Verify
that every address has bytecode on the node used for the factory deployment.

## Lido Lend artifact input

Set `LIDO_LEND_ARTIFACTS_DIR` to one immutable Lido Lend deployment directory. The script reads protocol
addresses from `protocol.toml`, the CircuitBreaker from `markets/*.toml`, and exit-book addresses from
`exit-books.toml`. It rejects mixed artifacts by comparing `deployment`, `chain_id`, and `config_hash`, and
cross-checks each market with its linked oracle and GuardianSignals artifacts.

`TRUSTED_CALLER` is the committee address allowed to create motions through the deployed factories.

## Fixed permission model

The generated permissions do not contain market-controller or GuardianSignals addresses. Market and guardian
factories call the fixed `LidoLendOwner` facade, which resolves the market-specific contracts from `marketId`.
IRM factories call the fixed IrmRouter and AdaptiveCurveIrm instances. Exit-book targets are supplied in
motion calldata, while the generated EasyTrack permissions restrict execution to the exit books from the
deployment artifacts.

Adding a market or giving it a fresh GuardianSignals registry therefore does not require changing an existing
factory's EasyTrack permission. A permission changes only when its fixed protocol target changes or a factory
is deployed with a different target.

## Selecting factories

`LIDO_LEND_FACTORIES` is an optional comma-separated list. If it is not set, all factories are deployed.
Both short names and full contract names are accepted:

```bash
export LIDO_LEND_FACTORIES=MarketManagerActions,GuardianActions
```

is equivalent to:

```bash
export LIDO_LEND_FACTORIES=LidoLendMarketManagerActions,LidoLendGuardianActions
```

The supported short names are:

```text
ActivateMarket
RegisterPauser
GuardianActions
MarketManagerActions
RiskStewardActions
IrmActions
ExitBookActions
```

An empty list, an unknown name, or a duplicate is rejected before deployment.

The script resolves only the protocol components used by the selected factories. `ActivateMarket` requires
the protocol RiskStewardDashboard and shared CircuitBreaker; `RegisterPauser` requires the shared
CircuitBreaker. Activation still performs the initial pauser registration, while `RegisterPauser` supports a
standalone registration, replacement, or removal motion.

Grouped factories decode `abi.encode(Action, payload)`. Existing action ordinals are unchanged; the new
actions are appended as `MarketManagerActions.SetFee = 5` and `ExitBookActions.SetServiceFee = 2`.

| Selected factories | Required artifacts |
| --- | --- |
| All selections | `protocol.toml` and at least one `markets/*.toml` |
| ActivateMarket | protocol RiskStewardDashboard and shared CircuitBreaker |
| RegisterPauser | shared CircuitBreaker |
| ExitBookActions | `exit-books.toml` |

## Anvil rehearsal

Start a persistent Anvil node with Ethereum mainnet's chain ID in terminal 1:

```bash
cd /path/to/easy-track

anvil \
  --fork-url "$MAINNET_RPC_URL" \
  --chain-id 1 \
  --port 8545
```

Deploy Lido Lend to this exact node from the Lido Lend repository. Use a new deployment directory:

```bash
cd /path/to/lido-lend-market

make deploy-run \
  CONFIG=mainnet \
  RUN=anvil-easy-track \
  RPC_URL=http://127.0.0.1:8545 \
  DEPLOYER_PRIVATE_KEY="$ANVIL_DEPLOYER_PRIVATE_KEY" \
  VERIFY=false
```

Before this deployment, copy the market config used for the rehearsal instead of editing the committed
`weth-wsteth.toml`. Its `pausers` list must contain the CircuitBreaker address intended for that market; an
empty list is intentionally incomplete and must not be used to produce acceptance artifacts.

No separate activation artifact is part of this workflow. Market artifacts contain the resolved activation
inputs and CircuitBreaker.

Keep Anvil running. Addresses from a different node are not valid unless the resulting bytecode is demonstrably
present at the same addresses.

Export the selected factory set and its required addresses in terminal 2. A minimal deployment looks like:

```bash
cd /path/to/easy-track

export LIDO_LEND_ARTIFACTS_DIR=/path/to/lido-lend-market/deployed/anvil-easy-track
export TRUSTED_CALLER=<committee-address>
export LIDO_LEND_FACTORIES=MarketManagerActions
```

Run the standard Brownie deployment command:

```bash
poetry run brownie run deploy_lido_lend_factories \
  --network mainnet-fork
```

Because Anvil is already listening on port 8545, Brownie attaches to it. If no node is listening, Brownie
starts a fresh fork; that fresh fork will not contain the separately deployed Lido Lend contracts.

Review the displayed network, chain ID, deployer, executor, selected factories, and protocol addresses before
answering `yes`.

## Preflight

Before preparing the development deployer or sending deployment transactions, the script validates the
selected topology:

- all consumed artifacts belong to one deployment, chain ID, and config hash;
- market IDs and linked oracle/GuardianSignals addresses are internally consistent;
- the facade points to the expected core and `core.owner()` points back to that facade;
- IRM router, curve, dashboard, and exit book bindings point to the expected core/router;
- the executor read from the actual EasyTrack contract equals the protocol artifact executor;
- for `ActivateMarket` and `RegisterPauser`, the shared `CircuitBreaker.ADMIN` equals that executor;
- for `ActivateMarket`, the executor has the owner's `MARKET_CREATOR_ROLE` and `FEE_MANAGER_ROLE`, plus the
  dashboard's `STEWARD_ADMIN_ROLE`;
- the executor has the owner, IRM, dashboard, and exit-book roles required by the selected factories.

Any failure stops the script before factory deployment.

## Fee-management scope

`ActivateMarket` accepts an initial market fee of at most 25%. A nonzero fee is installed as the final action;
zero leaves the core's default fee unchanged and omits that call.

`MarketManagerActions.SetFee` changes one market fee through `LidoLendOwner`. The EVMScriptExecutor must hold
`FEE_MANAGER_ROLE` on the owner facade.

`ExitBookActions.SetServiceFee` applies one recipient and service-fee rate to a non-empty ordered list of exit
books. The rate is capped at 25%; a zero recipient is accepted only with a zero rate. The factory accepts any
non-zero target in calldata, while its EasyTrack permission blob permits `setServiceFee` only on the Morpho
and ERC-4626 exit books from the protocol artifacts. The executor must hold `FEE_MANAGER_ROLE` on both.

## Production deployment

Set the reviewed immutable Lido Lend deployment directory and the Brownie account name:

```bash
export DEPLOYER=<brownie-account-name>
export LIDO_LEND_ARTIFACTS_DIR=/path/to/lido-lend-market/deployed/<production-run>
export TRUSTED_CALLER=<committee-address>
export LIDO_LEND_FACTORIES=<comma-separated-factory-list>
```

Run:

```bash
poetry run brownie run deploy_lido_lend_factories \
  --network mainnet
```

On a live network the script sets the configured priority and maximum fees and publishes the selected
factory sources after deployment.

## Deployment artifact

The script writes a new, non-overwriting artifact:

```text
et-lido-lend-deployed-<network>-<chain-id>-<block>.json
```

There is one entry per deployed factory:

```json
{
  "LidoLendMarketManagerActions": {
    "contract": "LidoLendMarketManagerActions",
    "address": "0x...",
    "constructorArgs": ["0x...", "0x..."],
    "permissions": "0x..."
  }
}
```

`permissions` is the exact fixed EasyTrack permission blob for that factory. The artifact contains only
deployed factories; it does not claim that any factory is registered in EasyTrack.

After deployment:

1. confirm that the artifact contains exactly the selected factories;
2. confirm bytecode exists at every resulting address;
3. compare constructor arguments with the reviewed immutable Lido Lend artifacts;
4. preserve the artifact and console/transaction output with the deployment record;
5. use the permissions blobs as inputs to the separate governance registration process.

## Tests

The Lido Lend integration test modes and focused commands are documented in
[`tests/integration/lido_lend/README.md`](../tests/integration/lido_lend/README.md).
