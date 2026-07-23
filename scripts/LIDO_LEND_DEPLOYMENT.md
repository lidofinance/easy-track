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
- Lido Lend deployment directory containing `registry.toml` and the activation plans;
- trusted caller address;
- selected factory names;
- deployer address;
- `et-lido-lend-deployed-<network>-<chain-id>-<block>.json`;
- deployment transaction hashes and the final block number.

Do not copy addresses from a deployment on another node merely because it uses the same network name. Verify
that every address has bytecode on the node used for the factory deployment.

## Lido Lend address mapping

The deployment script reads protocol addresses from environment variables because Lido Lend is deployed from
a separate repository.

| Environment variable | Lido Lend artifact |
| --- | --- |
| `LIDO_LEND_CORE` | `registry.toml`: `protocol.core` |
| `LIDO_LEND_OWNER` | `registry.toml`: `protocol.owner_facade` |
| `LIDO_LEND_IRM_ROUTER` | `registry.toml`: `protocol.irm_router` |
| `LIDO_LEND_ADAPTIVE_CURVE_IRM` | `registry.toml`: `protocol.adaptive_curve_irm` |
| `LIDO_LEND_CIRCUIT_BREAKER` | `activation-<market>.toml`: `activation.circuit_breaker` |
| `LIDO_LEND_RISK_STEWARD_DASHBOARD` | `registry.toml`: `protocol.risk_steward_dashboard` |
| `LIDO_LEND_MORPHO_EXIT_BOOK` | `registry.toml`: `exit_books.morpho` |
| `LIDO_LEND_ERC4626_EXIT_BOOK` | `registry.toml`: `exit_books.erc4626` |

`TRUSTED_CALLER` is the committee address allowed to create motions through the deployed factories.

## Fixed permission model

The generated permissions do not contain market-controller or GuardianSignals addresses. Market and guardian
factories call the fixed `LidoLendOwner` facade, which resolves the market-specific contracts from `marketId`.
IRM factories call the fixed IrmRouter and AdaptiveCurveIrm instances; the remaining factories call the fixed
dashboard or exit books supplied at deployment.

Adding a market or giving it a fresh GuardianSignals registry therefore does not require changing an existing
factory's EasyTrack permission. A permission changes only when its fixed protocol target changes or a factory
is deployed with a different target.

## Selecting factories

`LIDO_LEND_FACTORIES` is an optional comma-separated list. If it is not set, all factories are deployed.
Both short names and full contract names are accepted:

```bash
export LIDO_LEND_FACTORIES=SetSupplyCap,AddGuardian
```

is equivalent to:

```bash
export LIDO_LEND_FACTORIES=LidoLendSetSupplyCap,LidoLendAddGuardian
```

The supported short names are:

```text
ActivateMarket
AddGuardian
RemoveGuardian
ReplaceGuardian
GrantInstantActivation
SetGuardiansQuorum
SetSuspectWindow
UnbanGuardianSignals
SetCollateralActivationConfig
SetSettlementConfig
SetSupplyCap
UnfreezeMarket
SetIrmCurveParams
SetMarketIrm
AddRiskSteward
RemoveRiskSteward
SetMarketExitBookAllowed
```

An empty list, an unknown name, or a duplicate is rejected before deployment.

The script only requires optional protocol addresses used by the selected factories. `LIDO_LEND_CORE` and
`LIDO_LEND_CIRCUIT_BREAKER` are always required by the preflight: the core anchors protocol bindings and
`CircuitBreaker.ADMIN` identifies the EVMScriptExecutor whose roles must be checked.

| Selected factories | Additional required addresses |
| --- | --- |
| Activate, market-management, or guardian factories | `LIDO_LEND_OWNER` |
| Activate or IRM factories | `LIDO_LEND_IRM_ROUTER` |
| Activate or curve-parameter factories | `LIDO_LEND_ADAPTIVE_CURVE_IRM` |
| Risk steward factories | `LIDO_LEND_RISK_STEWARD_DASHBOARD` |
| Exit book factory | both exit book addresses |

## Hardhat rehearsal

Start a persistent Hardhat node in terminal 1:

```bash
cd /path/to/easy-track

npx hardhat node \
  --fork "$MAINNET_RPC_URL" \
  --port 8545
```

Deploy Lido Lend to this exact node from the Lido Lend repository. Use a new deployment directory:

```bash
cd /path/to/lido-lend-market

make deploy-run \
  CONFIG=mainnet \
  RUN=hardhat-easy-track \
  RPC_URL=http://127.0.0.1:8545 \
  DEPLOYER_PRIVATE_KEY="$HARDHAT_DEPLOYER_PRIVATE_KEY"
```

Keep Hardhat running. Addresses from an Anvil deployment or a different Hardhat process are not valid unless
the resulting bytecode is demonstrably present at the same addresses.

Export the selected factory set and its required addresses in terminal 2. A minimal deployment looks like:

```bash
cd /path/to/easy-track

export TRUSTED_CALLER=<committee-address>
export LIDO_LEND_FACTORIES=SetSupplyCap
export LIDO_LEND_CORE=<registry.protocol.core>
export LIDO_LEND_OWNER=<registry.protocol.owner_facade>
export LIDO_LEND_CIRCUIT_BREAKER=<activation.circuit_breaker>
```

Run the standard Brownie deployment command:

```bash
poetry run brownie run deploy_lido_lend_factories \
  --network mainnet-fork
```

Because Hardhat is already listening on port 8545, Brownie attaches to it. If no node is listening, Brownie
starts a fresh Hardhat fork; that fresh fork will not contain the separately deployed Lido Lend contracts.

Review the displayed network, chain ID, deployer, executor, selected factories, and protocol addresses before
answering `yes`.

## Preflight

Before preparing the development deployer or sending deployment transactions, the script validates the
selected topology:

- every required address has contract bytecode;
- owner, IRM router, curve, dashboard, and exit book bindings point to the expected core/router;
- `CircuitBreaker.ADMIN` is nonzero and is used as the expected EVMScriptExecutor;
- the executor has the owner, IRM, dashboard, and exit-book roles required by the selected factories.

Any failure stops the script before factory deployment.

## Production deployment

Set the same protocol inputs using addresses from the reviewed production Lido Lend deployment. Also set the
Brownie account name:

```bash
export DEPLOYER=<brownie-account-name>
export TRUSTED_CALLER=<committee-address>
export LIDO_LEND_FACTORIES=<comma-separated-factory-list>

export LIDO_LEND_CORE=<address>
export LIDO_LEND_CIRCUIT_BREAKER=<address>

# Set the remaining variables required by the selected factories.
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
  "LidoLendSetSupplyCap": {
    "contract": "LidoLendSetSupplyCap",
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
3. compare constructor arguments with the reviewed inputs;
4. preserve the artifact and console/transaction output with the deployment record;
5. use the permissions blobs as inputs to the separate governance registration process.

## Tests

The Lido Lend integration test modes and focused commands are documented in
[`tests/integration/lido_lend/README.md`](../tests/integration/lido_lend/README.md).
