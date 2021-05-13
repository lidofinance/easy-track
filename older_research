
# Table of Contents

1.  [Intro](#orgcfa2117)
2.  [Init](#org2f2b0d0)
3.  [Ownership](#org79ec3c5)
4.  [Ballot Makers](#orgf0a41bc)
5.  [Ballot Time](#org8560c24)
6.  [Make Ballot](#org58316d8)
7.  [Make Ballot for Validators](#org0dc367a)
    1.  [Possible Attacks](#org5eaf6f7)
8.  [Send objection](#org3dfb9da)
9.  [Ballot](#org3bdc350)
10. [Ballot Endings](#orgeb29905)
11. [Other task and todoes](#org4364775)
12. [Tangle](#org455f525)
13. [Tests](#orga94f489)
    1.  [Common part - deploy and pass vote](#orgddd5ca3)
    2.  [Test example](#orgef2d784)
    3.  [Test plan](#org7cdf7f5)
        1.  [Dao-voting](#orgf26eaa5)
        2.  [Deploy Easy Track](#org96830c3)
        3.  [Send Objections](#orgecbb2a0)
        4.  [Finish Voting](#org0eca36d)
        5.  [Calculate results](#org5bb5fb1)
14. [Other](#orgc7e78d6)



<a id="orgcfa2117"></a>

# Intro

У нас есть 4 трека, каждый из них может одновременно вести
несколько голосований.

Я решил положить все настраиваемые параметры в структуру
голосования.

По сути треки отличаются только базовыми настройками этих
голосований. Мы можем сделать каждый трек отдельным
контрактом.

Для всех голосований предложение считается принятым, если до
его окончания не было получено достаточно возражений.

Tracks variants:

-   validators requests
-   grant distibution
-   payments of rewards
-   regular insurance payments


<a id="org2f2b0d0"></a>

# Init

Я предполагаю, что разворачивать контракты EasyTrack-ов
будет контракт голосования DAO - тогда он и будет owner-ом
всех EasyTrack-ов. [TODO:gmm] - Проверить это.

Только `owner` может добавлять `ballotMaker`-ов - адреса
тех, кто может начинать голосование.

Переменная для хранения `owner`-а

    owner: public(address)

При инициализации запоминаем, кто `owner`:

    self.owner = msg.sender


<a id="org79ec3c5"></a>

# Ownership

Проверка `onlyOwner`:

    assert msg.sender == self.owner

Надо уметь трансферить `owner`-а:

    @external
    def transferOwnership(_new_owner: address):
        assert msg.sender == self.owner
        self.owner = _new_owner

[NOTE:gmm] - Кому можно создавать трек - решает
ДАО. Овнершип контракта = арагон агент (c) Vasya


<a id="orgf0a41bc"></a>

# Ballot Makers

[TODO:gmm] - Для трека валидаторов нужна функция, которая
проверяет, что начинающий голосование, есть в Node Operator
Registry. Ее вызов заменит блок <a id="orge319883"></a>. См.
раздел [Ballot Endings](#orgeb29905)

Для остальных треков, мы определяем HashMap в котором лежат
адреса ballot<sub>makers</sub>, которые могут начинать
голосования. Вероятно, это адреса Gnosis Safe. Также
вероятно, что мы должны иметь возможность добавлять такие
адреса в трек и блокировать их. [TODO:gmm] - Проверить это.

    ballot_makers: public(HashMap[address, bool])

Проверка, что sender есть в `ballot maker`

    assert self.ballot_makers[msg.sender] == True

`Owner` может добавлять и удалять `ballot makers`:

    @external
    def add_ballot_maker(_param: address):
        assert msg.sender == self.owner
        self.ballot_makers[_param] = True

    @external
    def del_ballot_maker(_param: address):
        assert msg.sender == self.owner
        self.ballot_makers[_param] = False

[NOTE:gmm] - ACL тут не нужен пока (c) Vasya


<a id="org8560c24"></a>

# Ballot Time

Мы считаем голосование завершенным, если одно из условий
истинно:

-   текущее время блока больше чем значение поля deadline
-   вес возражений выше порога возражений

Для этого нам нужны соответствующие поля в структуре
голосования:

    deadline: uint256
    objections_total_weight: uint256

И функция, которая проверят, завершено ли голосование.

    @external
    def is_ballot_finished(_ballot_id: uint256) -> bool:
        if ( block.timestamp > self.ballots[_ballot_id].deadline ):
           return True
        if ( self.objections_threshold > self.ballots[_ballot_id].objections_total_weight ):
           return True
        return False

Для каждого трека может быть разное время голосования,
поэтому нужно поле для хранения установленного времени:

    ballot_time: public(uint256)

Будем инициализировать это поле при иницализации контракта:

    self.ballot_time = _ballot_time

из соответствующего параметра:

    _ballot_time: uint256,


<a id="org58316d8"></a>

# Make Ballot

Голосования нумеруются начиная с единицы, текущенной номер
хранится в соотвествующей переменной:

    next_ballot_index: public(uint256)

Она должна быть проинициализирована, когда контракт
создается:

    self.next_ballot_index = 1

[TODO:gmm] - Возможно нужно минимальное время между
попытками одного пользователя создать новое голосование?

[TODO:gmm] - Возможно при создании голосования надо как-то
определять код, который будет выполнен, если голосование
пройдет?

Функция создания голосования:

    @external
    def make_ballot(_ballotHash: bytes32):
        assert self.ballot_makers[msg.sender] == True
        self.ballots[self.next_ballot_index] = Ballot({
            deadline: block.timestamp + self.ballot_time,
            objections_total_weight: 0,
            ballot_maker: msg.sender,
            snapshot_block: block.number - 1
        })
        self.ballots[self.next_ballot_index].snapshot_block = block.number - 1
        log EasyTrackVoteStart(_ballotHash, self.next_ballot_index)
        self.next_ballot_index = self.next_ballot_index + 1

Для нее в структуре голосования нам нужны поля:

    ballot_maker: address

Так как мы эмитим событие, его надо объявить:

    event EasyTrackVoteStart:
      ballotHash: indexed(bytes32)
      ballotId: indexed(uint256)

[NOTE:gmm] - Vasya:

Нельзя, чтобы можно было заспамить голосование, т.е. чтобы
голосующим не хватило денег или внимания чтобы остановить
плохие предложения или их часть

Можно сделать один общий на всех счетчик, который позволяет
делать голосование раз в час, тогда их будет не
более 24. Конкретное число может настраиваться (как и длина
голосования). Можно разрешать голосование раз в 4 часа -
ничего не случиться, если подождать 4 часа для старта.

Голосующая мощность = балансу на момент Х.

Идею привязывать голосование к LDO-токенам не делаем (пока).
Это все можно вынести в "планы на будущее"


<a id="org0dc367a"></a>

# Make Ballot for Validators

[TODO:gmm] - Для validator's easy track мы хотим проверять,
что адрес, который создает голосование есть в Node Operator
Registry. См. строчку 273 в файле:
<https://github.com/lidofinance/lido-dao/blob/master/contracts/0.4.24/nos/NodeOperatorsRegistry.sol>

    require(msg.sender == operators[_operator_id].rewardAddress, "APP_AUTH_FAILED");

Тут мы должны будем передавать operator<sub>id</sub> в функцию
создания голосования. Мапа operators объявлена как internal,
но есть функция getNodeOperator которая view accessor для
этой мапы, и [TODO:gmm] - ее можно заюзать через интерфейс.

    modifier operatorExists(uint256 _id) {
        require(_id < getNodeOperatorsCount(), "NODE_OPERATOR_NOT_FOUND");
        _;
    }

    /**
     * @notice Returns the n-th node operator
     * @param _id Node Operator id
     * @param _fullInfo If true, name will be returned as well
     */
    function getNodeOperator(uint256 _id, bool _fullInfo) external view
        operatorExists(_id)
        returns
        (
         bool active,
         string name,
         address rewardAddress,
         uint64 stakingLimit,
         uint64 stoppedValidators,
         uint64 totalSigningKeys,
         uint64 usedSigningKeys
         )
    {
        NodeOperator storage operator = operators[_id];

        active = operator.active;
        name = _fullInfo ? operator.name : "";    // reading name is 2+ SLOADs
        rewardAddress = operator.rewardAddress;
        stakingLimit = operator.stakingLimit;
        stoppedValidators = operator.stoppedValidators;
        totalSigningKeys = operator.totalSigningKeys;
        usedSigningKeys = operator.usedSigningKeys;
    }


<a id="org5eaf6f7"></a>

## Possible Attacks

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
обязан совпадать с адресом на котором они держат
LDO-токены. Также, так как валидаторы добавляются `owner`-ом
то им не нужен минимальный стейк для создания голосования.

Таким образом, мы контролируем тех, кто создает голосование,
и если начинается спам - оперативно удаляем его. Поэтому
дополнительные механизмы связанные с LDO-токенами не
нужны. [TODO:gmm] - Но нужен механизм отмены спаммерских
голосований тогда.


<a id="org3dfb9da"></a>

# Send objection

Возможна атака, при которой возражающий может продать
проголосовавшие жетоны и сразу же купить новые, чтобы
проголосовать снова. Это не бесплатная атака, учитывая цену
газа. В случае ее реализации DAO переходит к полноценному
голосованию по всем вопросам. Мы считаем риск небольшим и
сейчас ничего не делаем с этой угрозой.

[NOTE:gmm] Vasya:

Атака с покупкой и продажей купируется историей про баланс
на момент Х

Чтобы сделать быстрый вариант возражений, можно сразу
отменять голосование если порог перейден, чтобы поменьше
писать в storage

Общий ID голосований возможно будет удобнее для мониторинга

[TODO:gmm] - Можно смотреть снапшот баланса токенов так:

    import "@aragon/minime/contracts/MiniMeToken.sol";
    uint64  snapshotBlock = getBlockNumber64() - 1;
    uint256 votingPower = token.totalSupplyAt(snapshotBlock);

Мы можем взять текущий блок минус один, и записать его в
структуру Ballot. Когда кто-то хочет проголосовать против,
мы можем узнать его баланс на момент этого блока и так
определить его power.

Нам потребуется импортировать интерфейс MiniMe token-а отсюда:
<https://github.com/aragon/minime/blob/master/contracts/MiniMeToken.sol>

    from vyper.interfaces import ERC20

    interface MiniMe:
      def balanceOfAt(_owner: address, _blockNumber: uint256) -> uint256: view

Нужна также переменная, где лежит адрес LDO-контракта

    TOKEN: constant(address) = 0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32

Тут будем хранить блок, на который считаем балансы

    snapshot_block: uint256

При создании голосования надо заполнить это поле:

    self.ballots[self.next_ballot_index].snapshot_block = block.number - 1

Проверка не истекло ли время голосования.

    assert block.timestamp < self.ballots[_ballot_idx].deadline

Порог возражений:

    objections_threshold: public(uint256)

Инициализация порога возражений в init

    _objections_threshold: uint256,

    self.objections_threshold = _objections_threshold

Проверка, достаточно ли уже возражений

    assert self.ballots[_ballot_idx].objections_total_weight < self.objections_threshold

Функция возражения, работает только до дедлайна и пока
возражений недостаточно:

[TODO:gmm] - Надо считать в процентах от totalSupplyAt но
это чуть дороже по газу. "Objections<sub>threshold</sub> должен быть в
процентах от voting power, а не абсолютное число. потому что
total voting power будет меняться во времени" (с) Sam

    @external
    def sendObjection(_ballot_idx: uint256):
        assert block.timestamp < self.ballots[_ballot_idx].deadline
        assert self.ballots[_ballot_idx].objections_total_weight < self.objections_threshold
        _voting_power: uint256 = MiniMe(TOKEN).balanceOfAt(msg.sender, self.ballots[_ballot_idx].snapshot_block)
        self.objections[_ballot_idx][msg.sender] = _voting_power
        self.ballots[_ballot_idx].objections_total_weight = _voting_power + self.ballots[_ballot_idx].objections_total_weight
        log Objection(msg.sender, _voting_power)

Мы не можем иметь мапу в структуре голосования, которая
хранит возражения, поэтому их придется хранить отдельнно в
storage переменной:

    objections: HashMap[uint256, HashMap[address, uint256]]

Не забудем объявить event:

    event Objection:
      sender: indexed(address)
      power: uint256

[TODO:gmm] Если нельзя иметь HashMap в структуре, то можно в
отдельной переменной сделать HashMap от HashMap-а

[TODO:gmm] Посмотреть что такое allowance и permit
(подписанные сообщения разрешающие тратить) в контексте
траты токенов. Где смотреть?

[TODO:gmm] Возможно айди голосования лучше сделать общим для
всех треков через наследование или базовый контракт - factory

[TODO:gmm] Внимательно прочесть MiniMi-контракт, объявить
его интерфейс, приводить к нему и заюзать


<a id="org3bdc350"></a>

# Ballot

Голосования лежат в мапе, где ключ - индекс голосования, а
значение - структура голосования:

    ballots: public(HashMap[uint256, Ballot])

    struct Ballot:
      deadline: uint256
      objections_total_weight: uint256
      ballot_maker: address
      snapshot_block: uint256


<a id="orgeb29905"></a>

# Ballot Endings

[TODO:gmm] - Таймаут между изи-треками

Считаем, что у нас есть функция, которую можно вызвать, и
она сработает, если время голосования прошло, а возражений
поступило недостаточно.

[TODO:gmm] - Как задавать эту функцию коссвенно? В новом
оракуле есть кусок, который позволяет зашивать произвольный
смарт-контракт и дергать его - посмотреть как это
сделано. Надо вызвать функцию, которая переведет деньги. В
LIDO DAO есть адреса арагоновских проксиков, в арагоне
написано как это работает (etherscan). CallData определяет
что именно дергать.  Посмотреть как у арагона это
сделано. Посмотреть что происходит при enacting голосования
арагона в LIDO DAO, и в код арагона на etherscan

    @external
    def ballotResult(_ballot_idx: uint256):
        assert block.timestamp > self.ballots[_ballot_idx].deadline
        assert self.ballots[_ballot_idx].objections_total_weight < self.objections_threshold
        log EnactBallot(_ballot_idx)

Если голосование завершено, то здесь нужен event:

    event EnactBallot:
      idx: indexed(uint256)

[NOTE:gmm] - Vasya:

Два варианта:

-   Простой способ - вызывать любую функцию от имени
    агента. Небезопасно, но просто можно стащить функцию из
    арагона и использовать ее (Forward&#x2026;) Но тогда нужен
    хороший мониторинг, который будет следить, алертить,
    кидать в телеграмм.
-   Сложный способ - ограничить возможности вызываемых функций
    (операторы могут только в ключи, гранты только переводить
    фонды и.т.п). Это интереснее.


<a id="org4364775"></a>

# Other task and todoes

[TODO:gmm] - Разобраться, как можно интегрироваться со
всеобщим голосованием DAO

Какой план на апгрейды с curve?

[TODO:gmm] - Как проводить экзекьющен чтобы отдельные треки
имели раздельные полномочия, acl

Говерментс (проблемы обговорили)

Upgradable не нужен. Вместо него сансетим изитрек и заводим
новый. Параметры однако может быть нуждаются в изменениях.

Но может и стоит.

Или можно сделать через паттерн "Делегат" - какую функцию
они могут вызвать чтобы проверить можно ли делать это
голосование.

Самая интересная часть, над которой можно думать.

[TODO:gmm] - В ldo-purchase-executor/script/deploy.py есть
функция deploy<sub>and</sub><sub>start</sub><sub>dao</sub><sub>vote</sub> надо посмотреть можно по
ней что-то понять. Там же есть про деплой контракта и как
проголосовать (отправить возражение) в dao<sub>voting.vote</sub>()
есть что-то, что, вероятно, поможет написать тесты.

[TODO:gmm] - Кроме покупки страховки команда Meter
выкатывала одно голосование за 4 разные вещи -
посмотреть. Можно оттуда скопипастить. Где этот код?

[TODO:gmm] - Как мне представиться контрактом голосования
DAO, чтобы протестить это? Как написать такой тест?

[TODO:gmm] regular insurance payments Тут надо делать вызов
вручную раз в полгода


<a id="org455f525"></a>

# Tangle

    # @version 0.2.8
    # @author Lido <info@lido.fi>
    # @licence MIT
    from vyper.interfaces import ERC20

    interface MiniMe:
      def balanceOfAt(_owner: address, _blockNumber: uint256) -> uint256: view

    event EasyTrackVoteStart:
      ballotHash: indexed(bytes32)
      ballotId: indexed(uint256)
    event Objection:
      sender: indexed(address)
      power: uint256
    event EnactBallot:
      idx: indexed(uint256)

    struct Ballot:
      deadline: uint256
      objections_total_weight: uint256
      ballot_maker: address
      snapshot_block: uint256

    owner: public(address)
    ballot_makers: public(HashMap[address, bool])
    ballot_time: public(uint256)
    next_ballot_index: public(uint256)
    TOKEN: constant(address) = 0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32
    objections_threshold: public(uint256)
    objections: HashMap[uint256, HashMap[address, uint256]]
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
        self.objections_threshold = _objections_threshold

    @external
    def transferOwnership(_new_owner: address):
        assert msg.sender == self.owner
        self.owner = _new_owner

    @external
    def add_ballot_maker(_param: address):
        assert msg.sender == self.owner
        self.ballot_makers[_param] = True

    @external
    def del_ballot_maker(_param: address):
        assert msg.sender == self.owner
        self.ballot_makers[_param] = False

    @external
    def make_ballot(_ballotHash: bytes32):
        assert self.ballot_makers[msg.sender] == True
        self.ballots[self.next_ballot_index] = Ballot({
            deadline: block.timestamp + self.ballot_time,
            objections_total_weight: 0,
            ballot_maker: msg.sender,
            snapshot_block: block.number - 1
        })
        self.ballots[self.next_ballot_index].snapshot_block = block.number - 1
        log EasyTrackVoteStart(_ballotHash, self.next_ballot_index)
        self.next_ballot_index = self.next_ballot_index + 1

    @external
    def is_ballot_finished(_ballot_id: uint256) -> bool:
        if ( block.timestamp > self.ballots[_ballot_id].deadline ):
           return True
        if ( self.objections_threshold > self.ballots[_ballot_id].objections_total_weight ):
           return True
        return False



    @external
    def sendObjection(_ballot_idx: uint256):
        assert block.timestamp < self.ballots[_ballot_idx].deadline
        assert self.ballots[_ballot_idx].objections_total_weight < self.objections_threshold
        _voting_power: uint256 = MiniMe(TOKEN).balanceOfAt(msg.sender, self.ballots[_ballot_idx].snapshot_block)
        self.objections[_ballot_idx][msg.sender] = _voting_power
        self.ballots[_ballot_idx].objections_total_weight = _voting_power + self.ballots[_ballot_idx].objections_total_weight
        log Objection(msg.sender, _voting_power)

    @external
    def ballotResult(_ballot_idx: uint256):
        assert block.timestamp > self.ballots[_ballot_idx].deadline
        assert self.ballots[_ballot_idx].objections_total_weight < self.objections_threshold
        log EnactBallot(_ballot_idx)


<a id="orga94f489"></a>

# Tests


<a id="orgddd5ca3"></a>

## Common part - deploy and pass vote

Когда я делаю тест я хочу в каждом тесте:

-   развернуть изи-трек
-   создать голосование
-   выполнить голосование

Для этого служит fixture
`deploy_executor_and_pass_easy_track_vote`, которая
возвращает лямбду. Эта лямбда будет вызвана в каждом
последующем тесте.

Так как fixture напоминает макрос, нужно, чтобы ее параметры
тоже были fixtures.

    @pytest.fixture(scope='module')
    def fx_ballot_maker(accounts):
      return accounts.at('0xAD4f7415407B83a081A0Bee22D05A8FDC18B42da', force=True)

    @pytest.fixture(scope='module')
    def fx_ballot_time():
      return 1

    @pytest.fixture(scope='module')
    def fx_objections_threshold():
      return 2

    @pytest.fixture(scope='module')
    def fx_stub():
      return True

    @pytest.fixture(scope='module')
    def deploy_executor_and_pass_easy_track_vote(
            fx_ballot_maker,
            fx_ballot_time,
            fx_objections_threshold,
            fx_stub
            ):
        def la_lambda():
          (executor, vote_id) = deploy_and_start_easy_track_vote(
              {'from': fx_ballot_maker}, # TODO: ACL
              ballot_maker=fx_ballot_maker,
              ballot_time=fx_ballot_time,
              objections_threshold=fx_objections_threshold,
              stub=fx_stub
          )
          print(f'vote id: {vote_id}')
          # TODO: определить аккаунты, которые будут голосовать
          # Wait for the vote to end
          chain.sleep(3 * 60 * 60 * 24)
          chain.mine()
          print(f'vote executed')
          # Ret
          return executor

        return la_lambda

Внутри возвращаемой лямбды вызывается функция
`deploy_and_start_easy_track_vote`, которая:

-   разворачивает easy<sub>track</sub>
-   добаляет ballot<sub>makers</sub>
-   создает голосование.

Она должна вернуть развернутый контракт и `vote-id`.

    def deploy_and_start_easy_track_vote(
            tx_params,
            ballot_maker,
            ballot_time,
            objections_threshold,
            stub
            ):
        # Deploy EasyTrack
        executor = ValidatorsVote.deploy(
            ballot_time,
            objections_threshold,
            stub,
            tx_params,
            )
        # Add BallotMaker
        executor.add_ballot_maker(ballot_maker, tx_params)
        tx = executor.make_ballot(
            1,
            tx_params
            )
        # Debug out
        tx.info()
        # Get vote_id
        vote_id = tx.events['EasyTrackVoteStart']['ballotId']
        # Ret
        return (executor, vote_id)


<a id="orgef2d784"></a>

## Test example

    import pytest
    from brownie import Wei, chain, reverts
    from brownie.network.state import Chain
    from brownie import accounts
    from brownie import ValidatorsVote

    def deploy_and_start_easy_track_vote(
            tx_params,
            ballot_maker,
            ballot_time,
            objections_threshold,
            stub
            ):
        # Deploy EasyTrack
        executor = ValidatorsVote.deploy(
            ballot_time,
            objections_threshold,
            stub,
            tx_params,
            )
        # Add BallotMaker
        executor.add_ballot_maker(ballot_maker, tx_params)
        tx = executor.make_ballot(
            1,
            tx_params
            )
        # Debug out
        tx.info()
        # Get vote_id
        vote_id = tx.events['EasyTrackVoteStart']['ballotId']
        # Ret
        return (executor, vote_id)

    @pytest.fixture(scope='module')
    def fx_ballot_maker(accounts):
      return accounts.at('0xAD4f7415407B83a081A0Bee22D05A8FDC18B42da', force=True)

    @pytest.fixture(scope='module')
    def fx_ballot_time():
      return 1

    @pytest.fixture(scope='module')
    def fx_objections_threshold():
      return 2

    @pytest.fixture(scope='module')
    def fx_stub():
      return True

    @pytest.fixture(scope='module')
    def deploy_executor_and_pass_easy_track_vote(
            fx_ballot_maker,
            fx_ballot_time,
            fx_objections_threshold,
            fx_stub
            ):
        def la_lambda():
          (executor, vote_id) = deploy_and_start_easy_track_vote(
              {'from': fx_ballot_maker}, # TODO: ACL
              ballot_maker=fx_ballot_maker,
              ballot_time=fx_ballot_time,
              objections_threshold=fx_objections_threshold,
              stub=fx_stub
          )
          print(f'vote id: {vote_id}')
          # TODO: определить аккаунты, которые будут голосовать
          # Wait for the vote to end
          chain.sleep(3 * 60 * 60 * 24)
          chain.mine()
          print(f'vote executed')
          # Ret
          return executor

        return la_lambda

    def test_example(deploy_executor_and_pass_easy_track_vote):
        print("DBG : test is running...")
        deploy_executor_and_pass_easy_track_vote()
        # Чтобы тест упал и я увидел отладочные сообщения
        # assert 0 == 1
        with reverts():
            accounts[0].transfer(accounts[1], "10 ether", gas_price=0)


<a id="org7cdf7f5"></a>

## Test plan

Нужны приемочные тесты (сценарии):


<a id="orgf26eaa5"></a>

### Dao-voting

Надо эмулировать DAO-voting в тестах, чтобы развернуть Easy
Track.

[TODO:gmm] - Я предполагаю что для DAO-голосования нужен
файл интерефейса, который я могу взять из
`ldo-purchase-executor/intrfaces`. Я его объявляю:

    # Lido DAO Vault (Agent) contract
    interface Vault:
        def deposit(_token: address, _value: uint256): payable

Я нашел соответствие ему в `interfaces/Agent.json`:

    ...
    {
        "constant": false,
        "inputs": [
            {
                "name": "_token",
                "type": "address"
            },
            {
                "name": "_value",
                "type": "uint256"
            }
        ],
        "name": "deposit",
        "outputs": [],
        "payable": true,
        "stateMutability": "payable",
        "type": "function"
    }
    ...

[TODO:gmm] - Не очень понять при чем тут `deposit`.

Вот так он вызывается:

    Vault(LIDO_DAO_VAULT).deposit(
        LIDO_DAO_VAULT_ETH_TOKEN,
        eth_cost,
        value=eth_cost
    )

[TODO:gmm] - Есть образец эмуляции дао-голосования в
`conftest`, который выглядит так (я не понимаю как он
работает).

Там есть:

-   промотка времени (chain.sleep):
-   обращение через интерфейс в фикстурах (как работает?)

    lido_dao_voting_address = '0x2e59A20f205bB85a89C53f1936454680651E618e'

    @pytest.fixture(scope='module')
    def dao_voting(interface):
        return interface.Voting(lido_dao_voting_address)

    # together these accounts hold 15% of LDO total supply
    ldo_holders = [
        '0x3e40d73eb977dc6a537af587d48316fee66e9c8c',
        '0xb8d83908aab38a159f3da47a59d84db8e1838712',
        '0xa2dfc431297aee387c05beef507e5335e684fbcd'
    ]

    for holder_addr in ldo_holders:
        print('voting from acct:', holder_addr)
        accounts[0].transfer(holder_addr, '0.1 ether')
        account = accounts.at(holder_addr, force=True)
        dao_voting.vote(vote_id, True, False, {'from': account})

    # wait for the vote to end
    chain.sleep(3 * 60 * 60 * 24)
    chain.mine()

    assert dao_voting.canExecute(vote_id)
    dao_voting.executeVote(vote_id, {'from': accounts[0]})

    print(f'vote executed')

    total_ldo_assignment = sum([ p[1] for p in ldo_purchasers ])
    assert ldo_token.balanceOf(executor) == total_ldo_assignment

    ldo_assign_role = dao_token_manager.ASSIGN_ROLE()
    assert dao_acl.hasPermission(executor, dao_token_manager, ldo_assign_role)

    return executor


<a id="org96830c3"></a>

### Deploy Easy Track

[TODO:gmm] - Как мне обращаиться к Node Operator Registry и
Gnosis Safe чтобы извлечь тех, кто может создавать Easy
Track Voting?

[TODO:gmm] - Как работает ACL и как я могу использовать это
для Easy Track?


<a id="orgecbb2a0"></a>

### Send Objections


<a id="org0eca36d"></a>

### Finish Voting


<a id="org5bb5fb1"></a>

### Calculate results


<a id="orgc7e78d6"></a>

# Other

-   Brownie сам качает нужную версию Vyper
-   Brownie имеет brownie-config, где можно указать архивную
    ноду для форкинга из майнета.
-   Можно прикинуться любым из адресов (как?)
-   Если в brownie console написать chain[-1] можно получить
    последний блок. Из консоли можно сделать
    ex=ContractName.deploy(&#x2026;)
-   Когда я хочу вызвать другой контракт, я объявляют
    интерфейс, потом беру адрес этого контракта, привожу его к
    интерфейсу и вызываю функцию контракта:
    MyIface(addr).func(..) Если в вызове есть типы данных,
    которые не поддерживаются в вайпер, то используем raw<sub>call</sub>
-   [TODO:gmm] Мне надо как-то получить Node Operator Registry в папку
    interfaces - сгенерировать ABI из исходного кода или взять
    на Etherscan
-   deploy<sub>and</sub><sub>start</sub><sub>dao</sub><sub>voting</sub> эмулирует голосование DAO
-   brownie run позволяет вызвать любой скрипт (например для
    деплоя)
-   brownie accounts list показывает аккаунты (см. доки)
-   администратор контракта (dao agent app) должен
    устанавливать список разрешенных адресов - например гносис
    сэйф, чтобы выполнять операции.
-   Есть репа stacking<sub>rewards</sub> где можно подстмотреть про
    время голосования на высоте блока и таймштампах. vyper
    current block time etc
-   Энактинг голосования смотреть в репке нового оракула
-   Перемотка времени - гугл brownie test time

Тут конфиг, в нем куски оставлены как пример фикстур
