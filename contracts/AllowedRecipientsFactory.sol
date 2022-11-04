// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./EVMScriptFactories/AddAllowedRecipient.sol";
import "./EVMScriptFactories/RemoveAllowedRecipient.sol";
import "./EVMScriptFactories/TopUpAllowedRecipients.sol";
import "./AllowedRecipientsRegistry.sol";

contract AllowedRecipientsFactory {
    address public immutable easyTrack;
    address public immutable finance;
    address public immutable evmScriptExecutor;
    address public immutable defaultAdmin;
    IBokkyPooBahsDateTimeContract public immutable bokkyPooBahsDateTimeContract;
    
    constructor(
        address _easytrack,
        address _finance,
        address _evmScriptExecutor,
        address _defaultAdmin,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    ){
        easyTrack = _easytrack;
        finance = _finance;
        evmScriptExecutor = _evmScriptExecutor;
        defaultAdmin = _defaultAdmin;
        bokkyPooBahsDateTimeContract = _bokkyPooBahsDateTimeContract;
    }

    event AllowedRecipientsRegistryDeployed(
        address indexed creator,
        address indexed allowedRecipientsRegistry,
        address _defaultAdmin, 
        IBokkyPooBahsDateTimeContract bokkyPooBahsDateTimeContract,
        address[] addRecipientToAllowedListRoleHolders,
        address[] removeRecipientFromAllowedListRoleHolders,
        address[] setLimitParametersRoleHolders,
        address[] updateSpentAmountRoleHolders
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
        address[] memory _addRecipientToAllowedListRoleHolders,
        address[] memory _removeRecipientFromAllowedListRoleHolders,
        address[] memory _setLimitParametersRoleHolders,
        address[] memory _updateSpentAmountRoleHolders
    ) public returns(AllowedRecipientsRegistry registry) 
    {
        registry = new AllowedRecipientsRegistry(
            defaultAdmin, 
            _addRecipientToAllowedListRoleHolders,
            _removeRecipientFromAllowedListRoleHolders,
            _setLimitParametersRoleHolders,
            _updateSpentAmountRoleHolders,
            bokkyPooBahsDateTimeContract
        );
        
        emit AllowedRecipientsRegistryDeployed(
            msg.sender,
            address(registry),
            defaultAdmin,
            bokkyPooBahsDateTimeContract,
            _addRecipientToAllowedListRoleHolders,
            _removeRecipientFromAllowedListRoleHolders,
            _setLimitParametersRoleHolders,
            _updateSpentAmountRoleHolders
        );
    }

    function deployTopUpAllowedRecipients(
        address _trustedCaller, 
        address _allowedRecipientsRegistry,
        address _token
    )   
        public 
        returns(TopUpAllowedRecipients topUpAllowedRecipients) 
    {      
        topUpAllowedRecipients = new TopUpAllowedRecipients(
            _trustedCaller,
            _allowedRecipientsRegistry,
            finance,
            _token,
            easyTrack
        );

        emit TopUpAllowedRecipientsDeployed(
            msg.sender,
            address(topUpAllowedRecipients),
            _trustedCaller,
            _allowedRecipientsRegistry,
            finance,
            _token,
            easyTrack
        );

        return topUpAllowedRecipients;
    }


    function deployAddAllowedRecipient(
        address _trustedCaller, 
        address _allowedRecipientsRegistry
    ) 
        public
        returns(AddAllowedRecipient addAllowedRecipient) 
    {
        addAllowedRecipient = 
            new AddAllowedRecipient(_trustedCaller, _allowedRecipientsRegistry);

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
    ) 
        public
        returns(RemoveAllowedRecipient removeAllowedRecipient) 
    {
        removeAllowedRecipient  =
            new RemoveAllowedRecipient(_trustedCaller, _allowedRecipientsRegistry);

        emit RemoveAllowedRecipientDeployed(
            msg.sender,
            address(removeAllowedRecipient),
            _trustedCaller,
            _allowedRecipientsRegistry
        );
    }
}
