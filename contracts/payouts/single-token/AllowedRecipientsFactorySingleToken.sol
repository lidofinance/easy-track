// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "contracts/EVMScriptFactories/AddAllowedRecipient.sol";
import "contracts/EVMScriptFactories/RemoveAllowedRecipient.sol";
import "./TopUpAllowedRecipientsSingleToken.sol";
import "contracts/AllowedRecipientsRegistry.sol";

/// @author bulbozaur
/// @notice Factory for Allowed Recipient Easy Track contracts
contract AllowedRecipientsFactorySingleToken {
    event AllowedRecipientsRegistryDeployed(
        address indexed creator,
        address indexed allowedRecipientsRegistry,
        address _defaultAdmin,
        address[] addRecipientToAllowedListRoleHolders,
        address[] removeRecipientFromAllowedListRoleHolders,
        address[] setLimitParametersRoleHolders,
        address[] updateSpentAmountRoleHolders,
        IBokkyPooBahsDateTimeContract bokkyPooBahsDateTimeContract
    );

    event TopUpAllowedRecipientsDeployed(
        address indexed creator,
        address indexed topUpAllowedRecipients,
        address trustedCaller,
        address allowedRecipientsRegistry,
        address finance,
        address token,
        address easyTrack
    );

    event AddAllowedRecipientDeployed(
        address indexed creator,
        address indexed addAllowedRecipient,
        address trustedCaller,
        address allowedRecipientsRegistry
    );

    event RemoveAllowedRecipientDeployed(
        address indexed creator,
        address indexed removeAllowedRecipient,
        address trustedCaller,
        address allowedRecipientsRegistry
    );

    function deployAllowedRecipientsRegistry(
        address _defaultAdmin,
        address[] memory _addRecipientToAllowedListRoleHolders,
        address[] memory _removeRecipientFromAllowedListRoleHolders,
        address[] memory _setLimitParametersRoleHolders,
        address[] memory _updateSpentAmountRoleHolders,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    ) public returns (AllowedRecipientsRegistry registry) {
        registry = new AllowedRecipientsRegistry(
            _defaultAdmin,
            _addRecipientToAllowedListRoleHolders,
            _removeRecipientFromAllowedListRoleHolders,
            _setLimitParametersRoleHolders,
            _updateSpentAmountRoleHolders,
            _bokkyPooBahsDateTimeContract
        );

        emit AllowedRecipientsRegistryDeployed(
            msg.sender,
            address(registry),
            _defaultAdmin,
            _addRecipientToAllowedListRoleHolders,
            _removeRecipientFromAllowedListRoleHolders,
            _setLimitParametersRoleHolders,
            _updateSpentAmountRoleHolders,
            _bokkyPooBahsDateTimeContract
        );
    }

    function deployTopUpAllowedRecipients(
        address _trustedCaller,
        address _allowedRecipientsRegistry,
        address _token,
        address _finance,
        address _easyTrack
    ) public returns (TopUpAllowedRecipientsSingleToken topUpAllowedRecipients) {
        topUpAllowedRecipients = new TopUpAllowedRecipientsSingleToken(
            _trustedCaller,
            _allowedRecipientsRegistry,
            _finance,
            _token,
            _easyTrack
        );

        emit TopUpAllowedRecipientsDeployed(
            msg.sender,
            address(topUpAllowedRecipients),
            _trustedCaller,
            _allowedRecipientsRegistry,
            _finance,
            _token,
            _easyTrack
        );

        return topUpAllowedRecipients;
    }

    function deployAddAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry)
        public
        returns (AddAllowedRecipient addAllowedRecipient)
    {
        addAllowedRecipient = new AddAllowedRecipient(_trustedCaller, _allowedRecipientsRegistry);

        emit AddAllowedRecipientDeployed(
            msg.sender,
            address(addAllowedRecipient),
            _trustedCaller,
            _allowedRecipientsRegistry
        );
    }

    function deployRemoveAllowedRecipient(
        address _trustedCaller,
        address _allowedRecipientsRegistry
    ) public returns (RemoveAllowedRecipient removeAllowedRecipient) {
        removeAllowedRecipient = new RemoveAllowedRecipient(
            _trustedCaller,
            _allowedRecipientsRegistry
        );

        emit RemoveAllowedRecipientDeployed(
            msg.sender,
            address(removeAllowedRecipient),
            _trustedCaller,
            _allowedRecipientsRegistry
        );
    }
}
