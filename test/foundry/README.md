# Foundry tests

Two suites, each on its own profile in `foundry.toml`:

| Suite | Profile | Compiles | Network |
|---|---|---|---|
| `unit/` | `unit` | `contracts/` and the tests at solc 0.8.6, so tests deploy the real contracts and stubs with `new` | none |
| `scenario/` | `default` | only `test/foundry`, with its own modern-pragma interfaces | a fork of hoodi or mainnet |

Plain `forge test` runs the default profile, so it runs the scenario suite only, and reports every
scenario contract as skipped when no RPC URL is set. The unit suite needs its profile:

```bash
npm run test:unit                  # FOUNDRY_PROFILE=unit forge test
CHAIN=hoodi npm run test:scenario  # forge test --match-path 'test/foundry/scenario/**'
```

`npm install` brings forge-std as a normal npm dependency, there is no submodule.

## Unit suite

Local tests of the Easy Track core, the libraries, the limits checker, the allowed recipients
registry with its add and remove factories, the payouts builders with the allowed tokens registry
and the single-token top-up factory, the reward programs registry with its factories, the node
operator factories, the exit request hash factories, the MEV-Boost relay factories, the operator
grid factories, the vault hub factories and the staking module factories, ported from the Brownie
suite in `tests/`, one Foundry test per Python test. Every test deploys what it needs with `new`
and runs without a network. Stubs the tests share live in `unit/stubs/`, encoders and constants in
`unit/helpers/`.

```bash
npm run test:unit
FOUNDRY_PROFILE=unit forge test --match-contract EasyTrackTest   # one contract
```

## Scenario suite

Happy-path scenario tests for the **deployed** Easy Track EVM-script factories listed in
`deployed-<chain>.json`, main below, and `deployed-{sr,sm}-<chain>.json`. Each test forks a live
network and drives one factory through the full motion lifecycle against the real on-chain contracts:

```
build the on-chain data the motion needs
createMotion (trustedCaller) → warp motionDuration → enactMotion → assert the on-chain effect
```

The suite prepares only **data**: operators, penalties, slashings, groups. Everything else must
already hold on-chain: the factory registered in Easy Track with permissions, the executor holding
the roles the motion calls, and the contracts the factory targets at the expected version. If any of
that is missing, the test **fails**. It is never auto-arranged. Two files under `aragon/` drive the
DAO apps instead of a deployed factory: the ACL's parameterized permissions, and the reward programs
factories over a fresh Easy Track. The suite is independent of the Brownie suite and has no Python.

### Running

`forge` / `just` auto-load `.env`, which holds `HOODI_RPC_URL` / `MAINNET_RPC_URL`. `CHAIN`,
default `hoodi`, selects the network and the `deployed-*.json` files. `RPC_URL` is not consulted.
Some tests deploy a stub gate, a second factory or a whole Easy Track from the `contracts` profile
artifacts, so build that profile first with `FOUNDRY_PROFILE=contracts forge build`. Without `out/`
they fail naming the command.

```bash
CHAIN=hoodi   npm run test:scenario
CHAIN=mainnet npm run test:scenario
CHAIN=hoodi   forge test --mc SettleGeneralDelayedPenalty -vvv   # one factory
```

A root [`justfile`](../../justfile) has two recipes:

```bash
RPC_URL=$MAINNET_RPC_URL just make-fork                             # start a local Anvil fork (reused if up)
CHAIN=mainnet just test-scenario --fork-url http://127.0.0.1:8545  # run against it (fast, cached)
just test-scenario                                                 # or self-fork <CHAIN>_RPC_URL
```

If the Easy Track contract is already present in the running EVM, as with `--fork-url`, the suite
reuses that fork instead of re-forking. With no RPC and no active fork every scenario contract is
reported as `[SKIP] setUp()` with the name of the variable it looked for. Forge keeps every state
change in memory, so a reused Anvil fork is left untouched.

### Coverage

Every factory of the `sr` and `sm` artifacts is covered, plus the SimpleDVT factories and
`SetDepositsReserveTarget` of the main one, the Aragon ACL and the reward programs factories.
Preconditions are **constructed** on the fork through module admin roles. Nothing scans for
pre-existing state.

