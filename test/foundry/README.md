# Foundry tests

Two suites, each on its own profile in `foundry.toml`:

| Suite | Profile | Compiles | Network |
|---|---|---|---|
| `unit/` | `default` | `contracts/` and the tests at solc 0.8.6, so tests deploy the real contracts and stubs with `new` | none |
| `scenario/` | `scenario` | only `test/foundry`, with its own modern-pragma interfaces | a fork of hoodi or mainnet |

Plain `forge test` runs the default profile, the unit suite. The scenario suite needs its profile and the contracts built, and reports every forking scenario contract as skipped when no RPC URL is set:

```bash
npm test                           # forge test
CHAIN=hoodi npm run test:scenario  # forge build && FOUNDRY_PROFILE=scenario forge test
```

`npm install` brings forge-std as a normal npm dependency, there is no submodule.

## Unit suite

Local tests of the contracts under `contracts/`, ported from the Brownie suite in `tests/` with one Foundry test per Python test. They cover the Easy Track core and its libraries, the limits checker and the allowed recipients registry with its factories, the payouts builders with the allowed tokens registry and the single-token top-up factory, the reward programs registry with its factories, and the node operator, exit request hash, MEV-Boost relay, operator grid, vault hub and staking module factories. Every test deploys what it needs with `new` and runs without a network. Stubs the tests share live in `unit/stubs/`, encoders and constants in `unit/helpers/`. The date-time test checks the stub in `unit/stubs/` against `unit/helpers/Calendar.sol`, where the Python runs against the mainnet deployment.

```bash
npm test
forge test --match-contract EasyTrackTest   # one contract
```

## Scenario suite

Happy-path scenario tests for the **deployed** Easy Track EVM-script factories listed in `deployed-<chain>.json`, main below, and `deployed-{sr,sm}-<chain>.json`. Each test forks a live network and drives one factory through the full motion lifecycle against the real on-chain contracts:

```
build the on-chain data the motion needs
createMotion (trustedCaller) → warp motionDuration → enactMotion → assert the on-chain effect
```

The suite prepares only **data**: operators, penalties, slashings, groups. A deployed factory runs as the DAO registered it. Its registration, the executor's protocol roles and the versions of the contracts it targets are real on-chain state, and a test fails where that state is missing. The exceptions act as a DAO vote would, through Voting or a permission's manager, and the Notes list each one. A test that deploys a fresh factory or a fresh Easy Track registers and permissions what it deploys. The exit request and MEV-Boost suites register the deployed factory where the fork lacks the registration. The gate permission tests re-register `SetMerkleGateTree` with a stub gate. The payouts suites regrant the executor `CREATE_PAYMENTS_ROLE` on Finance.

Six files under `aragon/` drive the DAO apps instead of a deployed factory: the ACL's parameterized permissions, the reward programs, LEGO program and staking limit factories over a fresh Easy Track, the deploy script's wiring and the executor permission votes. Four files under `payouts/` drive the allowed recipients registries and factories, the motions files once per instance of `integration-test-addresses-<chain>.yaml`, whatever the file does not list deployed fresh through the builders and registered in Easy Track, and a fifth checks the reader of that file over inline text, without a fork. `vebo/` and `mevboost/` drive the deployed exit request hash and MEV-Boost relay factories, `vaults/` the operator grid and vault hub factories deployed fresh with their own Easy Track and `VaultsAdapter`, `lido/` the deployed `SetDepositsReserveTarget` and a fresh one. The suite is independent of the Brownie suite and has no Python.

### Running

`forge` and `just` auto-load `.env`, which holds `HOODI_RPC_URL` and `MAINNET_RPC_URL`. `CHAIN`, default `hoodi`, selects the network and the `deployed-*.json` files. `RPC_URL` is not consulted. Some tests deploy a stub gate, a second factory, a whole Easy Track, the payouts builders or the vaults adapter and factories from the artifacts `forge build` writes to `out/`, which the npm script and the just recipe build first. Without them the tests fail naming the command.

```bash
CHAIN=hoodi   npm run test:scenario
CHAIN=mainnet npm run test:scenario
CHAIN=hoodi   FOUNDRY_PROFILE=scenario forge test --mc SettleGeneralDelayedPenalty -vvv   # one factory
```

A root [`justfile`](../../justfile) runs the unit suite with `just test`, the scenario suite after a build, and formats the tests with `just fmt`:

```bash
RPC_URL=$MAINNET_RPC_URL just make-fork                             # start a local Anvil fork (reused if up)
CHAIN=mainnet just test-scenario --fork-url http://127.0.0.1:8545  # run against it (fast, cached)
just test-scenario                                                 # or self-fork <CHAIN>_RPC_URL
```

