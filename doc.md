
# Table of Contents

1.  [Intro](#org048fc2c)
2.  [Contract initialization](#org18dcc72)
3.  [Vote initiation](#org439654d)
    1.  [Check credentials to start vote](#org6e0561c)
        1.  [validator request](#org970587f)
        2.  [grant distibution](#orge03c875)
        3.  [payments of rewards](#orgabf1818)
        4.  [regular insurance payments](#org6d0f9ec)
4.  [Objections](#org4d1d652)
    1.  [Avoidance of malicious objections](#orgd356024)
    2.  [Send objection function](#org896218f)
5.  [Expiration of the voting period](#org9f911bf)
    1.  [Objection threshold](#org3429ea5)
6.  [Execution of voting](#org47172a4)
7.  [Monitoring of voting](#orgca456d2)
8.  [Tangle](#orgc9afa10)
    1.  [validator's requests contract](#orgb71978c)



<a id="org048fc2c"></a>

# Intro

У нас есть 4 трека, каждый из них может одновременно вести
одно голосование.

[TODO:gmm] не будет паралельных голосований на одном треке?

Голосование может начать кто-то кто обладает правами, при
этом для каждого трека эти права и процедура их проверки
разные. Поэтому я буду подставлять различающееся в один и
тот же шаблон контракта, чтобы DRY.

Предложение считается принятым, если до его окончания не
было получено достаточно возражений.

Tracks variants:

-   validators requests
-   grant distibution
-   payments of rewards
-   regular insurance payments


<a id="org18dcc72"></a>

# Contract initialization

Init нужен чтобы определить, кто может добавлять тех, кому
разрешено начинать голосование. По идее, только контракт
всеобщего голосования DAO может сделать это.

[TODO:gmm] - Лучше ли обойтись только assert-ом без init-а?

[TODO:gmm] - Нужен механизм, чтобы поменять адрес такого
контракта?

[TODO:gmm] - Как мне представиться контрактом голосования
DAO, чтобы протестить это? Как написать такой тест? Как-то так?

    # Lido DAO Vote contract
    interface DaoVote:
        def someFunc(_someparam: someType): payable
        ...

    @external
    def __init__(_admin: address):
        self.admins[_admin] = True


<a id="org439654d"></a>

# Vote initiation

Начинаем голосование easy-track, вызвая `start_vote`. Он
вызовет `check_creds` чтобы проверить, может ли `msg.sender`
начинать голосование.

`check_creds`-функции свои для каждого easy-track.

[TODO:gmm] - Минимальное время между попытками одного
пользователя создать новое голосоваине

[TODO:gmm] - Минимальный порог для начала голосования

[TODO:gmm] - Нужно лочить токены, чтобы одними и теми же
токенами нельзя было создавать голосования слишком часто

    # Starting vote process
    @external
    def start_vote():
        # Check
        self._check_creds(msg.sender)


<a id="org6e0561c"></a>

## Check credentials to start vote

Для каждого трека способ проверки прав для начала
голосования свой


<a id="org970587f"></a>

### validator request

Тот кто хочет начать голосование должен быть
валидатором. Допустим, мы ведем хеш-таблицу валидаторов:

    validators: public(HashMap[address, bool])

Тогда нужен список адресов, которые может добавлять и
удалять валидаторов:

    admins: public(HashMap[address, bool])

и функции добавления и удаления валидаторов:

    @external
    def add_validator(_param: address):
        assert self.admins[msg.sender], "not an admin"
        self.validators[_param] = True

    @external
    def del_validator(_param: address):
        assert self.admins[msg.sender], "not an admin"
        self.validators[_param] = False

И теперь можно проверять адрес на наличие в списке валидаторов

    @external
    def add_validator(_param: address):
        assert self.admins[msg.sender], "not an admin"
        self.validators[_param] = True

    @external
    def del_validator(_param: address):
        assert self.admins[msg.sender], "not an admin"
        self.validators[_param] = False

    @internal
    def _check_creds(sender: address):
        assert self.validators[sender], "not a validator"


<a id="orge03c875"></a>

### grant distibution

Голосование начинается, если удовлетворены требования
пороговой подписи K из N

[TODO:gmm] как написать проверку порога?


<a id="orgabf1818"></a>

### payments of rewards

[TODO:gmm] Эти пэйменты будет вызывать арагон-агент. Как?


<a id="org6d0f9ec"></a>

### regular insurance payments

[TODO:gmm] Тут надо делать периодический вызов? Как?


<a id="org4d1d652"></a>

# Objections


<a id="orgd356024"></a>

## Avoidance of malicious objections

Существует атака, при которой возражающий может продать
проголосовавшие жетоны и сразу же купить новые, чтобы
проголосовать снова. Чтобы этого не произошло, в контракте
easy-track необходимо обратиться к менеджеру токенов, чтобы
запретить передачу этих токенов до конца голосования.

Еще более экономичный способ - использовать остатки на
момент блока, в котором началось голосование. То есть
голосовать могут только жетоны, которые не были перемещены с
момента начала голосования.


<a id="org896218f"></a>

## Send objection function

[TODO:gmm] send<sub>objection</sub> fun

[TODO:gmm] проверка не истекло ли время голосования

    # Starting vote process
    @external
    def send_objection():
        ...


<a id="org9f911bf"></a>

# Expiration of the voting period

[TODO:gmm] - Как я могу получить время, чтобы определить что
голосование пора завершать?

[TODO:gmm] - Если голосование завершено, то здесь нужен
event?

[TODO:gmm] - Подсчет возражений

[TODO:gmm] - Как мне запустить что-то по результатам?


<a id="org3429ea5"></a>

## Objection threshold

[TODO:gmm] Нужен свой порог для каждого трека


<a id="org47172a4"></a>

# Execution of voting

Если голосование успешно завершено, надо вызвать функцию,
которая переведет деньги.

[TODO:gmm] - Она внешняя?

[TODO:gmm] - Вызывать через интерфейс?

    @external
    @payable
    def execute_purchase(_ldo_receiver: address = msg.sender) -> uint256:
        """
        @notice Purchases for the specified address (defaults to message sender).
        @param _ldo_receiver The address the purchase is executed for.
        @return Vesting ID to be used with the DAO's `TokenManager` contract.
        """
        return self._execute_purchase(_ldo_receiver, msg.sender, msg.value)


    @internal
    def _execute_vote(_ldo_receiver: address, _caller: address, _eth_received: uint256) -> uint256:
        """
        @dev
            We don't use any reentrancy lock here because, among all external calls in this
            function (Vault.deposit, TokenManager.assignVested, LDO.transfer, and the default
            payable function of the message sender), only the last one executes the code not
            under our control, and we make this call after all state mutations.
        """
        assert block.timestamp < self.offer_expires_at, "offer expired"

        ldo_allocation: uint256 = 0
        eth_cost: uint256 = 0
        ldo_allocation, eth_cost = self._get_allocation(_ldo_receiver)

        assert ldo_allocation > 0, "no allocation"
        assert _eth_received >= eth_cost, "insufficient funds"

        # clear the purchaser's allocation
        self.ldo_allocations[_ldo_receiver] = 0

        # forward ETH cost of the purchase to the DAO treasury contract
        Vault(LIDO_DAO_VAULT).deposit(
            LIDO_DAO_VAULT_ETH_TOKEN,
            eth_cost,
            value=eth_cost
        )

        vesting_start: uint256 = block.timestamp
        vesting_cliff: uint256 = vesting_start + self.vesting_cliff_delay
        vesting_end: uint256 = vesting_start + self.vesting_end_delay

        # TokenManager can only assign vested tokens from its own balance
        assert ERC20(LDO_TOKEN).transfer(LIDO_DAO_TOKEN_MANAGER, ldo_allocation)

        # assign vested LDO tokens to the purchaser from the DAO treasury reserves
        # Vyper has no uint64 data type so we have to use raw_call instead of an interface
        call_result: Bytes[32] = raw_call(
            LIDO_DAO_TOKEN_MANAGER,
            concat(
                method_id('assignVested(address,uint256,uint64,uint64,uint64,bool)'),
                convert(_ldo_receiver, bytes32),
                convert(ldo_allocation, bytes32),
                convert(vesting_start, bytes32),
                convert(vesting_cliff, bytes32),
                convert(vesting_end, bytes32),
                convert(False, bytes32)
            ),
            max_outsize=32
        )
        vesting_id: uint256 = convert(extract32(call_result, 0), uint256)

        log PurchaseExecuted(_ldo_receiver, ldo_allocation, eth_cost, vesting_id)

        # refund any excess ETH to the caller
        eth_refund: uint256 = _eth_received - eth_cost
        if eth_refund > 0:
            # use raw_call to forward all remaining gas just in case the caller is a smart contract
            raw_call(_caller, b"", value=eth_refund)

        return vesting_id


<a id="orgca456d2"></a>

# Monitoring of voting

[TODO:gmm] - Как это делать?


<a id="orgc9afa10"></a>

# Tangle

[TODO:gmm] - Общие вещи если надо


<a id="orgb71978c"></a>

## validator's requests contract

Сделаем генерацию контракта для validator's requests

    # @version 0.2.8
    # @author Lido <info@lido.fi>
    # @licence MIT

    validators: public(HashMap[address, bool])
    admins: public(HashMap[address, bool])

    @external
    def __init__(_admin: address):
        self.admins[_admin] = True

    @external
    def add_validator(_param: address):
        assert self.admins[msg.sender], "not an admin"
        self.validators[_param] = True

    @external
    def del_validator(_param: address):
        assert self.admins[msg.sender], "not an admin"
        self.validators[_param] = False

    @internal
    def _check_creds(sender: address):
        assert self.validators[sender], "not a validator"

    # Starting vote process
    @external
    def start_vote():
        # Check
        self._check_creds(msg.sender)
