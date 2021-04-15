
# Table of Contents

1.  [Intro](#orgfb54a09)
2.  [Contract initialization](#org9273de6)
3.  [Vote initiation](#org06473c8)
    1.  [Check credentials to start vote](#org5898994)
        1.  [validator request](#org66fd09e)
        2.  [grant distibution](#org959ea5c)
        3.  [payments of rewards](#org97baa11)
        4.  [regular insurance payments](#org5b36df8)
4.  [Objections](#org78c98dd)
    1.  [Avoidance of malicious objections](#org994134f)
    2.  [Send objection function](#org0d86621)
5.  [Expiration of the voting period](#org228686c)
    1.  [Objection threshold](#org52dad47)
6.  [Execution of voting](#org89231f3)
7.  [Monitoring of voting](#org3893d3d)
8.  [Tangle](#org4fe5a1e)
    1.  [validator's requests contract](#org07c3506)
    2.  [test for validator's requests contract](#org255dfd6)



<a id="orgfb54a09"></a>

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


<a id="org9273de6"></a>

# Contract initialization

Init нужен чтобы определить, кто может добавлять тех, кому
разрешено начинать голосование. По идее, только контракт
всеобщего голосования DAO может сделать это.

[TODO:gmm] - В ldo<sub>purchase</sub><sub>executor</sub>/script/deploy.py есть
функция deploy<sub>and</sub><sub>start</sub><sub>dao</sub><sub>vote</sub> надо посмотреть можно по
ней что-то понять. Там же есть про деполой контракта и как
проголосовать (отправить возражение) в dao<sub>voting.vote</sub> что
вероятно поможет написать тесты.

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


<a id="org06473c8"></a>

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


<a id="org5898994"></a>

## Check credentials to start vote

Для каждого трека способ проверки прав для начала
голосования свой


<a id="org66fd09e"></a>

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


<a id="org959ea5c"></a>

### grant distibution

Голосование начинается, если удовлетворены требования
пороговой подписи K из N

[TODO:gmm] как написать проверку порога?


<a id="org97baa11"></a>

### payments of rewards

[TODO:gmm] Эти пэйменты будет вызывать арагон-агент. Как?
Мне надо достать интерфейс и посмотреть как у арагона это
сделано?


<a id="org5b36df8"></a>

### regular insurance payments

[TODO:gmm] Тут надо делать периодический вызов? Как?


<a id="org78c98dd"></a>

# Objections


<a id="org994134f"></a>

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


<a id="org0d86621"></a>

## Send objection function

[TODO:gmm] send<sub>objection</sub> fun

[TODO:gmm] проверка не истекло ли время голосования

    # Starting vote process
    @external
    def send_objection():
        ...


<a id="org228686c"></a>

# Expiration of the voting period

[TODO:gmm] - Как я могу получить время, чтобы определить что
голосование пора завершать?

[TODO:gmm] - Если голосование завершено, то здесь нужен
event?

[TODO:gmm] - Подсчет возражений

[TODO:gmm] - Как мне запустить что-то по результатам?


<a id="org52dad47"></a>

## Objection threshold

[TODO:gmm] Нужен свой порог для каждого трека


<a id="org89231f3"></a>

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


<a id="org3893d3d"></a>

# Monitoring of voting

[TODO:gmm] - Как это делать?


<a id="org4fe5a1e"></a>

# Tangle

[TODO:gmm] - Общие вещи если надо


<a id="org07c3506"></a>

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


<a id="org255dfd6"></a>

## test for validator's requests contract

Это заготовки для тестов.

Когда я делаю тест я хочу:

-   развернуть изи-трек
-   создать голосование
-   закинуть возражение
-   завершить голосование (как ускорить его?)
-   посчитать результаты
-   убедиться, что посчитано верно
