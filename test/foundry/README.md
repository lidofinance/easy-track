# Foundry tests

Two suites, each on its own profile in `foundry.toml`. The tests are a port of the Brownie suite in `tests/`, see [BROWNIE-PORT.md](BROWNIE-PORT.md) for the mapping and the differences.

| Directory | Suite | Profile | Network |
|---|---|---|---|
| `unit/` | Unit tests of the contracts under `contracts/`, with the factories in `unit/factories/`, the libraries in `unit/libraries/` and the payouts contracts in `unit/payouts/`. Shared encoders and constants in `unit/helpers/`, stand-ins for the Aragon contracts in `unit/stubs/` | `default`, solc 0.8.6 | none |
| `scenario/` | Fork tests of the deployed factories of `deployed-*.json`, one directory per module: `sr`, `sm`, `sdvt`, `vebo`, `mevboost`, `vaults`, `lido`, `payouts` and `aragon` for the DAO apps and the Foundry scripts | `scenario`, solc 0.8.38 | a fork of hoodi or mainnet |
| `helpers/` | Base contracts of the scenario suite | `scenario` | |
| `interfaces/` | Interfaces of the deployed contracts the scenario suite calls | `scenario` | |

The Foundry scripts under `script/` compile with the scenario profile too, see the root README.

## Setup

[Foundry](https://getfoundry.sh) and `npm install`, which brings forge-std as a dependency. The scenario suite reads `HOODI_RPC_URL` and `MAINNET_RPC_URL` from `.env`, see `.env.sample`, and `CHAIN` selects the network, default `hoodi`.

## Unit suite

```bash
forge test                                   # also npm test, just test
forge test --match-contract EasyTrackTest    # one contract
```

## Scenario suite

Some tests deploy fresh factories from the artifacts `forge build` writes to `out/`, so the contracts are built first. Without an RPC URL every scenario contract is reported as skipped.

```bash
CHAIN=hoodi   npm run test:scenario          # forge build && FOUNDRY_PROFILE=scenario forge test
CHAIN=mainnet npm run test:scenario
CHAIN=hoodi   FOUNDRY_PROFILE=scenario forge test --mc SettleGeneralDelayedPenalty -vvv   # one factory
```

The `justfile` recipes run the suite on a local Anvil fork when one is up on `ANVIL_PORT`, default 8545, else on `<CHAIN>_RPC_URL`. The fork's chain selects the network, and forge keeps every state change in memory, so the fork is left untouched between runs:

```bash
CHAIN=mainnet just make-fork                 # start the Anvil fork, reused if already running
just test-scenario                           # build, then run against it
just test-scenario --mc VaultHub             # one suite
```

## Formatting

The tests and scripts are formatted with `forge fmt`, never prettier. `contracts/` is excluded from both the formatter and the linter.

```bash
just fmt                                     # forge fmt test/foundry script
forge fmt --check test/foundry script
```

## CI

`tests.yml` runs the unit suite and the format check on every pull request, and the scenario suite on Hoodi.
