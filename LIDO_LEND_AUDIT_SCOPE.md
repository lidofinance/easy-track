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
| `LidoLendActivateMarket` | 170 | Configures and routes the IRM, creates the market, appoints a steward, registers a pauser, and optionally sets the initial fee. |
| `LidoLendRegisterPauser` | 55 | Registers or replaces a market pauser after resolving its controller and checking the CircuitBreaker role. |
| `LidoLendGuardianActions` | 254 | Adds, removes, and replaces guardians; updates quorum and suspect window; batch-unbans accounts. |
| `LidoLendMarketManagerActions` | 272 | Configures activation and settlement, updates supply caps and fees, and batch-unfreezes markets. |
| `LidoLendRiskStewardActions` | 87 | Adds and removes market stewards through the RiskStewardDashboard. |
| `LidoLendIrmActions` | 100 | Applies market IRM configs and routes markets through the shared IrmRouter. |
| `LidoLendExitBookActions` | 150 | Updates Morpho and ERC-4626 exit-book allow lists and service fees. |
| **Factory subtotal (7 contracts)** | **1,088** | |

### Supporting Scope

| Contract | nSLOC | Role |
| --- | ---: | --- |
| `LidoLendOwnerFactoryBase` | 22 | Shared trusted-caller, owner-facade, controller, and GuardianSignals resolution. |
| `ILidoLend.sol` | 128 | Protocol structs and interfaces used for validation, selectors, and calldata encoding. |
| **Supporting subtotal (2 files)** | **150** | |
| **Total scope (9 files)** | **1,238** | |

## Critical Audit Focus Areas

- correctness and ordering of EVMScript targets, selectors, and calldata;
- validation at motion creation and state changes before enactment;
- market/controller resolution and protocol-role assumptions;
- atomicity of multi-call activation and guardian operations;
- array validation, per-entry checks, and gas bounds for batched motions;
- consistency between immutable deployment parameters and the target Lido Lend domain.
