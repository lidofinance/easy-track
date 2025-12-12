// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../libraries/EVMScriptCreator.sol";
import "../interfaces/IEVMScriptFactory.sol";
import "../interfaces/INodeOperatorsRegistry.sol";
import "../interfaces/ICSModule.sol";
import "../interfaces/IConsolidationMigrator.sol";

/// @author vgorkavenko
/// @notice Creates EVMScript to allow consolidation between a curated node operator and a target module operator
contract AllowConsolidationPair is IEVMScriptFactory {
    struct AllowConsolidationPairInput {
        uint256 sourceOperatorId;
        uint256 targetOperatorId;
    }

    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_SOURCE_OPERATOR_ID_OUT_OF_RANGE = "SOURCE_OPERATOR_ID_OUT_OF_RANGE";
    string private constant ERROR_TARGET_OPERATOR_ID_OUT_OF_RANGE = "TARGET_OPERATOR_ID_OUT_OF_RANGE";
    string private constant ERROR_PAIR_ALREADY_ALLOWED = "PAIR_ALREADY_ALLOWED";
    string private constant ERROR_CALLER_IS_NOT_SOURCE_OPERATOR_OWNER =
        "CALLER_IS_NOT_SOURCE_OPERATOR_OWNER";
    string private constant ERROR_ZERO_MIGRATOR = "ZERO_MIGRATOR";

    // -------------
    // VARIABLES
    // -------------

    /// @notice Source module bound to the legacy NodeOperatorRegistry implementation.
    /// @dev The `sourceOperatorId` can reference only this module with the old NodeOperatorRegistry interface.
    INodeOperatorsRegistry public immutable sourceModule;
    /// @notice Target module the consolidation migrator points to.
    ICSModule public immutable targetModule;
    /// @notice Consolidation migrator contract that maintains the allowlist.
    IConsolidationMigrator public immutable consolidationMigrator;
    /// @notice Cached source module id that must equal the migrator binding.
    uint256 public immutable sourceModuleId;
    /// @notice Cached target module id that must equal the migrator binding.
    uint256 public immutable targetModuleId;

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _consolidationMigrator) {
        require(_consolidationMigrator != address(0), ERROR_ZERO_MIGRATOR);

        consolidationMigrator = IConsolidationMigrator(_consolidationMigrator);

        sourceModule = INodeOperatorsRegistry(consolidationMigrator.sourceModule());
        targetModule = ICSModule(consolidationMigrator.targetModule());
        sourceModuleId = consolidationMigrator.sourceModuleId();
        targetModuleId = consolidationMigrator.targetModuleId();
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates EVMScript that allows consolidation between the curated and the target operators.
    /// @param _creator Address who creates EVMScript
    /// @param _evmScriptCallData Encoded AllowConsolidationPairInput
    function createEVMScript(
        address /* _creator */,
        bytes memory _evmScriptCallData
    ) external view override returns (bytes memory) {
        AllowConsolidationPairInput memory input = _decodeEVMScriptCallData(_evmScriptCallData);

        _validateInputData(input);

        return
            EVMScriptCreator.createEVMScript(
                address(consolidationMigrator),
                IConsolidationMigrator.allowPair.selector,
                abi.encode(input.sourceOperatorId, input.targetOperatorId)
            );
    }

    /// @notice Decodes call data used by createEVMScript method.
    /// @param _evmScriptCallData Encoded AllowConsolidationPairInput
    /// @return AllowConsolidationPairInput struct with the decoded inputs
    function decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) external pure returns (AllowConsolidationPairInput memory) {
        return _decodeEVMScriptCallData(_evmScriptCallData);
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _decodeEVMScriptCallData(
        bytes memory _evmScriptCallData
    ) private pure returns (AllowConsolidationPairInput memory) {
        return abi.decode(_evmScriptCallData, (AllowConsolidationPairInput));
    }

    function _validateInputData(
        AllowConsolidationPairInput memory input
    ) private view {
        uint256 sourceCount = sourceModule.getNodeOperatorsCount();
        require(input.sourceOperatorId < sourceCount, ERROR_SOURCE_OPERATOR_ID_OUT_OF_RANGE);

        (, , address rewardAddress, , , , ) = sourceModule.getNodeOperator(
            input.sourceOperatorId,
            false
        );
        require(msg.sender == rewardAddress, ERROR_CALLER_IS_NOT_SOURCE_OPERATOR_OWNER);
        // TODO: should we allow MANAGE_SIGNING_KEYS_ROLE holders to enact the script?

        uint256 targetCount = targetModule.getNodeOperatorsCount();
        require(input.targetOperatorId < targetCount, ERROR_TARGET_OPERATOR_ID_OUT_OF_RANGE);

        require(
            consolidationMigrator.isPairAllowed(input.sourceOperatorId, input.targetOperatorId) == false,
            ERROR_PAIR_ALREADY_ALLOWED
        );
    }
}
