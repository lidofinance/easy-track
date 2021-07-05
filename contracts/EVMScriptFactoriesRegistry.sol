// SPDX-FileCopyrightText: 2021 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.4;

import "./interfaces/IEVMScriptFactory.sol";
import "./libraries/EVMScriptPermissions.sol";
import "./EasyTrackStorage.sol";

contract EVMScriptFactoriesRegistry is EasyTrackStorage {
    using EVMScriptPermissions for bytes;

    event EVMScriptFactoryAdded(address indexed _evmScriptFactory, bytes _permissions);
    event EVMScriptFactoryRemoved(address indexed _evmScriptFactory);

    function addEVMScriptFactory(address _evmScriptFactory, bytes memory _permissions)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        require(_permissions.isValidPermissions(), "INVALID_PERMISSIONS");
        require(!_isEVMScriptFactory(_evmScriptFactory), "EVM_SCRIPT_FACTORY_ALREADY_ADDED");
        evmScriptFactories.push(_evmScriptFactory);
        evmScriptFactoryIndices[_evmScriptFactory] = evmScriptFactories.length;
        evmScriptFactoryPermissions[_evmScriptFactory] = _permissions;
        emit EVMScriptFactoryAdded(_evmScriptFactory, _permissions);
    }

    function removeEVMScriptFactory(address _evmScriptFactory)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        uint256 index = _getEVMScriptFactoryIndex(_evmScriptFactory);
        uint256 lastIndex = evmScriptFactories.length - 1;

        if (index != lastIndex) {
            address lastEVMScriptFactory = evmScriptFactories[lastIndex];
            evmScriptFactories[index] = lastEVMScriptFactory;
            evmScriptFactoryIndices[lastEVMScriptFactory] = index + 1;
        }

        evmScriptFactories.pop();
        delete evmScriptFactoryIndices[_evmScriptFactory];
        delete evmScriptFactoryPermissions[_evmScriptFactory];
        emit EVMScriptFactoryRemoved(_evmScriptFactory);
    }

    function getEVMScriptFactories() external view returns (address[] memory) {
        return evmScriptFactories;
    }

    function isEVMScriptFactory(address _maybeEVMScriptFactory) external view returns (bool) {
        return _isEVMScriptFactory(_maybeEVMScriptFactory);
    }

    function _createEVMScript(
        address _evmScriptFactory,
        address _creator,
        bytes memory _evmScriptCallData
    ) internal returns (bytes memory _evmScript) {
        require(_isEVMScriptFactory(_evmScriptFactory), "EVM_SCRIPT_FACTORY_NOT_FOUND");
        _evmScript = IEVMScriptFactory(_evmScriptFactory).createEVMScript(
            _creator,
            _evmScriptCallData
        );
        bytes memory permissions = evmScriptFactoryPermissions[_evmScriptFactory];
        require(permissions.canExecuteEVMScript(_evmScript), "HAS_NO_PERMISSIONS");
    }

    function _getEVMScriptFactoryIndex(address _evmScriptFactory)
        private
        view
        returns (uint256 _index)
    {
        _index = evmScriptFactoryIndices[_evmScriptFactory];
        require(_index > 0, "EVM_SCRIPT_FACTORY_NOT_FOUND");
        _index -= 1;
    }

    function _isEVMScriptFactory(address _maybeEVMScriptFactory) private view returns (bool) {
        return evmScriptFactoryIndices[_maybeEVMScriptFactory] > 0;
    }
}
