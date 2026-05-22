// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./BaseModuleStub.sol";

/// @notice Test stub for CuratedModule (implements ICuratedModule).
contract CuratedModuleStub is BaseModuleStub {
    address internal _metaRegistry;

    function META_REGISTRY() external view returns (address) {
        return _metaRegistry;
    }

    function mock_setMetaRegistry(address metaRegistry_) external {
        _metaRegistry = metaRegistry_;
    }
}
