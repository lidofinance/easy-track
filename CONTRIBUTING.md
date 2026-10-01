# Easy Track Contribution Guide

Thank you for contributing to Easy Track. This guide explains how to set up the repository, what conventions to follow, and what a pull request must contain before the maintainers merge it. The merge requirements are written as checks, so a human reviewer or an agent can verify each one from the PR and the repository.

## Ways to Contribute

> [!CAUTION]
> Report vulnerabilities in contracts through the [Lido Bug Bounty on Immunefi](https://immunefi.com/bounty/lido/) (see [bugbounty.md](bugbounty.md)), not through GitHub issues.

- **Issues.** Use GitHub issues for bugs in off-chain code (tests, scripts, tooling) and for feature requests. Check for an existing issue first.
- **Code.** Most contributions add or change an EVMScript factory. Read [EVMScript Factory Requirements](README.md#evmscript-factory-requirements) in the README before you start.
- **Tooling and CI.** Open an issue to discuss the change first.

## Responsibilities

- **Contract developers** are responsible for the correctness and security of the contract code they submit. They get it right through internal review and external audits.
- **Maintainers** check process and repository hygiene: tests, deployments, CI, deploy scripts, shared-module safety and scope. An approval into `develop` does not mean the contract logic has been audited. An approval into `master` does, because maintainers merge only audited contract code (see [R8](#r8-audit-master-only)).

## Getting Started

### Requirements

- Node.js 22 (version pinned in `.nvmrc`)
- Python 3.10 (version pinned in `.python-version`) and [Poetry](https://python-poetry.org/)
- [Foundry](https://book.getfoundry.sh/), for the Foundry scenario tests and Slither

### Setup

```bash
git clone https://github.com/lidofinance/easy-track
cd easy-track
nvm install
npm ci
poetry install
poetry run brownie networks import network-config.yaml True
```

Copy `.env.sample` to `.env` and set `MAINNET_RPC_URL` and `HOODI_RPC_URL`. Foundry loads `.env` automatically. Brownie does not, so also export the mainnet RPC URL in your shell:

```bash
export MAINNET_RPC_URL=<YOUR_RPC_URL>
```

### Running Tests

```bash
poetry run brownie test --network mainnet-fork   # Brownie unit, integration and scenario tests
CHAIN=hoodi forge test -vv                       # Foundry scenario tests against deployed factories
```

See the [Tests](README.md#tests) section of the README and [test/foundry/README.md](test/foundry/README.md) for more options.

## Repository Structure

| Path                            | Contents                                                                   |
| ------------------------------- | -------------------------------------------------------------------------- |
| `contracts/`                    | Core contracts (`EasyTrack.sol`, `EVMScriptExecutor.sol`, ...)             |
| `contracts/EVMScriptFactories/` | EVMScript factories                                                        |
| `scripts/`                      | Deploy scripts (Brownie)                                                   |
| `tests/`                        | Brownie tests: `evm_script_factories/` (unit), `integration/`, `scenario/` |
| `test/foundry/`                 | Foundry fork scenario tests for deployed factories                         |
| `utils/`                        | Shared Python helpers and network config                                   |
| `deployed-*.json`               | Deployment artifacts, one file per network and area                        |

## EVMScript Factories

### How a factory is used

1. A motion creator calls `EasyTrack.createMotion(factory, calldata)`. Who may create a motion is up to the factory: usually a single trusted caller such as a committee multisig, but some factories allow any eligible address, such as a node operator or its manager. Easy Track calls `factory.createEVMScript(creator, calldata)`, checks that the script calls only the (contract, method) pairs registered for that factory, and stores the script's hash.
2. The motion runs for the motion duration. LDO holders can object; if objections reach the threshold, the motion is rejected.
3. Anyone calls `EasyTrack.enactMotion(motionId, calldata)`. Easy Track calls `createEVMScript` **again** with the same calldata, requires the same hash, and runs the script through `EVMScriptExecutor`.

All validation in `createEVMScript` therefore runs twice, against the state at creation and at enactment. If the state changes in between so that validation fails or the script differs, enactment reverts.

### Requirements

- Implement [`IEVMScriptFactory`](contracts/interfaces/IEVMScriptFactory.sol). Mark `createEVMScript` as `view`.
- Restrict who can create motions: inherit [`TrustedCaller`](contracts/TrustedCaller.sol) and apply `onlyTrustedCaller(_creator)`, or do an explicit check on `_creator` when the creator is not a fixed address (see `IncreaseVettedValidatorsLimit.sol`, `AllowConsolidationPair.sol`).
- Build the script with [`EVMScriptCreator`](contracts/libraries/EVMScriptCreator.sol), never by hand.
- Provide a public `decodeEVMScriptCallData`, so anyone can read a motion's parameters on-chain.
- Validate all input before building the script. Revert on anything the target contract would reject, and on anything outside the factory's bounds.
- Request the narrowest permissions: only the (contract, method) pairs the script calls. They are registered with `EVMScriptFactoriesRegistry.addEVMScriptFactory(factory, permissions)` as concatenated 20-byte address + 4-byte selector pairs.
- Every action a factory performs must also be possible through Aragon Voting. `EVMScriptExecutor` must hold the role that the target method requires.

### Best practices

- **Bound each motion.** Put limits on what one motion can change, as immutables set in the constructor: a maximum value (`SetDepositsReserveTarget`) or a maximum change per motion (`UpdateStakingModuleShareLimits`). Larger changes go through a DAO vote.
- **Commit the current value.** Include the expected current state in the calldata and require it to match the chain (`CURRENT_VALUES_MISMATCH` in `UpdateStakingModuleShareLimits`). The motion then enacts only if nothing changed since token holders reviewed it.
- **Reject no-op motions** whose new value equals the current one (`SAME_DEPOSITS_RESERVE_TARGET`, `NO_CHANGES`).
- **Check batch input.** Reject empty input, require equal array lengths, and require IDs to be in range and strictly ascending, which also rules out duplicates.
- **Treat a factory as immutable.** Set all configuration in the constructor, as `immutable` where the type allows it (a `string` such as `name` cannot be), and check addresses for zero. To change parameters, deploy a new factory, register it, and remove the old one.
- **Name instances.** When one contract is deployed for several modules, add `string public name` (for example `CSM`, `CM`) and use it in the artifact key (`<Contract>:<Instance>`).
- **Follow the code style of existing factories:**
  - errors as `string private constant ERROR_<NAME> = "<NAME>";` with `require(cond, ERROR_<NAME>)`, not custom errors;
  - banner-separated sections `ERRORS → CONSTANTS → IMMUTABLES → VARIABLES → CONSTRUCTOR → EXTERNAL METHODS → PRIVATE METHODS`, omitting empty ones;
  - NatSpec on public and external functions, with the calldata encoding documented on `createEVMScript`;
  - decoding in a private `_decodeEVMScriptCallData` that the public decoder calls;
  - `calldata` for read-only external parameters;
  - `pragma solidity 0.8.6;` in new factories.

Start from [`SetDepositsReserveTarget.sol`](contracts/EVMScriptFactories/SetDepositsReserveTarget.sol) for a single call, or [`UpdateStakingModuleShareLimits.sol`](contracts/EVMScriptFactories/UpdateStakingModuleShareLimits.sol) for bounded changes, committed current values and named instances. `SetDepositsReserveTarget` departs from two of the rules above: in new code, use `require` instead of `if (...) revert(...)`, and check constructor addresses for zero.

## Conventions

- **Solidity.** See the code style in [EVMScript Factories](#best-practices). Contracts compile with solc 0.8.6 (EVM `berlin`, optimizer off).
- **Formatting.** Solidity and JSON files are formatted with Prettier (`npm run lint:check`). Python is formatted with Black, line length 120.
- **Commits.** Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/): `feat:`, `fix:`, `chore:`, and so on.

## Branches

| Branch    | Network          | Meaning of a merge                             |
| --------- | ---------------- | ---------------------------------------------- |
| `develop` | Hoodi (testnet)  | The change is tested and deployed on testnet.  |
| `master`  | Ethereum mainnet | The change is audited and deployed on mainnet. |

Open PRs against `develop`. A change reaches `master` only after it has been merged into `develop`.

## Pull Request Requirements

A PR into `develop` must meet R1–R6. A PR into `master` must meet R1–R8.

### R1. Tests match the test plan

A **test plan** is provided with the PR, usually outside the PR description: the list of behaviours that must be tested. For a factory it covers at least:

- the happy path: the EVMScript produced for valid input (target address, function selector, encoded arguments);
- every `require` / revert path in `createEVMScript` and in the constructor;
- access control: a call from an address other than the trusted caller reverts;
- `decodeEVMScriptCallData`: a round trip of valid calldata, and a revert on malformed calldata;
- a scenario test of the motion lifecycle: create the motion, wait for the motion duration, enact it, then check the on-chain effect.

**Check:** every item in the test plan has at least one test. Each test asserts on the result (the EVMScript bytes or the on-chain state). A test that only checks that a call did not revert does not count.

### R2. Testnet deployment, with addresses in the PR

Each new or changed contract is deployed on Hoodi, and the PR adds its entry to the matching artifact file:

| Contracts                               | Artifact file            |
| --------------------------------------- | ------------------------ |
| Staking-module factories (CSM, CM, ...) | `deployed-sm-hoodi.json` |
| Staking-router factories                | `deployed-sr-hoodi.json` |
| Other contracts                         | `deployed-hoodi.json`    |

```json
"SetDepositsReserveTarget": {
    "contract": "SetDepositsReserveTarget",
    "address": "0x...",
    "constructorArgs": ["0x...", 1000, "0x..."],
    "txHash": "0x..."
}
```

If the same contract is deployed more than once, the key is `<Contract>:<Instance>`, for example `UpdateStakingModuleShareLimits:CSM`.

**Check:** each new contract has an entry with all four fields, and `contract` matches the contract name.

### R3. CI is green

All GitHub Actions checks on the PR pass. Two workflows run on every PR into `develop` or `master`.

**`Tests`** ([tests.yml](.github/workflows/tests.yml)) has four jobs:

| Job                            | What it runs                                                                                                                                                                                                                              | Network      |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Unit Tests                     | Brownie unit tests under `tests/` (everything except `integration/`, `scenario/` and the DateTime library test). Each test deploys the contracts it needs from scratch.                                                                   | mainnet fork |
| Unit Tests - DateTime Library  | `tests/test_bokky_poo_bahs_date-time-library.py`, run as a separate job                                                                                                                                                                   | mainnet fork |
| Integration & Scenario Tests   | `tests/integration/` loads deployed factories by address from `deployed-mainnet.json` and `integration-test-addresses-mainnet.yaml`. `tests/scenario/` deploys fresh factories and runs full motions against the real mainnet Easy Track. | mainnet fork |
| Foundry Scenario Tests (Hoodi) | `test/foundry/scenario/`. Each test drives a factory that is already deployed through a full motion: create, wait, enact, then check the effect on-chain. Addresses come from `deployed-{sr,sm}-hoodi.json`.                              | Hoodi fork   |

The Foundry scenario tests cover the staking-router and staking-module factories, and set up only the data a motion needs, such as operators or penalties. They fail if the factory is not registered in Easy Track on Hoodi, or if the executor lacks the roles the motion needs. They therefore pass only after the Hoodi deployment from R2 is complete.

**`Slither Analysis`** ([slither.yml](.github/workflows/slither.yml)) runs static analysis on `contracts/`. It runs with `--fail-none`, so it passes even when Slither reports findings. Check the PR's code-scanning alerts.

To reproduce a failing job locally, run the same command:

```bash
poetry run brownie test --ignore=tests/integration --ignore=tests/scenario \
  --ignore=tests/test_bokky_poo_bahs_date-time-library.py -s --network mainnet-fork
poetry run brownie test tests/integration/ -s --network mainnet-fork
poetry run brownie test tests/scenario/ -s --network mainnet-fork
CHAIN=hoodi forge test -vv
```

**Check:** `gh pr checks <PR>` shows no failed or pending checks. A local test run does not replace CI.

### R4. Deploy scripts are correct

Each new contract has a deploy script in `scripts/`. Use [deploy_set_deposits_reserve_target_factory.py](scripts/deploy_set_deposits_reserve_target_factory.py) as the reference. It writes a single entry to `deployed-{network}.json`. For a named staking-module or staking-router factory, follow [deploy_update_staking_module_share_limits_factory.py](scripts/deploy_update_staking_module_share_limits_factory.py), which writes `<Contract>:<Instance>` to `deployed-sr-{network}.json` (staking-module factories write `deployed-sm-{network}.json`). The script:

- passes constructor arguments in the same order and with the same types as the contract's constructor;
- reads network-specific values from `utils/` config or environment variables, with no hard-coded secrets or private keys;
- prints the network, the deployer and every constructor argument, then asks for confirmation before it deploys;
- writes the R2 entry to the correct `deployed-*.json` file when it runs on a live network.

**Check:** the recorded `constructorArgs` are what the script produces for that network.

### R5. No breaking changes in shared modules

These files are shared by every factory:

- `contracts/EasyTrack.sol`, `EVMScriptExecutor.sol`, `EVMScriptFactoriesRegistry.sol`, `MotionSettings.sol`, `LimitsChecker.sol`, `TrustedCaller.sol`
- `contracts/libraries/`
- `contracts/interfaces/IEVMScriptFactory.sol`, `contracts/interfaces/IEasyTrack.sol`
- shared test code: `utils/*.py`, `tests/conftest.py`, `tests/scenario/conftest.py`, `test/foundry/helpers/`

Additions (a new fixture, a new network entry) are fine. Changes to the behaviour or signature of existing code can break deployed contracts or other tests without a visible failure.

**Check:** the PR changes no existing code in these files. If it has to, the PR description explains why and lists the affected contracts and tests.

### R6. No out-of-scope changes

The PR changes only what its title and description say. Typical out-of-scope changes: edits to factories the PR does not name, dependency files (`package.json`, `pyproject.toml`, lock files, `brownie-config.yaml`), CI (`.github/`), mainnet artifacts in a PR into `develop`, and unrelated refactoring or formatting.

**Check:** every changed file is needed for the stated change. If a file differs only because the target branch has moved on, rebase the PR. That is not an out-of-scope change.

### R7. Mainnet deployment, with addresses in the PR (`master` only)

The same as R2, on mainnet: entries in `deployed-sm-mainnet.json`, `deployed-sr-mainnet.json` or `deployed-mainnet.json`.

**Check:** each new contract has a mainnet entry with all four fields, and its `constructorArgs` match the deploy script (R4) for mainnet.

### R8. Audit (`master` only)

New and changed contracts are audited. Each audit report is provided with the PR, usually outside the PR description, as a link to the report in the [lidofinance/audits](https://github.com/lidofinance/audits) repository, for example `MixBytes Easy Track for Deposit Reserve Target management Audit Report 09-2026.pdf`. Links to reports hosted anywhere else do not count; add the report to that repository first.

**Check:**

- every new or changed contract is covered by a linked report under `https://github.com/lidofinance/audits/`;
- the contract code being merged is the code that was audited; later changes to tests, scripts or artifacts do not need a new audit;
- the bytecode deployed on mainnet matches the audited source, shown in the PR (for example with a diffyscan report or a bytecode comparison).

## Checklist

Into `develop`:

- [ ] R1: test plan provided, and every item has a test
- [ ] R2: deployed on Hoodi, entries added to `deployed-*-hoodi.json`
- [ ] R3: all CI checks green
- [ ] R4: deploy script present, and its arguments match the constructor and the recorded `constructorArgs`
- [ ] R5: no existing code in shared modules changed, or the change is justified
- [ ] R6: no files outside the PR scope

Into `master`, also:

- [ ] R7: deployed on mainnet, entries added to `deployed-*-mainnet.json`
- [ ] R8: audit report in `lidofinance/audits` provided, the audited contract code matches the merged code, and the mainnet bytecode matches the audited source
