// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

/// @author (draft)
/// @notice Test-only stub of the MorphoExitBook, covering only `setMarketAllowed` — the method
/// `LidoLendActivateMarket` targets. Never called during EVMScript creation; used only so tests can
/// reproduce the exact selector and ABI encoding brownie would produce for the real call.
contract MorphoExitBookStub {
    bytes32 public constant ALLOWLIST_MANAGER_ROLE = keccak256("ALLOWLIST_MANAGER_ROLE");

    struct MarketParams {
        address loanToken;
        address collateralToken;
        address oracle;
        address irm;
        uint256 lltv;
    }

    MarketParams public lastMarketParams;
    bool public lastAllowed;
    mapping(bytes32 => address) public marketIdToVault;
    mapping(bytes32 => bool) public isMarketAllowed;
    mapping(bytes32 => mapping(address => bool)) public hasRole;
    bool public enforceRoles;

    function grantRole(bytes32 role, address account) external {
        hasRole[role][account] = true;
    }

    function setEnforceRoles(bool enforce) external {
        enforceRoles = enforce;
    }

    function setMarketVault(bytes32 marketId, address vault) external {
        marketIdToVault[marketId] = vault;
    }

    function setMarketAllowed(MarketParams calldata marketParams, bool allowed) external {
        require(
            !enforceRoles || hasRole[ALLOWLIST_MANAGER_ROLE][msg.sender],
            "MISSING_ALLOWLIST_MANAGER_ROLE"
        );
        lastMarketParams = marketParams;
        lastAllowed = allowed;
        isMarketAllowed[keccak256(abi.encode(marketParams))] = allowed;
    }
}
