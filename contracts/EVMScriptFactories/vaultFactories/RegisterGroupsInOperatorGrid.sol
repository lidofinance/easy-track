// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../TrustedCaller.sol";
import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/IOperatorGrid.sol";
import "../../interfaces/ILido.sol";
import "../../interfaces/ILidoLocator.sol";
import "../../interfaces/IVaultHub.sol";

/// @author dry914
/// @notice Creates EVMScript to register a group and its tiers in OperatorGrid
contract RegisterGroupsInOperatorGrid is TrustedCaller, IEVMScriptFactory {

    // -------------
    // VARIABLES
    // -------------

    /// @notice Address of OperatorGrid
    IOperatorGrid public immutable operatorGrid;

    // -------------
    // CONSTANTS
    // -------------

    uint256 internal constant TOTAL_BASIS_POINTS = 10000;
    uint256 internal constant MAX_FEE_BP = type(uint16).max;

    uint256 internal immutable MAX_RELATIVE_SHARE_LIMIT_BP;
    ILido internal immutable LIDO;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _operatorGrid)
        TrustedCaller(_trustedCaller)
    {   
        require(_operatorGrid != address(0), "Zero operator grid");

        operatorGrid = IOperatorGrid(_operatorGrid);

        ILidoLocator locator = ILidoLocator(IOperatorGrid(_operatorGrid).LIDO_LOCATOR());
        LIDO = ILido(locator.lido());
        IVaultHub vaultHub = IVaultHub(locator.vaultHub());
        MAX_RELATIVE_SHARE_LIMIT_BP = vaultHub.MAX_RELATIVE_SHARE_LIMIT_BP();
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript to register multiple groups and their tiers in OperatorGrid
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded: (address[] _nodeOperators, uint256[] _shareLimits, IOperatorGrid.TierParams[][] _tiers)
    function createEVMScript(address _creator, bytes calldata _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (
            address[] memory _nodeOperators,
            uint256[] memory _shareLimits,
            IOperatorGrid.TierParams[][] memory _tiers
        ) = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(_nodeOperators, _shareLimits, _tiers);
        
        // Each group requires 2 calls (registerGroup and registerTiers)
        uint256 totalCalls = _nodeOperators.length * 2;
        address toAddress = address(operatorGrid);
        bytes4[] memory methodIds = new bytes4[](totalCalls);
        bytes[] memory calldataArray = new bytes[](totalCalls);

        for (uint256 i = 0; i < _nodeOperators.length; i++) {
            // Register group
            methodIds[i * 2] = IOperatorGrid.registerGroup.selector;
            calldataArray[i * 2] = abi.encode(_nodeOperators[i], _shareLimits[i]);

            // Register tiers
            methodIds[i * 2 + 1] = IOperatorGrid.registerTiers.selector;
            calldataArray[i * 2 + 1] = abi.encode(_nodeOperators[i], _tiers[i]);
        }

        return EVMScriptCreator.createEVMScript(toAddress, methodIds, calldataArray);
    }

    /// @notice Decodes call data used by createEVMScript method
    /// @param _evmScriptCallData Encoded: (address[] _nodeOperators, uint256[] _shareLimits, IOperatorGrid.TierParams[][] _tiers)
    /// @return NodeOperator addresses, group share limits and arrays of tier parameters
    function decodeEVMScriptCallData(bytes calldata _evmScriptCallData)
        external
        pure
        returns (address[] memory, uint256[] memory, IOperatorGrid.TierParams[][] memory)
    {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        private
        pure
        returns (address[] memory, uint256[] memory, IOperatorGrid.TierParams[][] memory)
    {
        return abi.decode(_evmScriptCallData, (address[], uint256[], IOperatorGrid.TierParams[][]));
    }

    function _validateInputData(
        address[] memory _nodeOperators,
        uint256[] memory _shareLimits,
        IOperatorGrid.TierParams[][] memory _tiers
    ) private view {
        require(_nodeOperators.length > 0, "Empty node operators array");
        require(
            _nodeOperators.length == _shareLimits.length &&
            _nodeOperators.length == _tiers.length,
            "Array length mismatch"
        );

        uint256 _maxSaneShareLimit = (LIDO.getTotalShares() * MAX_RELATIVE_SHARE_LIMIT_BP) / TOTAL_BASIS_POINTS;
        for (uint256 i = 0; i < _nodeOperators.length; i++) {
            require(_nodeOperators[i] != address(0), "Zero node operator");
            require(_tiers[i].length > 0, "Empty tiers array");

            IOperatorGrid.Group memory group = operatorGrid.group(_nodeOperators[i]);
            require(group.operator == address(0), "Group exists");

            require(_shareLimits[i] <= _maxSaneShareLimit, "Group share limit too high");

            // Validate tier parameters
            for (uint256 j = 0; j < _tiers[i].length; j++) {
                require(_tiers[i][j].shareLimit <= _shareLimits[i], "Tier share limit too high");

                require(_tiers[i][j].reserveRatioBP != 0, "Zero reserve ratio");
                require(_tiers[i][j].reserveRatioBP <= TOTAL_BASIS_POINTS, "Reserve ratio too high");

                require(_tiers[i][j].forcedRebalanceThresholdBP != 0, "Zero forced rebalance threshold");
                require(_tiers[i][j].forcedRebalanceThresholdBP <= _tiers[i][j].reserveRatioBP, "Forced rebalance threshold too high");

                require(_tiers[i][j].infraFeeBP <= MAX_FEE_BP, "Infra fee too high");
                require(_tiers[i][j].liquidityFeeBP <= MAX_FEE_BP, "Liquidity fee too high");
                require(_tiers[i][j].reservationFeeBP <= MAX_FEE_BP, "Reservation fee too high");
            }
        }
    }
}