If the Easy Track contract is already present in the running EVM, as with `--fork-url`, the suite reuses that fork instead of re-forking. With no RPC and no active fork every scenario contract is reported as `[SKIP] setUp()` with the name of the variable it looked for. Forge keeps every state change in memory, so a reused Anvil fork is left untouched.

### Coverage

Every factory of the `sr` and `sm` artifacts is covered, plus the SimpleDVT, MEV-Boost relay and exit request hash factories and `SetDepositsReserveTarget` of the main one, the Aragon ACL, the reward programs, LEGO program and staking limit factories, the allowed recipients payouts, the vaults factories and the deploy and permission scripts. Preconditions are **constructed** on the fork through module admin roles. Nothing scans for pre-existing state.

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
| `AddAllowedRecipient`, `RemoveAllowedRecipient`, `TopUpAllowedRecipients` of every `multi_token` instance of `integration-test-addresses-<chain>.yaml`, the missing ones deployed fresh through `AllowedRecipientsBuilder` | `payouts/AllowedRecipientsMotionsMultiToken.t.sol` | add and remove recipients by motion. Pay DAI and USDC within the period limit, carry a motion over the period rollover, renew the limit in the next period of a changed grid. Reject a motion past the limit, or one that meets a token or recipient removal, or a limit decrease, in flight |
| the same, through `deploySingleRecipientTopUpOnlySetup` and `deployFullSetup` of the listed builder | `payouts/AllowedRecipientsHappyPathMultiToken.t.sol` | a top-up-only registry of one recipient and a full setup end to end, the Agent managing recipients and tokens, the executor refused |
| `AddAllowedRecipient`, `RemoveAllowedRecipient`, `TopUpAllowedRecipientsSingleToken` of every `single_token` instance, the missing ones deployed fresh through `AllowedRecipientsBuilderSingleToken` | `payouts/AllowedRecipientsMotionsSingleToken.t.sol` | the same paying the instance's stETH or LDO, without the token cases |
| the same, through `deploySingleRecipientTopUpOnlySetup` and `deployFullSetup` of the listed builder | `payouts/AllowedRecipientsHappyPathSingleToken.t.sol` | the same paying LDO |
| none, the reader of `integration-test-addresses-<chain>.yaml` | `payouts/IntegrationTestAddresses.t.sol` | read a suite's contracts and instances past the other suite, `"local"` and an omitted contract as fresh, a missing file or a suite without instances as one `default` instance. No fork |
| `SetDepositsReserveTarget`, deployed fresh over the live Lido (chains with a v3 Lido) | `lido/SetDepositsReserveTargetFreshFactory.t.sol` | set the target to the factory's maximum, then to zero. Reject a motion of a second factory whose permissions name the Agent instead of Lido |
| `CuratedSubmitExitRequestHashes` (main, mainnet, else deployed fresh) | `vebo/CuratedSubmitExitRequestHashes.t.sol` | the reward address of the first operator with enough deposited keys requests one exit, then 200 in one motion, and delivers each batch to the oracle. Reject a key the operator has not deposited |
| `SDVTSubmitExitRequestHashes` (main) | `vebo/SDVTSubmitExitRequestHashes.t.sol` | the same from the trusted committee, 60 requests in the batch. The rejection runs through a fresh factory, the Hoodi deployment predates the check |
| `AddMEVBoostRelays`, `RemoveMEVBoostRelays`, `EditMEVBoostRelays` (main) | `mevboost/MEVBoostRelaysAllowedList.t.sol` | add one relay then three, fill the list to 40 in one motion, remove one then three, empty the full list in one motion, edit relays in place |
| `TopUpLegoProgram`, deployed fresh with its own Easy Track | `aragon/LegoProgramEasyTrack.t.sol` | one motion pays the LEGO program LDO, stETH and ETH from the Agent through Finance |
| `IncreaseNodeOperatorStakingLimit`, deployed fresh with its own Easy Track | `aragon/NodeOperatorsEasyTrack.t.sol` | two DAO votes let the executor set limits and the Agent add a curated operator, which adds three keys and raises its limit to three by a motion |
| the five factories of `scripts/deploy.py`, deployed fresh with their own Easy Track | `aragon/DeployScript.t.sol` | the deploy script's wiring read back: settings, roles on Voting, executor, factory getters, registry roles, factory permissions |
| none, the executor permission scripts | `aragon/ExecutorPermissions.t.sol` | a vote grants a fresh executor `CREATE_PAYMENTS_ROLE` and `SET_NODE_OPERATOR_LIMIT_ROLE`, a second revokes them and leaves it none of the DAO apps' permissions |
| `RegisterGroupsInOperatorGrid`, `UpdateGroupsShareLimitInOperatorGrid`, `RegisterTiersInOperatorGrid`, `AlterTiersInOperatorGrid`, `SetJailStatusInOperatorGrid`, `UpdateVaultsFeesInOperatorGrid`, deployed fresh with their own Easy Track and `VaultsAdapter` (chains with vaults) | `vaults/OperatorGrid.t.sol` | register two groups with their tiers, halve their share limits, append tiers, overwrite tiers, jail a vault, set a vault's fees after a fresh report |
| `ForceValidatorExitsInVaultHub`, `SetLiabilitySharesTargetInVaultHub`, `SocializeBadDebtInVaultHub`, the same | `vaults/VaultHub.t.sol` | force the exit of an unhealthy vault's validators, set the redemption shares of two minted vaults, move bad debt between two vaults of one operator |

