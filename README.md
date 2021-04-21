
# Table of Contents

1.  [Intro](#org359d9a8)
2.  [Init](#org9842a3d)
3.  [Ownership](#orgecd16ed)
4.  [Ballot Makers](#org80926e1)
5.  [Ballot Time](#orgb5614c9)
6.  [Make Ballot](#org7ddfbba)
7.  [Send objection](#org218bcba)
8.  [Ballot](#orge0905d7)
9.  [Ballot Endings](#org9174c4d)
10. [Other task and todoes](#orge015254)
11. [Tangle](#org3dadba5)
12. [Tests](#org16132e2)



<a id="org359d9a8"></a>

# Intro

У нас есть 4 трека, каждый из них может одновременно вести
несколько голосований.

Я пока не придумал ничего лучше, чем положить все
настраиваемые параметры в структуру голосования.

По сути треки отличаются только базовыми настройками этих
голосований. Мы можем сделать их отдельными контрактами.

Для всех голосований предложение считается принятым, если до
его окончания не было получено достаточно возражений.

Tracks variants:

-   validators requests
-   grant distibution
-   payments of rewards
-   regular insurance payments


<a id="org9842a3d"></a>

# Init

Переменная для хранения `owner`-а

    owner: public(address)

При инициализации запоминаем, кто `owner`:

    self.owner = msg.sender

Init нужен чтобы определить, кто может добавлять тех, кому
разрешено начинать голосование. По идее, только контракт
всеобщего голосования DAO может сделать это. Но, насколько я
понял, мы избегаем апгрейда DAO-контрактов, поэтому пока
рулит всем `owner`.

[TODO:gmm] - Разобраться, как можно интегрироваться со
всеобщим голосованием DAO


<a id="orgecd16ed"></a>

# Ownership

Проверка `onlyOwner`:

    assert msg.sender = self.owner

Надо уметь трансферить `owner`-а:

    @external
    def transferOwnership(_new_owner: address):
        assert msg.sender = self.owner
        self.owner = _new_owner


<a id="org80926e1"></a>

# Ballot Makers

Только "узкий круг ограниченных людей" может начинать
голосования. Храним их в мапе:

    ballot_makers: public(HashMap[address, bool])

Проверка, что `ballot maker` относится к этому кругу людей:

    assert ballot_makers[msg.sender] = True

`Owner` может добавлять и удалять `ballot makers`:

    @external
    def add_ballot_maker(_param: address):
        assert msg.sender = self.owner
        ballot_makers[_param] = True

    @external
    def del_ballot_maker(_param: address):
        assert msg.sender = self.owner
        ballot_makers[_param] = False


<a id="orgb5614c9"></a>

# Ballot Time

Мы считаем голосование завершенным, если одно из условий

Мы считаем голосование завершенным, если одно из условий
истинно:

-   текущее время блока больше чем значение поля deadline
-   вес возражений выше порога возражений

Для этого нам нужны соответствующие поля в структуре
голосования:

    deadline: uint256
    objections_total_weight: uint256

И функция, которая проверят, завершено ли голосование

    @external
    def is_ballot_finished(_ballot_id: uint256):
        if ( block.timestamp > ballots[_ballot_id].deadline ):
           return True
        if ( objections_threshold > ballots[_ballot_id].objections_total_weight ):
           return True
        return False

Для разных треков может быть разное время голосования,
поэтому нужно поле для хранения установленного времени:

    ballot_time: public(uint256)

Будем инициализировать это поле при иницализации контракта:

    self.ballot_time = _ballot_time

из соответствующего параметра:

    _ballot_time: uint256,


<a id="org7ddfbba"></a>

# Make Ballot

Возможна атака, когда `ballot maker` создает много
голосований, в рассчете на то, у возражающих не хватит
стейка чтобы возразить по всем голосованиям и какая-то часть
голосований пройдет без возражений. Например, так можно
выводить деньги на грантовые программы. Даже если гранты
переводятся на мультисиг, это требует только договоренности
с владельцами мультисига, которые тоже могут иметь
заинтересованность в выводе денег.

Была идея, чтобы возможность создавать easy-track
голосования была как-то привязана к LDO-токенам.

Мы могли бы заблокировать токены двумя способами:

-   перевести их на контракт, и после окончания голосования
    дать возможность забрать
-   запретить их трансфер на время голосования, вызвав
    токен-менеджер (требует апгрейда токен-менеджера)

(Токен-менеджер - это контракт, который позволяет увидеть
сколько у адреса токенов, которые он пока не может
трансферить из-за вестинга. Смотреть тут:
<https://github.com/aragon/aragon-apps/tree/master/apps/token-manager/contracts>)

Мы не хотим апгрейдить токен-менеджер, т.к. это требует
много телодвижений с аудитом и вообще это непросто. Но если
мы захотим это делать, то можем включить нужный функционал в
другие изменения.

Еще один аспект, как минимум, по validator's easy-track:
адрес, на котором валидаторы хотят работать с изи-треком не
обязан совпадать с адресом на котором они держать
LDO-токены. Также, так как валидаторы добавляются `owner`-ом
то им не нужен минимальный стейк для создания голосования.

Таким образом, мы контролируем тех, кто создает голосование,
и если начинается спам - оперативно удаляем его. Поэтому
дополнительные механизмы связанные с LDO-токенами не
нужны. [TODO:gmm] - Но нужен механизм отмены спаммерских
голосований тогда.

Голосования нумеруются начиная с единицы, текущенной номер
хранится в соотвествующей переменной:

    next_ballot_index: public(uint256)

Она должна быть проинициализирована, когда контракт
создается:

    self.next_ballot_index = 1

[TODO:gmm] - Возможно нужно минимальное время между
попытками одного пользователя создать новое голосование?

Функция создания голосования:

    @public
    def make_ballot(_ballotHash: bytes32):
        assert ballot_makers[msg.sender] = True
        self.ballots[self.next_ballot_index] = Ballot({
            ballot_maker = msg.sender
            deadline = block.timestamp + self.ballot_time,
        })
        self.next_ballot_index = self.next_ballot_index + 1

Для нее в структуре голосования нам нужны поля:

    ballot_maker: address

[TODO:gmm] - Для validator's easy track мы хотим проверять,
что адрес, который создает голосование есть в Node Operator
Registry. См. строчку 273 в файле:
<https://github.com/lidofinance/lido-dao/blob/master/contracts/0.4.24/nos/NodeOperatorsRegistry.sol>

    require(msg.sender == operators[_operator_id].rewardAddress, "APP_AUTH_FAILED");

Тут мы должны будем передавать operator<sub>id</sub> в функцию
создания голосования. Мапа operators объявлена как internal,
но есть функция getNodeOperator которая view accessor для
этой мапы, и [TODO:gmm] - ее можно заюзать через интерфейс.


<a id="org218bcba"></a>

# Send objection

Возможна атака, при которой возражающий может продать
проголосовавшие жетоны и сразу же купить новые, чтобы
проголосовать снова. Это не бесплатная атака, учитывая цену
газа. В случае ее реализации DAO переходит к полноценному
голосованию по всем вопросам. Мы считаем риск небольшим и
сейчас ничего не делаем с этой угрозой.

[TODO:gmm] - Можно смотреть снапшот баланса токенов так:

    import "@aragon/minime/contracts/MiniMeToken.sol";
    uint64  snapshotBlock = getBlockNumber64() - 1;
    uint256 votingPower = token.totalSupplyAt(snapshotBlock);

Мы можем взять текущий блок минус один, и записать его в
структуру Ballot. Когда кто-то хочет проголосовать против,
мы можем узнать его баланс на момент этого блока и так
определить его power.

[TODO:gmm] - Нам потребуется импортировать MiniMe token (но
я не нашел как это сделать, нашел только ERC20):
<https://github.com/aragon/minime/blob/master/contracts/MiniMeToken.sol>

    from vyper.interfaces import ERC20

[TODO:gmm] - Потом, видимо надо объявить интерфейсы (нужен
balanceOfAt)

    interface ERC20:
      def balanceOfAt(_owner: address, _blockNumber: uint256) -> uint256: constant

Нужна также переменная, где лежит адрес LDO-контракта

    token: address(ERC20)

[TODO:gmm] - Не совсем верная инициализация интерфейса в
init-функции (пока не знаю адрес)

    ERC20(contract_address)

Тут будем хранить блок, на который считаем балансы

    snapshot_block: uint256

При инициализации надо заполнить это поле:

    self.snapshot_block = block.number - 1

Проверка не истекло ли время голосования.

    assert block.timestamp < self.ballots[_ballot_idx].deadline

Порог возражений:

    objections_threshold: public(uint256)

Инициализация порога возражений в init

    _objections_threshold: uint256,

    self.objections_threshold = _objections_threshold

Проверка, достаточно ли уже возражений

    assert self.ballots[_ballot_idx].objections_total < self.objections_threshold

Функция возражения, работает только до дедлайна и пока
возражений недостаточно:

[TODO:gmm] - Можем считать в процентах от totalSupplyAt но
это чуть дороже по газу

    @public
    def sendObjection(_ballot_idx: uint256):
        assert block.timestamp < self.ballots[_ballot_idx].deadline
        assert self.ballots[_ballot_idx].objections_total < self.objections_threshold
        _voting_power: uint256
        _voting_power = token.balanceOfAt( msg.sender, self.snapshot_block )
        self.ballots[_ballot_idx].objections[msg.sender] = _voting_power
        _total = self.ballots[_ballot_idx].objections_total_weight
        self.ballots[_ballot_idx].objections_total_weight = total + _voting_power
        log.Objection(msg.sender, power)

Нам нужно иметь мапу в структуре голосования, которая хранит
возражения:

    objections: HashMap(address, uint256)

Не забудем про event:

    log.Objection(msg.sender, power)

И объявим event:

    Objection: event({sender: indexed(address), power: uint256})

[TODO:gmm] SafeMath нужно как-то объявлять?

[TODO:gmm] Если нельзя иметь HashMap в структуре, то можно в
отдельной переменной сделать HashMap от HashMap-а

[TODO:gmm] Посмотреть что такое allowance и permit
(подписанные сообщения разрешающие тратить) в контексте
траты токенов

[TODO:gmm] Возможно айди голосования лучше сделать общим для
всех треков через наследование или базовый контракт - factory

[TODO:gmm] Внимательно прочесть MiniMi-контракт, объявить
его интерфейс, приводить к нему и заюзать


<a id="orge0905d7"></a>

# Ballot

Голосования лежат в мапе, где ключ - индекс голосования, а
значение - структура голосования:

    ballots: public(HashMap[uint256, Ballot])

    struct Ballot:
      deadline: uint256
      objections_total_weight: uint256
      ballot_maker: address
      snapshot_block: uint256
      objections: HashMap(address, uint256)


<a id="org9174c4d"></a>

# Ballot Endings

Считаем, что у нас есть функция, которую можно вызвать, и
она сработает, если время голосования прошло, а возражений
поступило недостаточно.

[TODO:gmm] - Как задавать эту функцию коссвенно? В новом
оракуле есть кусок, который позволяет зашивать проивольный
смарт-контракт и дергать его - посмотреть как это
сделано. Надо вызвать функцию, которая переведет
деньги. Читать как сделано в арагоне. В LIDO DAO есть адреса
арагоновских проксиков, в арагоне написано как это работает
(etherscan). CallData определяет что именно дергать. Также
посмотреть как у арагона это сделано? Посмотреть что
происходит при enacting голосования арагона в LIDO DAO, и в
код арагона на etherscan

    @external
    def ballotResult():
        assert block.timestamp > self.ballots[_name].deadline
        assert self.ballots[_ballot_idx].objections_total < self.objections_threshold
        some_action_stub()

[TODO:gmm] - Если голосование завершено, то здесь нужен
event


<a id="orge015254"></a>

# Other task and todoes

[TODO:gmm] - В ldo-purchase-executor/script/deploy.py есть
функция deploy<sub>and</sub><sub>start</sub><sub>dao</sub><sub>vote</sub> надо посмотреть можно по
ней что-то понять. Там же есть про деполой контракта и как
проголосовать (отправить возражение) в dao<sub>voting.vote</sub>()
есть что-то что вероятно поможет написать тесты.

[TODO:gmm] - Кроме покупки страховки команда Meter
выкатывала одно голосование за 4 разные вещи -
посмотреть. Можно оттуда скопипастить.

[TODO:gmm] - Как мне представиться контрактом голосования
DAO, чтобы протестить это? Как написать такой тест? Как-то
так?

    # Lido DAO Vote contract
    interface DaoVote:
        def someFunc(_someparam: someType):
        ...

[TODO:gmm] grant distibution - Голосование начинается, если
удовлетворены требования пороговой подписи K из N

[TODO:gmm] regular insurance payments Тут надо делать вызов
вручную раз в полгода

[TODO:gmm] - Upgradable contract?


<a id="org3dadba5"></a>

# Tangle

    # @version 0.2.8
    # @author Lido <info@lido.fi>
    # @licence MIT
    from vyper.interfaces import ERC20

    interface ERC20:
      def balanceOfAt(_owner: address, _blockNumber: uint256) -> uint256: constant

    Objection: event({sender: indexed(address), power: uint256})

    struct Ballot:
      deadline: uint256
      objections_total_weight: uint256
      ballot_maker: address
      snapshot_block: uint256
      objections: HashMap(address, uint256)

    owner: public(address)
    ballot_makers: public(HashMap[address, bool])
    ballot_time: public(uint256)
    next_ballot_index: public(uint256)
    token: address(ERC20)
    objections_threshold: public(uint256)
    ballots: public(HashMap[uint256, Ballot])

    @external
    def __init__(
        _ballot_time: uint256,
        _objections_threshold: uint256,
        _stub: bool
        ):
        self.owner = msg.sender
        self.ballot_time = _ballot_time
        self.next_ballot_index = 1
        ERC20(contract_address)
        self.snapshot_block = block.number - 1
        self.objections_threshold = _objections_threshold

    @external
    def transferOwnership(_new_owner: address):
        assert msg.sender = self.owner
        self.owner = _new_owner

    @external
    def add_ballot_maker(_param: address):
        assert msg.sender = self.owner
        ballot_makers[_param] = True

    @external
    def del_ballot_maker(_param: address):
        assert msg.sender = self.owner
        ballot_makers[_param] = False

    @public
    def make_ballot(_ballotHash: bytes32):
        assert ballot_makers[msg.sender] = True
        self.ballots[self.next_ballot_index] = Ballot({
            ballot_maker = msg.sender
            deadline = block.timestamp + self.ballot_time,
        })
        self.next_ballot_index = self.next_ballot_index + 1

    @external
    def is_ballot_finished(_ballot_id: uint256):
        if ( block.timestamp > ballots[_ballot_id].deadline ):
           return True
        if ( objections_threshold > ballots[_ballot_id].objections_total_weight ):
           return True
        return False



    @public
    def sendObjection(_ballot_idx: uint256):
        assert block.timestamp < self.ballots[_ballot_idx].deadline
        assert self.ballots[_ballot_idx].objections_total < self.objections_threshold
        _voting_power: uint256
        _voting_power = token.balanceOfAt( msg.sender, self.snapshot_block )
        self.ballots[_ballot_idx].objections[msg.sender] = _voting_power
        _total = self.ballots[_ballot_idx].objections_total_weight
        self.ballots[_ballot_idx].objections_total_weight = total + _voting_power
        log.Objection(msg.sender, power)

    @external
    def ballotResult():
        assert block.timestamp > self.ballots[_name].deadline
        assert self.ballots[_ballot_idx].objections_total < self.objections_threshold
        some_action_stub()


<a id="org16132e2"></a>

# Tests

Это заготовки для тестов.

Когда я делаю тест я хочу:

-   развернуть изи-трек
-   создать голосование
-   закинуть возражение
-   завершить голосование (как ускорить его?)
-   посчитать результаты
-   убедиться, что посчитано верно

Нужны приемочные тесты (сценарии):

-   что изи-трек разворачивается
-   что голосование создается
-   что голосование реагирует на возражения
-   что оно завершается (промотать время brownie test time
    прямо из теста)
