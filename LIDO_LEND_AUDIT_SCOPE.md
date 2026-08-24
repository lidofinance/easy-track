# Lido Lend — EasyTrack Factories Audit Scope

> [!note]
> Interim scope based on the current code. nSLOC is measured with `cloc` 2.08 and excludes blank and
> comment lines; counts may change before the audit starts.

## Product Description

The contracts provide an optimistic-governance layer for routine Lido Lend market operations. A trusted
committee creates an EasyTrack motion through an `IEVMScriptFactory`; unless the LDO objection threshold is
reached, the resulting EVMScript is enacted against the deployed protocol.

The factories activate markets, configure per-market policy and IRMs, manage guardians and risk stewards,
register pausers, and maintain exit-book allow lists. They validate requests when a motion is created, keep
fixed protocol addresses as immutables, and support batch execution only for naturally batchable operations.

## Audit Scope and Size

Single code base: `easy-track` (Brownie, Solidity 0.8.6, optimizer enabled with 200 runs, Berlin EVM).

### Factories

All factory contracts are under `contracts/EVMScriptFactories/lidoLendFactories/`.

| Contract | nSLOC | Role |
| --- | ---: | --- |
| `LidoLendActivateMarket` | 120 | Builds the ordered five-call market activation: configure and route the IRM, create the market, appoint a steward, and register a pauser. |
| `LidoLendRegisterPauser` | 57 | Registers or replaces a market pauser after resolving its controller and checking the CircuitBreaker role. |
| `LidoLendSetMorphoExitBookAllowed` | 48 | Batch-enables or disables markets on the Morpho exit book. |
| `LidoLendSetErc4626ExitBookAllowed` | 48 | Batch-enables or disables vaults on the ERC-4626 exit book. |
| `LidoLendAddGuardian` | 64 | Atomically adds a guardian and sets the resulting quorum. |
| `LidoLendRemoveGuardian` | 62 | Atomically updates quorum and removes a guardian. |
| `LidoLendReplaceGuardian` | 60 | Replaces an existing guardian without changing quorum. |
| `LidoLendSetGuardiansQuorum` | 48 | Updates guardian quorum within the current registry bounds. |
| `LidoLendSetSuspectWindow` | 48 | Updates the GuardianSignals suspect window within its protocol limit. |
| `LidoLendUnbanAccount` | 53 | Batch-unbans paired accounts across one or more markets. |
| `LidoLendSetCollateralActivationConfig` | 93 | Updates collateral-activation policy and validates its timing and amount bounds. |
| `LidoLendSetSettlementConfig` | 59 | Updates settlement policy and validates its basis-point fields. |
| `LidoLendSetSupplyCap` | 41 | Sets the supply cap of an existing market. |
| `LidoLendSetInstantActivation` | 58 | Enables or disables instant collateral activation for one caller. |
| `LidoLendUnfreezeMarket` | 48 | Batch-unfreezes markets that are frozen when the motion is created. |
| `LidoLendSetIrmConfig` | 55 | Applies a per-market configuration to the shared AdaptiveCurveIrm. |
| `LidoLendSetMarketIrm` | 56 | Routes a market to a non-zero IRM contract through the shared router. |
| `LidoLendAddRiskSteward` | 50 | Assigns a steward to an existing market through the RiskStewardDashboard. |
| `LidoLendRemoveRiskSteward` | 48 | Removes an existing market-steward assignment. |
| **Factory subtotal (19 contracts)** | **1,116** | |

### Supporting Scope

| Contract | nSLOC | Role |
| --- | ---: | --- |
| `LidoLendOwnerFactoryBase` | 22 | Shared trusted-caller, owner-facade, controller, and GuardianSignals resolution. |
| `ILidoLend.sol` | 123 | Protocol structs and interfaces used for validation, selectors, and calldata encoding. |
| **Supporting subtotal (2 files)** | **145** | |
| **Total scope (21 files)** | **1,261** | |

## Critical Audit Focus Areas

- correctness and ordering of EVMScript targets, selectors, and calldata;
- validation at motion creation and state changes before enactment;
- market/controller resolution and protocol-role assumptions;
- atomicity of multi-call activation and guardian operations;
- array validation, per-entry checks, and gas bounds for batched motions;
- consistency between immutable deployment parameters and the target Lido Lend domain.