### Notes

- **Deployed factories run as registered.** The suite upgrades nothing and leaves the executor's protocol roles as they are on-chain, else the test fails. Role grants build the data preconditions above.
- **Registration and permissions a vote would grant.** The gate permission tests re-register `SetMerkleGateTree` with a stub gate and the missing module test registers a second `UpdateStakingModuleShareLimits`, both deployed from the `forge build` artifacts. The exit request and MEV-Boost suites bind the deployed factories and register them as Voting only when the fork lacks the registration, the SimpleDVT exit request suite also a fresh factory for the undeposited key. The fresh `SetDepositsReserveTarget` grants the executor `BUFFER_RESERVE_MANAGER_ROLE` on Lido when it lacks it.
- **Fresh Easy Tracks.** The reward programs, LEGO program, staking limit, vaults and script suites deploy their own Easy Track, the vaults suites with Voting as admin and the deploy script suite with the script's settings, so do the payouts suites on a chain without the addresses file. The reward programs and LEGO program suites grant their fresh executor `CREATE_PAYMENTS_ROLE` on Finance as the permission manager. The staking limit suite grants it `SET_NODE_OPERATOR_LIMIT_ROLE` on the curated registry and grants the Agent `MANAGE_NODE_OPERATOR_ROLE` to add the operator.
- **Payouts suites.** They bind the Easy Track, builder, registries and factories `integration-test-addresses-<chain>.yaml` lists, deploy what it does not, register fresh factories as Voting and regrant the executor `CREATE_PAYMENTS_ROLE` on Finance without parameters, as the Brownie fixtures do. The Agent is their registries' admin and pays through Finance, so it must hold the DAI, USDC or LDO the top-ups move, and the LDO the LEGO program motion pays. A single-token suite paying stETH stakes the Agent's ETH when it runs short.
- **Skips.** The two SimpleDVT suites driving `IncreaseVettedValidatorsLimit` skip where it is deployed but not registered, as on mainnet. The vaults suites skip a chain without the vaults contracts, the deployed `SetDepositsReserveTarget` a chain whose artifact lacks it and the fresh one a Lido without a deposits reserve target.
- **Interfaces** in `interfaces/{External,Factories,EasyTrack,Payouts,Vaults}.sol` are self-contained with a modern pragma, so the suite never compiles `contracts/`. Build the factories first with `forge build`.
- **Gate discovery.** The gate of `SetMerkleGateTree` is the module's `CREATE_NODE_OPERATOR_ROLE` holder the executor may set the tree on. The staking-module addresses live in `NetworkConfig`. Every other target comes from the factory getters at runtime.
- **Commit re-validation.** Factories that commit a current value at creation, the share limits, the gate tree, the operator group and the lock nonce, re-check it at enactment. Each has a test that mutates that value after `createMotion` and asserts `enactMotion` then reverts.
- **DAO votes** in the SimpleDVT scenarios are replayed through the executor: Voting points it at the Agent with `setEasyTrack`, the Agent runs the script, Voting points it back. A vote that only grants an Aragon permission is replayed as that grant from the permission's manager. The payouts vote is replayed as the Agent's call, the vote adding a curated operator as the Agent's call after its grant, and the MEV-Boost vote as the list owner's `set_manager`. The permission scripts' votes are replayed as Voting's ACL calls once the setup vote made it the registry role's manager. Aragon Voting and the dual governance timelock are not driven.
- **Calendar periods** of the payouts registries are computed through the deployed date-time contract they use, so the suites warp to period boundaries, never by a duration.
