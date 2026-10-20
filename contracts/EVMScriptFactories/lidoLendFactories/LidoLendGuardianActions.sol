// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "../../libraries/EVMScriptCreator.sol";
import "../../interfaces/IEVMScriptFactory.sol";
import "../../interfaces/ILidoLend.sol";
import "./LidoLendOwnerFactoryBase.sol";

/// @notice Creates EVMScripts for guardian-management actions on Lido Lend markets
contract LidoLendGuardianActions is LidoLendOwnerFactoryBase, IEVMScriptFactory {
    // -------------
    // ERRORS
    // -------------

    string private constant ERROR_INVALID_ACTION = "INVALID_ACTION";
    string private constant ERROR_ZERO_GUARDIAN = "ZERO_GUARDIAN";
    string private constant ERROR_GUARDIAN_ALREADY_ADDED = "GUARDIAN_ALREADY_ADDED";
    string private constant ERROR_ACCOUNT_IS_DELEGATE = "ACCOUNT_IS_DELEGATE";
    string private constant ERROR_MAX_GUARDIANS_REACHED = "MAX_GUARDIANS_REACHED";
    string private constant ERROR_INVALID_QUORUM = "INVALID_QUORUM";
    string private constant ERROR_GUARDIAN_NOT_FOUND = "GUARDIAN_NOT_FOUND";
    string private constant ERROR_SAME_QUORUM = "SAME_QUORUM";
    string private constant ERROR_SAME_SUSPECT_WINDOW = "SAME_SUSPECT_WINDOW";
    string private constant ERROR_SUSPECT_WINDOW_TOO_HIGH = "SUSPECT_WINDOW_TOO_HIGH";
    string private constant ERROR_EMPTY_MARKETS_LIST = "EMPTY_MARKETS_LIST";
    string private constant ERROR_EMPTY_REQUESTS_LIST = "EMPTY_REQUESTS_LIST";

    // -------------
    // TYPES
    // -------------

    struct UnbanRequest {
        address account;
        bytes32[] marketIds;
    }

    /// @dev Action ordinals are part of the calldata ABI. Never reorder existing members; append only.
    enum Action {
        AddGuardian,
        RemoveGuardian,
        ReplaceGuardian,
        SetGuardiansQuorum,
        SetSuspectWindow,
        UnbanAccounts
    }

    // -------------
    // CONSTRUCTOR
    // -------------

    constructor(address _trustedCaller, address _lidoLendOwner)
        LidoLendOwnerFactoryBase(_trustedCaller, _lidoLendOwner)
    {}

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Creates an EVMScript for exactly one guardian-management action
    /// @param _creator Address who creates the EVMScript
    /// @param _evmScriptCallData Encoded tuple: (Action action, bytes payload)
    function createEVMScript(address _creator, bytes memory _evmScriptCallData)
        external
        view
        override
        onlyTrustedCaller(_creator)
        returns (bytes memory)
    {
        (Action action, bytes memory payload) = decodeEVMScriptCallData(_evmScriptCallData);

        if (action == Action.AddGuardian) {
            return _createAddGuardianEVMScript(payload);
        }
        if (action == Action.RemoveGuardian) {
            return _createRemoveGuardianEVMScript(payload);
        }
        if (action == Action.ReplaceGuardian) {
            return _createReplaceGuardianEVMScript(payload);
        }
        if (action == Action.SetGuardiansQuorum) {
            return _createSetGuardiansQuorumEVMScript(payload);
        }
        if (action == Action.SetSuspectWindow) {
            return _createSetSuspectWindowEVMScript(payload);
        }
        if (action == Action.UnbanAccounts) {
            return _createUnbanAccountsEVMScript(payload);
        }
        revert(ERROR_INVALID_ACTION);
    }

    // ------------------
    // PUBLIC DECODERS
    // ------------------

    /// @notice Decodes the common guardian-action envelope
    function decodeEVMScriptCallData(bytes memory _evmScriptCallData)
        public
        pure
        returns (Action action, bytes memory payload)
    {
        (action, payload) = abi.decode(_evmScriptCallData, (Action, bytes));
    }

    /// @notice Decodes AddGuardian payload: (bytes32 marketId, address guardian, uint256 newQuorum)
    function decodeAddGuardianPayload(bytes memory _payload)
        public
        pure
        returns (
            bytes32 marketId,
            address guardian,
            uint256 newQuorum
        )
    {
        (marketId, guardian, newQuorum) = abi.decode(_payload, (bytes32, address, uint256));
    }

    /// @notice Decodes RemoveGuardian payload: (bytes32 marketId, address guardian, uint256 newQuorum)
    function decodeRemoveGuardianPayload(bytes memory _payload)
        public
        pure
        returns (
            bytes32 marketId,
            address guardian,
            uint256 newQuorum
        )
    {
        (marketId, guardian, newQuorum) = abi.decode(_payload, (bytes32, address, uint256));
    }

    /// @notice Decodes ReplaceGuardian payload: (bytes32 marketId, address oldGuardian, address newGuardian)
    function decodeReplaceGuardianPayload(bytes memory _payload)
        public
        pure
        returns (
            bytes32 marketId,
            address oldGuardian,
            address newGuardian
        )
    {
        (marketId, oldGuardian, newGuardian) = abi.decode(_payload, (bytes32, address, address));
    }

    /// @notice Decodes SetGuardiansQuorum payload: (bytes32 marketId, uint256 newQuorum)
    function decodeSetGuardiansQuorumPayload(bytes memory _payload)
        public
        pure
        returns (bytes32 marketId, uint256 newQuorum)
    {
        (marketId, newQuorum) = abi.decode(_payload, (bytes32, uint256));
    }

    /// @notice Decodes SetSuspectWindow payload: (bytes32 marketId, uint256 newSuspectWindow)
    function decodeSetSuspectWindowPayload(bytes memory _payload)
        public
        pure
        returns (bytes32 marketId, uint256 newSuspectWindow)
    {
        (marketId, newSuspectWindow) = abi.decode(_payload, (bytes32, uint256));
    }

    /// @notice Decodes UnbanAccounts payload: UnbanRequest[]
    function decodeUnbanAccountsPayload(bytes memory _payload)
        public
        pure
        returns (UnbanRequest[] memory requests)
    {
        requests = abi.decode(_payload, (UnbanRequest[]));
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _createAddGuardianEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, address guardian, uint256 newQuorum) = decodeAddGuardianPayload(
            _payload
        );
        require(guardian != address(0), ERROR_ZERO_GUARDIAN);

        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
        require(!guardianSignals.isGuardian(guardian), ERROR_GUARDIAN_ALREADY_ADDED);
        _requireNotDelegate(guardianSignals, guardian, address(0));
        uint256 guardianCount = guardianSignals.getGuardianCount();
        require(guardianCount < guardianSignals.MAX_GUARDIANS_COUNT(), ERROR_MAX_GUARDIANS_REACHED);
        require(newQuorum != 0 && newQuorum <= guardianCount + 1, ERROR_INVALID_QUORUM);

        bytes4[] memory methodIds = new bytes4[](2);
        methodIds[0] = ILidoLendOwner.addGuardian.selector;
        methodIds[1] = ILidoLendOwner.setGuardiansQuorum.selector;

        bytes[] memory encodedCalldata = new bytes[](2);
        encodedCalldata[0] = abi.encode(marketId, guardian);
        encodedCalldata[1] = abi.encode(marketId, newQuorum);

        return EVMScriptCreator.createEVMScript(lidoLendOwner, methodIds, encodedCalldata);
    }

    function _createRemoveGuardianEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, address guardian, uint256 newQuorum) = decodeRemoveGuardianPayload(
            _payload
        );

        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
        require(guardianSignals.isGuardian(guardian), ERROR_GUARDIAN_NOT_FOUND);
        require(
            newQuorum != 0 && newQuorum < guardianSignals.getGuardianCount(),
            ERROR_INVALID_QUORUM
        );

        bytes4[] memory methodIds = new bytes4[](2);
        methodIds[0] = ILidoLendOwner.setGuardiansQuorum.selector;
        methodIds[1] = ILidoLendOwner.removeGuardian.selector;

        bytes[] memory encodedCalldata = new bytes[](2);
        encodedCalldata[0] = abi.encode(marketId, newQuorum);
        encodedCalldata[1] = abi.encode(marketId, guardian);

        return EVMScriptCreator.createEVMScript(lidoLendOwner, methodIds, encodedCalldata);
    }

    function _createReplaceGuardianEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, address oldGuardian, address newGuardian) = decodeReplaceGuardianPayload(
            _payload
        );
        require(newGuardian != address(0), ERROR_ZERO_GUARDIAN);

        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
        require(guardianSignals.isGuardian(oldGuardian), ERROR_GUARDIAN_NOT_FOUND);
        require(!guardianSignals.isGuardian(newGuardian), ERROR_GUARDIAN_ALREADY_ADDED);
        _requireNotDelegate(guardianSignals, newGuardian, oldGuardian);

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                ILidoLendOwner.replaceGuardian.selector,
                abi.encode(marketId, oldGuardian, newGuardian)
            );
    }

    function _createSetGuardiansQuorumEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, uint256 newQuorum) = decodeSetGuardiansQuorumPayload(_payload);

        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);
        require(newQuorum != guardianSignals.getQuorum(), ERROR_SAME_QUORUM);
        require(
            newQuorum != 0 && newQuorum <= guardianSignals.getGuardianCount(),
            ERROR_INVALID_QUORUM
        );

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                ILidoLendOwner.setGuardiansQuorum.selector,
                abi.encode(marketId, newQuorum)
            );
    }

    function _createSetSuspectWindowEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        (bytes32 marketId, uint256 newSuspectWindow) = decodeSetSuspectWindowPayload(_payload);
        IGuardianSignals guardianSignals = _guardianSignalsOf(marketId);

        require(
            newSuspectWindow <= guardianSignals.MAX_SUSPECT_WINDOW(),
            ERROR_SUSPECT_WINDOW_TOO_HIGH
        );
        require(newSuspectWindow != guardianSignals.getSuspectWindow(), ERROR_SAME_SUSPECT_WINDOW);

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                ILidoLendOwner.setGuardiansSuspectWindow.selector,
                abi.encode(marketId, newSuspectWindow)
            );
    }

    function _createUnbanAccountsEVMScript(bytes memory _payload)
        private
        view
        returns (bytes memory)
    {
        UnbanRequest[] memory requests = decodeUnbanAccountsPayload(_payload);
        require(requests.length > 0, ERROR_EMPTY_REQUESTS_LIST);

        bytes[] memory encodedCalldata = new bytes[](requests.length);
        for (uint256 i = 0; i < requests.length; ++i) {
            require(requests[i].marketIds.length > 0, ERROR_EMPTY_MARKETS_LIST);
            for (uint256 j = 0; j < requests[i].marketIds.length; ++j) {
                _guardianSignalsOf(requests[i].marketIds[j]);
            }
            encodedCalldata[i] = abi.encode(requests[i].marketIds, requests[i].account);
        }

        return
            EVMScriptCreator.createEVMScript(
                lidoLendOwner,
                ILidoLendOwner.unbanGuardianSignals.selector,
                encodedCalldata
            );
    }

    function _guardianSignalsOf(bytes32 _marketId) private view returns (IGuardianSignals) {
        return IGuardianSignals(_getMarketControllerOrRevert(_marketId).guardianSignals());
    }

    function _requireNotDelegate(
        IGuardianSignals _guardianSignals,
        address _account,
        address _allowedGuardian
    ) private view {
        (address[] memory guardians, address[] memory delegates) = _guardianSignals.getGuardians();
        for (uint256 i = 0; i < guardians.length; ++i) {
            require(
                delegates[i] != _account || guardians[i] == _allowedGuardian,
                ERROR_ACCOUNT_IS_DELEGATE
            );
        }
    }
}
