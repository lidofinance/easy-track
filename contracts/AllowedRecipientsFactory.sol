// SPDX-FileCopyrightText: 2022 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.4;

import "./EVMScriptFactories/AddAllowedRecipient.sol";
import "./EVMScriptFactories/RemoveAllowedRecipient.sol";
import "./EVMScriptFactories/TopUpAllowedRecipients.sol";
import "./AllowedRecipientsRegistry.sol";

contract AllowedRecipientsFactory {

    struct AllowedRecipientsEasyTrack {
        address allowedRecipientsRegistry;
        address topUpAllowedRecipients;
        address addAllowedRecipient;
        address removeAllowedRecipient;
    }

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
    IBokkyPooBahsDateTimeContract public bokkyPooBahsDateTimeContract;

    event AllowedRecipientsRegistryDeployed(
        address indexed creator,
        address indexed allowedRecipientsRegistry,
        uint256 limit, 
        uint256 periodDurationMonths,
        uint256 spentAmount
    );

    event AllowedRecipientsRegistryRecipients(
        address[] recipients, 
        string[] titles
    );

    event FactoryInitialized(
        address easyTrack,
        address finance,
        address evmScriptExecutor,
        address defaultAdmin,
        IBokkyPooBahsDateTimeContract bokkyPooBahsDateTimeContract
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

    event TopUpAllowedRecipientsDeployed(
        address indexed creator,
        address indexed topUpAllowedRecipients,
        address trustedCaller,
        address allowedRecipientsRegistry,
        address finance,
        address token,
        address easyTrack
    );

    event AllowedRecipientsSetupDeployed(
        address indexed creator,
        address allowedRecipientsRegistry,
        address topUpAllowedRecipients,
        address addAllowedRecipient,
        address removeAllowedRecipient
    );

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
        
        emit FactoryInitialized(
            _easytrack,
            _finance,
            _evmScriptExecutor,
            _defaultAdmin,
            _bokkyPooBahsDateTimeContract
        );
    }

    function deployAllowedRecipientsRegistry(
        address[] memory _recipients, 
        string[] memory _titles,
        uint256 _limit, 
        uint256 _periodDurationMonths,
        uint256 _spentAmount
    ) public returns(AllowedRecipientsRegistry) 
    {
        require(_recipients.length == _titles.length);
        require(_spentAmount <= _limit);
        
        address[] memory addRecipientToAllowedListRoleHolders = new address[](3);
        addRecipientToAllowedListRoleHolders[0] = defaultAdmin;
        addRecipientToAllowedListRoleHolders[1] = evmScriptExecutor;
        addRecipientToAllowedListRoleHolders[2] = address(this);
        address[] memory removeRecipientFromAllowedListRoleHolders = new address[](2);
        removeRecipientFromAllowedListRoleHolders[0] = defaultAdmin;
        removeRecipientFromAllowedListRoleHolders[1] = evmScriptExecutor;
        address[] memory setLimitParametersRoleHolders = new address[](2);
        setLimitParametersRoleHolders[0] = defaultAdmin;
        setLimitParametersRoleHolders[1] = address(this);
        address[] memory updateSpentAmountRoleHolders = new address[](3);
        updateSpentAmountRoleHolders[0] = defaultAdmin;
        updateSpentAmountRoleHolders[1] = evmScriptExecutor;
        updateSpentAmountRoleHolders[2] = address(this);

        AllowedRecipientsRegistry registry = new AllowedRecipientsRegistry(
            defaultAdmin, 
            addRecipientToAllowedListRoleHolders,
            removeRecipientFromAllowedListRoleHolders,
            setLimitParametersRoleHolders,
            updateSpentAmountRoleHolders,
            bokkyPooBahsDateTimeContract
        );
        
        for (uint256 i = 0; i < _recipients.length; i++) {
            registry.addRecipient(_recipients[i], _titles[i]);
        }
        registry.renounceRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(this));

        require(registry.getAllowedRecipients().length == _recipients.length);

        for (uint256 i = 0; i < _recipients.length; i++) {
            require(registry.isRecipientAllowed(_recipients[i]));
        }       

        registry.setLimitParameters(_limit, _periodDurationMonths);
        registry.renounceRole(SET_LIMIT_PARAMETERS_ROLE, address(this));

        registry.updateSpentAmount(_spentAmount);
        registry.renounceRole(UPDATE_SPENT_AMOUNT_ROLE, address(this));

        require(registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, defaultAdmin));
        require(registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, defaultAdmin));
        require(registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, defaultAdmin));
        require(registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, defaultAdmin));
        require(registry.hasRole(DEFAULT_ADMIN_ROLE, defaultAdmin));

        require(registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, evmScriptExecutor));
        require(registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, evmScriptExecutor));
        require(registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, evmScriptExecutor));

        require(!registry.hasRole(ADD_RECIPIENT_TO_ALLOWED_LIST_ROLE, address(this)));
        require(!registry.hasRole(REMOVE_RECIPIENT_FROM_ALLOWED_LIST_ROLE, address(this)));
        require(!registry.hasRole(SET_LIMIT_PARAMETERS_ROLE, address(this)));
        require(!registry.hasRole(UPDATE_SPENT_AMOUNT_ROLE, address(this)));
        require(!registry.hasRole(DEFAULT_ADMIN_ROLE, address(this)));
        
        emit AllowedRecipientsRegistryDeployed(
            msg.sender,
            address(registry),
            _limit, 
            _periodDurationMonths,
            _spentAmount
        );

        emit AllowedRecipientsRegistryRecipients( 
            _recipients, 
            _titles
        );

        return registry;
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

        require(topUpAllowedRecipients.token() == _token);
        require(address(topUpAllowedRecipients.allowedRecipientsRegistry()) == _allowedRecipientsRegistry);

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


    function deployAddAllowedRecipient(address _trustedCaller, address _allowedRecipientsRegistry) 
        public
        returns(AddAllowedRecipient) 
    {
        AddAllowedRecipient addAllowedRecipient = 
            new AddAllowedRecipient(_trustedCaller, _allowedRecipientsRegistry);

        require(address(addAllowedRecipient.allowedRecipientsRegistry()) == _allowedRecipientsRegistry);

        emit AddAllowedRecipientDeployed(
            msg.sender,
            address(addAllowedRecipient),
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

        require(address(removeAllowedRecipient.allowedRecipientsRegistry()) == _allowedRecipientsRegistry);

        emit RemoveAllowedRecipientDeployed(
            msg.sender,
            address(removeAllowedRecipient),
            _trustedCaller,
            _allowedRecipientsRegistry
        );

        return removeAllowedRecipient;
    }

    function deployFullSetup(
        address _trustedCaller,
        address[] memory _recipients, 
        string[] memory _titles,
        address _token, 
        uint256 _limit, 
        uint256 _periodDurationMonths,
        uint256 _spentAmount
    ) public returns (AllowedRecipientsEasyTrack memory) {
        AllowedRecipientsRegistry registry = deployAllowedRecipientsRegistry(
            _recipients,
            _titles,
            _limit, 
            _periodDurationMonths,
            _spentAmount
        );

        TopUpAllowedRecipients topUpAllowedRecipients = deployTopUpAllowedRecipients(
            _trustedCaller, 
            address(registry),
            _token
        );

        AddAllowedRecipient addAllowedRecipient = deployAddAllowedRecipient(
            _trustedCaller, 
            address(registry)
        );

        RemoveAllowedRecipient removeAllowedRecipient = deployRemoveAllowedRecipient(
            _trustedCaller, 
            address(registry)
        );

        emit AllowedRecipientsSetupDeployed(
            msg.sender,
            address(registry),
            address(topUpAllowedRecipients),
            address(addAllowedRecipient),
            address(removeAllowedRecipient)
        );

        return AllowedRecipientsEasyTrack(
            address(registry),
            address(topUpAllowedRecipients),
            address(addAllowedRecipient),
            address(removeAllowedRecipient)
        );
    }

    function _deploySingleRecipientTopUpOnlySetup(
        address _recipient, 
        string memory _title,
        address _token,
        uint256 _limit, 
        uint256 _periodDurationMonths
    ) public returns (AllowedRecipientsEasyTrack memory) {
        address[] memory recipients = new address[](1);
        recipients[0] = _recipient;

        string[] memory titles = new string[](1);
        titles[0] = _title;

        AllowedRecipientsRegistry registry = deployAllowedRecipientsRegistry(
            recipients,
            titles,
            _limit, 
            _periodDurationMonths,
            0
        );

        TopUpAllowedRecipients topUpAllowedRecipients = deployTopUpAllowedRecipients(
            _recipient, 
            address(registry),
            _token
        );

        emit AllowedRecipientsSetupDeployed(
            msg.sender,
            address(registry),
            address(topUpAllowedRecipients),
            address(0),
            address(0)
        );

        return AllowedRecipientsEasyTrack(
            address(registry),
            address(topUpAllowedRecipients),
            address(0),
            address(0)
        );
    }
}