| Factory (`deployed-*.json` key) | Test | Scenarios |
|---|---|---|
| `UpdateStakingModuleShareLimits:CSM` (sr) | `sr/UpdateStakingModuleShareLimits.t.sol` | increase / decrease the limits. Reject a stale committed current value, or a module id the router does not know, through a fresh factory |
| `AllowConsolidationPair` (sr) | `sr/AllowConsolidationPair.t.sol` | allow a source+target pair linked in one MetaRegistry group. Update its submitter |
| `SettleGeneralDelayedPenalty:CSM/CM` (sm) | `sm/SettleGeneralDelayedPenalty.t.sol` | settle one / multiple locked penalties. Reject nothing-to-settle, an already-settled lock or a stale nonce |
| `SetMerkleGateTree:CSM/CM` (sm) | `sm/SetMerkleGateTree.t.sol` | update a gate's tree, and the tree of a stub gate added to the permissions. Reject a stale committed current tree, an unchanged root or CID, the other module's gate outside the permissions, or a stub gate removed from them |
| `ReportWithdrawalsForSlashedValidators:CSM/CM` (sm) | `sm/ReportWithdrawalsForSlashedValidators.t.sol` | report one or two slashed validators withdrawn, and again as a no-op. Reject a zero penalty or zero exit balance |
| `CreateOrUpdateOperatorGroup:CM` (sm) | `sm/CreateOrUpdateOperatorGroup.t.sol` | create a group. Update it to non-empty / empty / empty→empty. Move a sub operator to a new or an existing group through two pending motions. Reject a stale committed group, or a claim on an operator still in another group |
| `SetDepositsReserveTarget` (main, hoodi only) | `lido/SetDepositsReserveTarget.t.sol` | raise the target. Reject an unchanged or too high target, or an untrusted creator |
| `AddNodeOperators`, `ActivateNodeOperators`, `DeactivateNodeOperators`, `SetNodeOperatorNames`, `SetNodeOperatorRewardAddresses`, `SetVettedValidatorsLimits`, `IncreaseVettedValidatorsLimit`, `UpdateTargetValidatorLimits`, `ChangeNodeOperatorManagers` (main) | `sdvt/SimpleDvtLifecycle.t.sol` | drive 36 new SimpleDVT operators through every factory, then a DAO vote hands the `MANAGE_SIGNING_KEYS` manager to the Agent |
| the same minus `UpdateTargetValidatorLimits` (main) | `sdvt/SimpleDvtCollisions.t.sol` | sixteen pairs of pending motions whose second enactment fails the factory's re-validation |
| `AddNodeOperators`, `ChangeNodeOperatorManagers` (main) | `sdvt/SimpleDvtSigningKeysRole.t.sol` | a DAO vote grants the Agent `MANAGE_SIGNING_KEYS`, the executor stays manager and still changes managers |
| none, the Aragon ACL itself | `aragon/AragonACL.t.sol` | create a plain permission. Grant, revoke and regrant a parameterized one. A regrant replaces the parameter list |
| `AddRewardProgram`, `TopUpRewardPrograms`, `RemoveRewardProgram`, deployed fresh with their own Easy Track | `aragon/RewardProgramsEasyTrack.t.sol` | add a reward program, top it up with 5 LDO from Finance, remove it |

### Notes

- **Deployed factories run as registered.** The suite grants the executor no roles and upgrades
  nothing. Those must already hold on-chain, else the test fails. Role grants build the data
  preconditions above. Four tests act as a DAO vote would: the gate permission tests re-register
  `SetMerkleGateTree` with a stub gate, the missing module test registers a second
  `UpdateStakingModuleShareLimits`, and the reward programs test grants its fresh executor
  `CREATE_PAYMENTS_ROLE` on Finance as the permission manager, all deployed from the `contracts`
  profile artifacts.
- **Interfaces** in `interfaces/{External,Factories,EasyTrack}.sol` are self-contained with a modern
  pragma, so the suite never compiles `contracts/`. Build the factories with the separate profile:
  `FOUNDRY_PROFILE=contracts forge build`.
- **Gate discovery.** The gate of `SetMerkleGateTree` is the module's `CREATE_NODE_OPERATOR_ROLE`
  holder the executor may set the tree on. The staking-module addresses live in `NetworkConfig`.
  Every other target comes from the factory getters at runtime.
- **Commit re-validation.** Factories that commit a current value at creation, the share limits, the
  gate tree, the operator group and the lock nonce, re-check it at enactment. Each has a test that
  mutates that value after `createMotion` and asserts `enactMotion` then reverts.
- **DAO votes** in the SimpleDVT scenarios are replayed through the executor: Voting points it at
  the Agent with `setEasyTrack`, the Agent runs the script, Voting points it back. A vote that only
  grants an Aragon permission is replayed as that grant from the permission's manager. Aragon
  Voting and the dual governance timelock are not driven.
