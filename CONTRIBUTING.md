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

Copy `.env.sample` to `.env` and set `MAINNET_RPC_URL` and `HOODI_RPC_URL`. Foundry loads `.env` automatically. Brownie does not, so also export them in your shell. A deploy script on a live network also needs `DEPLOYER`, the name of a Brownie account (create one with `poetry run brownie accounts new <name>`):

```bash
export MAINNET_RPC_URL=<YOUR_MAINNET_RPC_URL>
export HOODI_RPC_URL=<YOUR_HOODI_RPC_URL>
export DEPLOYER=<BROWNIE_ACCOUNT_NAME>
```

### Running Tests

```bash
poetry run brownie test --network mainnet-fork   # Brownie unit, integration and scenario tests
CHAIN=hoodi forge test -vv                       # Foundry scenario tests against deployed factories
```

See the [Tests](README.md#tests) section of the README and [test/foundry/README.md](test/foundry/README.md) for more options.

### Running a Deploy Script

Deploy scripts read their parameters from environment variables. Do a dry run on a fork first, then deploy on the live network:

```bash
TRUSTED_CALLER=0x... MAX_DEPOSITS_RESERVE_TARGET=... \
  poetry run brownie run scripts/deploy_set_deposits_reserve_target_factory.py --network hoodi-fork
TRUSTED_CALLER=0x... MAX_DEPOSITS_RESERVE_TARGET=... \
  poetry run brownie run scripts/deploy_set_deposits_reserve_target_factory.py --network hoodi
```

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
3. Anyone calls `EasyTrack.enactMotion(motionId, calldata)`. Easy Track calls `createEVMScript` **again** with the original creator and the supplied calldata, requires the generated script to have the same hash, and runs it through `EVMScriptExecutor`.

All validation in `createEVMScript` therefore runs twice, against the state at creation and at enactment. If validation fails or the script differs, enactment reverts. Easy Track commits only the script's hash: calldata parameters used only for validation can change at enactment if they produce the same script.

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

Start from [`SetDepositsReserveTarget.sol`](contracts/EVMScriptFactories/SetDepositsReserveTarget.sol) for a single call, or [`UpdateStakingModuleShareLimits.sol`](contracts/EVMScriptFactories/UpdateStakingModuleShareLimits.sol) for bounded changes and named instances. Both files predate parts of the code style: section banners, `calldata` parameters, `require` instead of `if (...) revert(...)`, and zero-address checks in the constructor. Where they differ from the list above, follow the list.

## Off-chain

### UI

Every new factory is added to the [Governance Portal](https://github.com/lidofinance/governance-portal). The UI for a factory has two parts:

- **Form.** The motion creator enters the motion parameters, and the form encodes them and calls `createMotion`.
- **View.** The motion card describes the motion, built from its decoded calldata.

By default, the UI uses only the factory contract. The form runs the checks from `createEVMScript` that need only the calldata and the factory's public getters, such as bounds, and the view shows what `decodeEVMScriptCallData` returns. The UI does not read any other contract, including the contract the motion changes, so a check against the current state (such as rejecting a no-op motion) needs form data from that contract. If the form or the view needs more than the factory, tell the maintenance team when you hand over the factory.

This is not a merge requirement, and the discussion about those details may happen outside GitHub. Contact the maintenance team early and bring the following, so the UI for your factory is complete and accurate:

- **Basics.** The display name, the category (`Staking`, `Treasury`, `stVaults`) and subcategory (`CSM0x02`, `Curated v2`, ...), who can create motions, and the testnet and mainnet addresses (R2, R7).
- **Form fields.** For each calldata parameter: a label, the unit and the input format (ETH or wei, basis points, address, list), and a default value, if any.
- **Extra form validations.** Checks that the factory does not make, for example against a third-party contract. For each: the contract, the method, the rule and the error message.
- **Form data.** Data the form reads from contracts other than the factory, for example the current value to show next to the input or prefill into it, or a list of node operators to pick from. For each: the contract and its testnet and mainnet addresses, the method, and what the value is used for.
- **View.** A one-line description of the motion and the decoded parameters it shows. List any data that is not in the calldata, such as the current value or an operator's name instead of its ID, with the same details as for form data.

For `SetDepositsReserveTarget`:

```text
Basics:      "Set deposits reserve target", Staking, no subcategory; trusted caller only;
             testnet 0x..., mainnet 0x...
Form fields: new deposits reserve target, ETH, converted to wei; no default
Validations: factory checks only (≤ MAX_DEPOSITS_RESERVE_TARGET, differs from current value)
Form data:   stETH.getDepositsReserveTarget(), shown as the current value and used for the
             "same value" check
View:        "Set deposits reserve target from <current> ETH to <new> ETH";
             <current> from stETH.getDepositsReserveTarget() while the motion is active
```

### Notifications

The Lido DAO bot posts Easy Track motions to Telegram chats. It does not send alerts in real time. There are two types of notifications:

- **Daily digest.** Posted once a day (every 8 hours on testnet) to every chat the bot is added to. It lists active motions with the time left and the objections.
- **Alert groups.** A separate message for a specific audience, such as the committee responsible for a factory. It lists the factory's motions that have passed and are waiting for enactment, or were enacted, rejected or canceled. A chat receives it only if a bot admin assigns the chat to the factory's alert group.

Each motion shows a link, a title and a description. By default, the title is the factory name and there is no description. When you hand over a factory, tell the maintenance team:

- **Title.** The name to show for the motion, usually the UI display name.
- **Description.** One line built from the decoded calldata. List any data that is not in the calldata, such as an operator's name or the current value, with the contract, its testnet and mainnet addresses and the method.

Alert groups are optional. To set one up, contact the maintenance team and tell them which group the factory belongs to (an existing one such as `node_operators`, `lego`, `rewards`, `csm`, or a new one) and which Telegram chats should receive it.

## Conventions

- **Solidity.** See the code style in [EVMScript Factories](#best-practices). Production contracts compile with solc 0.8.6 (EVM `berlin`, optimizer off). Foundry scenarios use modern Solidity interfaces in a separate profile; see [test/foundry/README.md](test/foundry/README.md#notes).
- **Formatting.** Format new Solidity files like the existing factories. The Prettier setup in the repository does not check them: `npm run lint:check` skips `contracts/EVMScriptFactories/`, and the pinned `prettier-plugin-solidity` formats function signatures differently from most existing factories. Python is formatted with Black, line length 120.
- **Commits.** Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/): `feat:`, `fix:`, `chore:`, and so on.

## Branches

| Branch    | Network          | Meaning of a merge                             |
| --------- | ---------------- | ---------------------------------------------- |
| `develop` | Testnet (Hoodi)  | The change is tested and deployed on testnet.  |
| `master`  | Ethereum mainnet | The change is audited and deployed on mainnet. |

Open PRs against `develop`. A change reaches `master` only after it has been merged into `develop`.

## Pull Request Requirements

A PR into `develop` must meet R1–R6. A PR into `master` must meet R1–R8. A PR that adds or changes neither contracts nor deployment artifacts must meet only R3, R5 and R6.

Here, contracts means production contracts. Test-only contracts under `contracts/test/` and `test/foundry/` do not require deployment, deploy scripts or audits.

### R1. Tests match the test plan

Link a **test plan** in the PR description: a list of the behaviours your tests must cover. It can live anywhere, as long as it's available for reviewers. For a factory it covers at least:

- the happy path: the EVMScript produced for valid input (target address, function selector, encoded arguments);
- every `require` / revert path in `createEVMScript` and in the constructor;
- boundary values: zero, the allowed limits, and values just outside them, where applicable;
- access control: a call from a `_creator` that may not create the motion reverts (an address other than the trusted caller, or one that fails the factory's own check on `_creator`);
- `decodeEVMScriptCallData`: a round trip of valid calldata, and a revert on malformed calldata;
- a scenario test of the motion lifecycle: create the motion, wait for the motion duration, enact it, then check the on-chain effect;
- state changes between creation and enactment, including stale expected values where applicable;
- for a staking-router or staking-module factory already registered on testnet with the required executor roles, a Foundry scenario test in `test/foundry/scenario/` that drives the testnet deployment from R2.

Use the share-limits [unit tests](tests/evm_script_factories/test_update_staking_module_share_limits.py) and [Brownie scenarios](tests/scenario/test_update_staking_module_share_limits_scenario.py) as examples, with [encoding helpers](utils/evm_script.py) and the fixtures in [tests/conftest.py](tests/conftest.py) and [tests/scenario/conftest.py](tests/scenario/conftest.py). Foundry scenarios extend [EasyTrackScenarioBase](test/foundry/helpers/EasyTrackScenarioBase.sol). Older examples may not meet every requirement above.

**Check:** every item in the test plan has at least one test. Each test asserts on the result (the EVMScript bytes, the on-chain state or the expected revert). A test that only checks that a call did not revert does not count.

### R2. Testnet deployment, with addresses in the PR

Each new or changed contract is deployed on testnet, and the PR adds its entry to the matching artifact file:

| Contracts                               | Artifact file            |
| --------------------------------------- | ------------------------ |
| Staking-module factories (CSM, CM, ...) | `deployed-sm-hoodi.json` |
| Staking-router factories                | `deployed-sr-hoodi.json` |
| Other contracts                         | `deployed-hoodi.json`    |

Older deploy scripts for vault and MEV Boost relay factories write `et-*-deployed-{network}.json` files without `txHash`. New scripts, vault factories included, use the files above.

```json
"SetDepositsReserveTarget": {
    "contract": "SetDepositsReserveTarget",
    "address": "0x...",
    "constructorArgs": ["0x...", 1000, "0x..."],
    "txHash": "0x..."
}
```

If the same contract is deployed more than once, the key is `<Contract>:<Instance>`, for example `UpdateStakingModuleShareLimits:CSM`.

Factory registration and executor role grants are handled separately and are not required to merge the PR.

**Check:** each new or changed contract has an entry with all four fields, and `contract` matches the contract name.

### R3. CI is green

All GitHub Actions checks on the PR pass. Two workflows run on every PR into `develop` or `master`.

**`Tests`** ([tests.yml](.github/workflows/tests.yml)) has four jobs:

| Job                            | What it runs                                                                                                                                                                                                                | Network      |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| Unit Tests                     | Brownie unit tests under `tests/` (everything except `integration/`, `scenario/` and the DateTime library test). Tests deploy factories and use stubs or live mainnet contracts from the fork.                              | mainnet fork |
| Unit Tests - DateTime Library  | `tests/test_bokky_poo_bahs_date-time-library.py`, run as a separate job                                                                                                                                                     | mainnet fork |
| Integration & Scenario Tests   | `tests/integration/` loads factories from deployment artifacts or deploys them locally. `tests/scenario/` deploys fresh factories and runs full motions against the real mainnet Easy Track, with stubs or live targets.    | mainnet fork |
| Foundry Scenario Tests (Hoodi) | `test/foundry/scenario/`. Each test drives a factory that is already deployed and registered through a full motion: create, wait, enact, then check the effect on-chain. Addresses come from `deployed-{sr,sm}-hoodi.json`. | testnet fork |

The Foundry scenario tests cover registered staking-router and staking-module factories. Each test reads a fixed artifact key. Add a deployment scenario once registration and executor role grants are complete; until then, use a Brownie scenario for motion lifecycle coverage. Foundry tests skip without an RPC URL or an active fork; a skipped run does not establish coverage.

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

PRs from forks do not get the repository secrets, so the Brownie jobs fail and the Foundry tests are skipped. For a fork PR, a maintainer pushes its branch to this repository and opens a PR from it, which runs CI with the secrets.

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
- shared test code: `utils/*.py`, `tests/conftest.py`, `tests/integration/conftest.py`, `tests/scenario/conftest.py`, `test/foundry/helpers/`, `test/foundry/interfaces/`

Additions (a new fixture, a new network entry) are fine. Changes to the behaviour or signature of existing code can break deployed contracts or other tests without a visible failure.

**Check:** the PR changes no existing code in these files. If it has to, the PR description explains why and lists the affected contracts and tests.

### R6. No out-of-scope changes

The PR changes only what its title and description say. Typical out-of-scope changes: edits to factories the PR does not name, dependency files (`package.json`, `pyproject.toml`, lock files, `brownie-config.yaml`), CI (`.github/`), mainnet artifacts outside a PR that records a mainnet deployment of audited code (such a PR into `develop` also meets R7 and R8), and unrelated refactoring or formatting.

**Check:** every changed file is needed for the stated change. If a file differs only because the target branch has moved on, rebase the PR. That is not an out-of-scope change.

### R7. Mainnet deployment, with addresses in the PR (`master` only)

The same as R2, on mainnet: entries in `deployed-sm-mainnet.json`, `deployed-sr-mainnet.json` or `deployed-mainnet.json`.

**Check:** each new contract has a mainnet entry with all four fields, and its `constructorArgs` match the deploy script (R4) for mainnet.

### R8. Audit (`master` only)

New and changed contracts are audited. The PR description links to each audit report in the [lidofinance/audits](https://github.com/lidofinance/audits) repository, for example `MixBytes Easy Track for Deposit Reserve Target management Audit Report 09-2026.pdf`. Links to reports hosted anywhere else do not count; add the report to that repository first.

**Check:**

- every new or changed contract is covered by a linked report under `https://github.com/lidofinance/audits/`;
- the contract code being merged is the code that was audited; later changes to tests, scripts or artifacts do not need a new audit;
- the bytecode deployed on mainnet matches the audited source, shown in the PR (for example with a diffyscan report, [bytecode-verificator](bytecode-verificator/bytecode_verificator.sh) or [compare_bytecode.py](scripts/compare_bytecode.py)).

## Checklist

Into `develop`:

- [ ] R1: test plan linked in the PR description, and every item has a test
- [ ] R2: deployed on testnet, entries added to the artifact files from the R2 table
- [ ] R3: all CI checks green
- [ ] R4: deploy script present, and its arguments match the constructor and the recorded `constructorArgs`
- [ ] R5: no existing code in shared modules changed, or the change is justified
- [ ] R6: no files outside the PR scope

Into `master`, also:

- [ ] R7: deployed on mainnet, entries added to the artifact files from the R7 list
- [ ] R8: audit report in `lidofinance/audits` linked in the PR description, the audited contract code matches the merged code, and the mainnet bytecode matches the audited source
