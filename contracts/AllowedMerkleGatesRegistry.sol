// SPDX-FileCopyrightText: 2025 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.6;

import "OpenZeppelin/openzeppelin-contracts@4.3.2/contracts/access/AccessControl.sol";

/// @title Registry of allowed merkle gates addresses of Staking Module
/// @notice Stores list of allowed addresses
contract AllowedMerkleGatesRegistry is AccessControl {
    // -------------
    // EVENTS
    // -------------
    event GateAdded(address indexed _gate, string _title);
    event GateRemoved(address indexed _gate);

    // -------------
    // ERRORS
    // -------------
    string private constant ERROR_GATE_ALREADY_ADDED_TO_ALLOWED_LIST =
        "GATE_ALREADY_ADDED_TO_ALLOWED_LIST";
    string private constant ERROR_GATE_NOT_FOUND_IN_ALLOWED_LIST =
        "GATE_NOT_FOUND_IN_ALLOWED_LIST";
    string private constant ERROR_INITIAL_GATES_AND_TITLES_LENGTH_MISMATCH =
        "INITIAL_GATES_AND_TITLES_LENGTH_MISMATCH";

    // -------------
    // VARIABLES
    // -------------

    /// @dev List of allowed gates
    address[] private allowedGates;

    // Position of the address in the `allowedGates` array,
    // plus 1 because index 0 means a value is not in the set.
    mapping(address => uint256) private allowedGateIndices;

    // -------------
    // CONSTRUCTOR
    // -------------

    /// @param _admin Address which will be granted with role DEFAULT_ADMIN_ROLE
    /// @param _gates Initial list of allowed gates
    /// @param _titles Titles for initial gates
    constructor(address _admin, address[] memory _gates, string[] memory _titles) {
        _setupRole(DEFAULT_ADMIN_ROLE, _admin);

        require(
            _gates.length == _titles.length,
            ERROR_INITIAL_GATES_AND_TITLES_LENGTH_MISMATCH
        );

        for (uint256 i = 0; i < _gates.length; ++i) {
            _addGate(_gates[i], _titles[i]);
        }
    }

    // -------------
    // EXTERNAL METHODS
    // -------------

    /// @notice Adds address to list of allowed addresses
    function addGate(address _gate, string memory _title)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        _addGate(_gate, _title);
    }

    /// @notice Removes address from list of allowed addresses 
    /// @dev To delete an allowed address from the allowedGates array in O(1),
    /// we swap the element to delete with the last one in the array,
    /// and then remove the last element (sometimes called as 'swap and pop').
    function removeGate(address _gate)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        uint256 index = _getAllowedGateIndex(_gate);
        uint256 lastIndex = allowedGates.length - 1;

        if (index != lastIndex) {
            address lastAllowedGate = allowedGates[lastIndex];
            allowedGates[index] = lastAllowedGate;
            allowedGateIndices[lastAllowedGate] = index + 1;
        }

        allowedGates.pop();
        delete allowedGateIndices[_gate];
        emit GateRemoved(_gate);
    }

    /// @notice Returns if passed address is listed as allowed gate in the registry
    function isGateAllowed(address _gate) external view returns (bool) {
        return allowedGateIndices[_gate] > 0;
    }

    /// @notice Returns current list of allowed gates
    function getAllowedGates() external view returns (address[] memory) {
        return allowedGates;
    }

    // ------------------
    // PRIVATE METHODS
    // ------------------

    function _getAllowedGateIndex(address _gate) private view returns (uint256 _index) {
        _index = allowedGateIndices[_gate];
        require(_index > 0, ERROR_GATE_NOT_FOUND_IN_ALLOWED_LIST);
        _index -= 1;
    }

    function _addGate(address _gate, string memory _title) private {
        require(
            allowedGateIndices[_gate] == 0,
            ERROR_GATE_ALREADY_ADDED_TO_ALLOWED_LIST
        );

        allowedGates.push(_gate);
        allowedGateIndices[_gate] = allowedGates.length;
        emit GateAdded(_gate, _title);
    }
}
