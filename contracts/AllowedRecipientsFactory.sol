// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./EVMScriptFactories/AddAllowedRecipient.sol";
import "./EVMScriptFactories/RemoveAllowedRecipient.sol";
import "./EVMScriptFactories/TopUpAllowedRecipients.sol";
import "./AllowedRecipientsRegistry.sol";


contract AllowedRecipientsFactory {

    bytes32 public constant ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE =
        keccak256("ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE");
    bytes32 public constant REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE =
        keccak256("REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE");
    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 public constant SET_LIMIT_PARAMETERS_ROLE = keccak256("SET_LIMIT_PARAMETERS_ROLE");
    bytes32 public constant UPDATE_SPENT_AMOUNT_ROLE = keccak256("UPDATE_SPENT_AMOUNT_ROLE");


    address public immutable easyTrack;
    address public immutable finance;
    address public immutable evmScriptExecutor;
    address public immutable defaultAdmin;

    event AllowedRecipientsRegistryDeployed(
        address creator,
        address admin,
        address[] addRecipientToAllowedListRoleHolders,
        address[] removeRecipientFromAllowedListRoleHolders,
        address[] setLimitParametersRoleHolders,
        address[] updateSpentAmountRoleHolders,
        IBokkyPooBahsDateTimeContract bokkyPooBahsDateTimeContract
    );

    event AddAllowedRecipientDeployed(
        address creator,
        address trustedCaller,
        address allowedRecipientsRegistry
    );

    event RemoveAllowedRecipientDeployed(
        address creator,
        address trustedCaller,
        address allowedRecipientsRegistry
    );

    event TopUpAllowedRecipientsDeployed(
        address creator,
        address trustedCaller,
        address allowedRecipientsRegistry,
        address finance,
        address token,
        address easyTrack
    );

    constructor(
        address _easytrack,
        address _finance,
        address _evmScriptExecutor,
        address _defaultAdmin
    ){
        easyTrack = _easytrack;
        finance = _finance;
        evmScriptExecutor = _evmScriptExecutor;
        defaultAdmin = _defaultAdmin;

    }

    function deploySingleRecipientSetup(
        address _trustedCaller, 
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract,
        address _token,
        uint256 _limit, 
        uint256 _periodDurationMonths
    ) public returns (address) {
        AllowedRecipientsRegistry registry = _deployBaseSetup(
            _trustedCaller,
            _bokkyPooBahsDateTimeContract,
            _token,
            _limit,
            _periodDurationMonths
        );

        registry.renounceRole(DEFAULT_ADMIN_ROLE, address(this));

        _check_factory_roles_renounced(registry);
    }

    function deployFullSetup(
        address _trustedCaller, 
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract,
        address _token,
        uint256 _limit, 
        uint256 _periodDurationMonths
    ) public returns (address) {
        AllowedRecipientsRegistry registry = _deployFullSetup(
            _trustedCaller,
            _bokkyPooBahsDateTimeContract,
            _token,
            _limit,
            _periodDurationMonths
        );

        registry.renounceRole(DEFAULT_ADMIN_ROLE, address(this));

        _check_factory_roles_renounced(registry);
    }

    function deployFullSetup(
        address _trustedCaller, 
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract,
        address _token,
        uint256 _limit, 
        uint256 _periodDurationMonths,
        address[] memory _recipients, 
        string[] memory _titles,
        uint256 _spentAmount
    ) public returns (address) {

        require(_recipients.length == _titles.length);

        AllowedRecipientsRegistry registry = _deployFullSetup(
            _trustedCaller,
            _bokkyPooBahsDateTimeContract,
            _token,
            _limit,
            _periodDurationMonths
        );
        
        registry.grantRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(this));

        for (uint256 i = 0; i < _recipients.length; i++) {
            registry.addRecipient(_recipients[i], _titles[i]);
        }

        registry.renounceRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(this));
        registry.renounceRole(DEFAULT_ADMIN_ROLE, address(this));

        _check_factory_roles_renounced(registry);
    }

    function deployAllowedRecipientsRegistry(
        address[] memory _addRecipientToAllowedListRoleHolders,
        address[] memory _removeRecipientFromAllowedListRoleHolders,
        address[] memory _setLimitParametersRoleHolders,
        address[] memory _updateSpentAmountRoleHolders,
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract
    ) public returns(AllowedRecipientsRegistry) 
    {
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            defaultAdmin,
            _addRecipientToAllowedListRoleHolders,
            _removeRecipientFromAllowedListRoleHolders,
            _setLimitParametersRoleHolders,
            _updateSpentAmountRoleHolders,
            _bokkyPooBahsDateTimeContract
        );

        emit AllowedRecipientsRegistryDeployed(
            msg.sender,
            defaultAdmin,
            _addRecipientToAllowedListRoleHolders,
            _removeRecipientFromAllowedListRoleHolders,
            _setLimitParametersRoleHolders,
            _updateSpentAmountRoleHolders,
            _bokkyPooBahsDateTimeContract
        );

        return registry;
    }

    function deployAddAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry) 
        public
        returns(AddAllowedRecipient) 
    {
        AddAllowedRecipient addAllowedRecipient = 
            new AddAllowedRecipient(_trustedCaller, _allowedRecipientsRegistry);

        emit AddAllowedRecipientDeployed(
            msg.sender,
            _trustedCaller,
            _allowedRecipientsRegistry
        );

        return addAllowedRecipient;
    }

    
    function deployRemoveAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry) 
        public
        returns(RemoveAllowedRecipient) 
    {
        RemoveAllowedRecipient removeAllowedRecipient =
            new RemoveAllowedRecipient(_trustedCaller, _allowedRecipientsRegistry);

        emit RemoveAllowedRecipientDeployed(
            msg.sender,
            _trustedCaller,
            _allowedRecipientsRegistry
        );

        return removeAllowedRecipient;
    }

    function deployTopUpAllowedRecipients(
        address _trustedCaller, 
        address _allowedRecipientsRegistry,
        address _token
    )   public returns(TopUpAllowedRecipients) 
    {
        TopUpAllowedRecipients topUpAllowedRecipients = new TopUpAllowedRecipients(
            _trustedCaller,
            _allowedRecipientsRegistry,
            finance,
            _token,
            easyTrack
        );

        emit TopUpAllowedRecipientsDeployed(
            msg.sender,
            _trustedCaller,
            _allowedRecipientsRegistry,
            finance,
            _token,
            easyTrack
        );
        
        return topUpAllowedRecipients;
    }

    function _deployFullSetup(
        address _trustedCaller, 
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract,
        address _token,
        uint256 _limit, 
        uint256 _periodDurationMonths
    ) private returns (AllowedRecipientsRegistry) {
        AllowedRecipientsRegistry registry = _deployBaseSetup(
            _trustedCaller, 
            _bokkyPooBahsDateTimeContract, 
            _token, 
            _limit, 
            _periodDurationMonths
        );
        
        AddAllowedRecipient addAllowedRecipient = deployAddAllowedRecipient(
            _trustedCaller,
            address(registry)
        );
        RemoveAllowedRecipient removeAllowedRecipient = deployRemoveAllowedRecipient(
            _trustedCaller,
            address(registry)
        );
        
        registry.grantRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(addAllowedRecipient));
        registry.grantRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, address(removeAllowedRecipient));

        require(registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(addAllowedRecipient)));
        require(registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, address(removeAllowedRecipient)));

        return registry;
    }

    function _deployBaseSetup(
        address _trustedCaller, 
        IBokkyPooBahsDateTimeContract _bokkyPooBahsDateTimeContract,
        address _token,
        uint256 _limit, 
        uint256 _periodDurationMonths
    ) private returns (AllowedRecipientsRegistry) {
        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            address(this), 
            new address[](0),
            new address[](0),
            new address[](0),
            new address[](0), 
            _bokkyPooBahsDateTimeContract
        );
        
        TopUpAllowedRecipients topUpAllowedRecipients = deployTopUpAllowedRecipients(
            _trustedCaller,
            address(registry),
            _token
        );
        
        registry.grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
        registry.grantRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, defaultAdmin);
        registry.grantRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, defaultAdmin);
        registry.grantRole(SET_LIMIT_PARAMETERS_ROLE, defaultAdmin);
        registry.grantRole(UPDATE_SPENT_AMOUNT_ROLE, defaultAdmin);

        require(registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, defaultAdmin));
        require(registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, defaultAdmin));
        require(registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, defaultAdmin));
        require(registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, defaultAdmin));

        return registry;
    }

    function _check_factory_roles_renounced(AllowedRecipientsRegistry registry) private
    {
        require(!registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(this)));
        require(!registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, address(this)));
        require(!registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, address(this)));
        require(!registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, address(this)));
        require(!registry.hasRole(DEFAULT_ADMIN_ROLE, address(this)));
    }
    
}