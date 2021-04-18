
# Table of Contents

1.  [Intro](#org843464a)
2.  [Init](#org6948586)
3.  [Ownership](#orgd56c6de)
4.  [Ballot Makers](#org387d29c)
5.  [Ballot Time](#org15e5993)
6.  [Ballot Stake](#org1de26a0)
7.  [Ballot](#orgb293de5)
8.  [Make Ballot](#orgc219762)
9.  [Send objection](#orgbe04726)
10. [Ballot Endings](#orgdb5756e)
11. [Other task and todoes](#org944542f)
12. [Tangle](#org891df24)
    1.  [validator's requests contract](#org7650e56)
    2.  [test for validator's requests contract](#org8b4ae83)



<a id="org843464a"></a>

# Intro

У нас есть 4 трека, каждый из них может одновременно вести
несколько голосований.

Я пока не придумал ничего лучше, чем положить все
настраиваемые параметры в структуру голосования.

По сути треки отличаются только базовыми настройками этих
голосований.

Для всех голосований Предложение считается принятым, если до
его окончания не было получено достаточно возражений.

Tracks variants:

-   validators requests
-   grant distibution
-   payments of rewards
-   regular insurance payments


<a id="org6948586"></a>

# Init

Переменная для хранения `owner`-а

    owner: public(address)

При инициализации запоминаем, кто `owner`:

    self.owner = msg.sender

[TODO:gmm] - Init нужен чтобы определить, кто может
добавлять тех, кому разрешено начинать голосование. По идее,
только контракт всеобщего голосования DAO может сделать это.


<a id="orgd56c6de"></a>

# Ownership

Мы можем проверять `onlyOwner`:

    assert msg.sender = self.owner

Надо уметь трансферить `owner`-а:

    @external
    def transferOwnership(_newOwner: address):
        assert msg.sender = self.owner
        self.owner = _newOwner


<a id="org387d29c"></a>

# Ballot Makers

Только "узкий круг ограниченных людей" может начинать
голосования. Храним их в мапе:

    ballotMakers: public(HashMap[address, bool])

Проверка, что начинающий голосование, относится к этому
кругу людей:

    assert ballotMakers[msg.sender] = True

`Owner` может добавлять и удалять `ballot makers`:

    @external
    def addBallotMaker(_param: address):
        assert msg.sender = self.owner
        ballotMakers[_param] = True

    @external
    def delBallotMaker(_param: address):
        assert msg.sender = self.owner
        ballotMakers[_param] = False


<a id="org15e5993"></a>

# Ballot Time

Для разных треков разное время, но пока так:

    ballotTime: public(timedelta)


<a id="org1de26a0"></a>

# Ballot Stake

Ballot maker мог бы спамить голосованиями, а учитывая что
они по умолчанию проходят, этого нельзя допускать.

Мы хотим, чтобы возможность создавать easy-track голосования
была как-то привязана к LDO-токенам. При этом, LDO-токены,
которые иницировали голосование, не должны иметь возможность
инициировать второе голосование, пока первое не закончилось.

Возможна атака, при которой возражающий может продать
проголосовавшие жетоны и сразу же купить новые, чтобы
проголосовать снова. Чтобы этого не произошло, в контракте
easy-track необходимо обратиться к менеджеру токенов, чтобы
запретить передачу этих токенов до конца голосования. Но это
вызывает проблемы с аудитом и обновлением LDO-контракта,
чего хочется избежать.

Можно использовать остатки на момент блока, в котором
началось голосование. То есть голосовать могут только
жетоны, которые не были перемещены с момента начала
голосования. Мне показалось это сложным в реализации.

Поэтому мы требуем замораживать токены в голосовании - когда
ballot maker начинает голосование, ему нужно приложить
токены, чтобы нельзя было создавать слишком много
голосований. Порог, ниже которого голосование не начнется:

    minBallotStake: public(decimal)

Проверка, что стейка достаточно для начала голосования. Тут
мы считаем, что порог общий для всех голосований во всех
треках.

    assert msg.value >= self.minBallotStake

[NOTE:gmm] - Возможна атака, когда `ballot maker` создает
много голосований, в рассчете на то, у возражающих не хватит
стейка чтобы возразить по всем голосованиям и какая-то часть
голосований пройдет без возражений. Например, так можно
вывести деньги на грантовые программы. Даже если гранты
переводятся на мультисиг, это требует только договоренности
с владельцами мультисига, которые тоже могут иметь
заинтересованность в выводе денег.


<a id="orgb293de5"></a>

# Ballot

Голосования лежат в мапе, где ключ - хэш голосования, а
значение - структура голосования:

    ballots: public(HashMap[string[255], Ballot])

    struct Ballot:
      name: string[255]
      ballotMaker: address
      ballotMakerStake: wei_value
      deadline: timestamp
      objections: HashMap(address, wei_value)
      objections_total: wei_value


<a id="orgc219762"></a>

# Make Ballot

Функция для начала голосования, после проверок создает
новый Ballot:

Проверка, нет ли уже такого голосования. Она нужна,
т.к. если не проверить, то новое голосование затрет
предыдущее.

    assert self.ballots[_name] = False

[VRFY:gmm] - Возможно нужно минимальное время между
попытками одного пользователя создать новое голосование?

Когда Ballot maker отдает нам свой стейк мы должны
запомнить, сколько он застейкал, чтобы потом разрешить ему
вернуть эту сумму.

    self.ballots[_name].ballotMakerStake = msg.value

После окончания голосования, нужно разрешать вернуть стейк
ballotMaker-у, но только всю сумму разом и только один раз.

    @external
    def withdrawBallotStake(_name: string[255]):
        assert self.ballots[_name].active = False
        assert self.ballots[_name].ballotMakerStake > 0
        _ballotMaker = self.ballots[_name].ballotMaker
        _amount: wei_value = self.ballots[_name].ballotMakerStake
        self.ballots[_name].ballotMakerStake = 0
        send(_ballotMaker, _amount)

Функция создания голосования:

    @public
    @payable
    def make_ballot(_name: string[255]):
        assert ballotMakers[msg.sender] = True
        assert msg.value >= self.minBallotStake
        assert self.ballots[_name] = False
        self.ballots[_name] = Ballot({
            name = _name,
            active = True,
            ballotMaker = msg.sender
            deadline = block.timestamp + self.ballotTime,
            result = True
        })
        self.ballots[_name].ballotMakerStake = msg.value


<a id="orgbe04726"></a>

# Send objection

Проверка не истекло ли время голосования.

    assert block.timestamp < self.ballots[_name].deadline

Порог возражений:

    objections_threshold: public(wei_value)

Проверка, достаточно ли уже возражений

    assert self.ballots[_name].objections_total < self.objections_threshold

Функция возражения, работает только до дедлайна и пока
возражений недостаточно:

    @public
    @payable
    def sendObjection(_name: string[266]):
        assert block.timestamp < self.ballots[_name].deadline
        assert self.ballots[_name].objections_total < self.objections_threshold
        self.ballots[_name].objections[msg.sender] = msg.value
        _total = self.ballots[_name].objections_total
        self.ballots[_name].objections_total = total + msg.value


<a id="orgdb5756e"></a>

# Ballot Endings

Считаем, что у нас есть функция, которую можно вызвать, и
она сработает, если время голосования прошло, а возражений
поступило недостаточно.

[TODO:gmm] - Как задавать эту функцию коссвенно? В новом
оракуле есть кусок, который позволяет зашивать проивольный
смарт-контракт и дергать его - посмотреть как это
сделано. Надо вызвать функцию, которая переведет
деньги. Читать как сделано в арагоне. В lido dao есть адреса
арагоновских проксиков, в арагоне написано как это работает
(etherscan) CallData определяет что именно дергать. Также
посмотреть как у арагона это сделано? Посмотреть что
происходит при enacting голосования арагона в lido DAO, код
арагона на etherscan

    @external
    def ballotResult()
        assert block.timestamp > self.ballots[_name].deadline
        assert self.ballots[_name].objections_total < self.objections_threshold
        some_action_stub()

[TODO:gmm] - Если голосование завершено, то здесь нужен
event


<a id="org944542f"></a>

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
        def someFunc(_someparam: someType): payable
        ...

[TODO:gmm] grant distibution - Голосование начинается, если
удовлетворены требования пороговой подписи K из N

[TODO:gmm] regular insurance payments Тут надо делать вызов
вручную раз в полгода


<a id="org891df24"></a>

# Tangle


<a id="org7650e56"></a>

## validator's requests contract

Сделаем генерацию контракта для validator's requests

    # @version 0.2.8
    # @author Lido <info@lido.fi>
    # @licence MIT
    from vyper.interfaces import ERC20

    struct Ballot:
      name: string[255]
      ballotMaker: address
      ballotMakerStake: wei_value
      deadline: timestamp
      objections: HashMap(address, wei_value)
      objections_total: wei_value

    owner: public(address)
    ballotMakers: public(HashMap[address, bool])
    ballotTime: public(timedelta)
    minBallotStake: public(decimal)
    ballots: public(HashMap[string[255], Ballot])
    objections_threshold: public(wei_value)

    @external
    def __init__():
        self.owner = msg.sender

    @external
    def transferOwnership(_newOwner: address):
        assert msg.sender = self.owner
        self.owner = _newOwner

    @external
    def addBallotMaker(_param: address):
        assert msg.sender = self.owner
        ballotMakers[_param] = True

    @external
    def delBallotMaker(_param: address):
        assert msg.sender = self.owner
        ballotMakers[_param] = False

    @public
    @payable
    def make_ballot(_name: string[255]):
        assert ballotMakers[msg.sender] = True
        assert msg.value >= self.minBallotStake
        assert self.ballots[_name] = False
        self.ballots[_name] = Ballot({
            name = _name,
            active = True,
            ballotMaker = msg.sender
            deadline = block.timestamp + self.ballotTime,
            result = True
        })
        self.ballots[_name].ballotMakerStake = msg.value

    @external
    def withdrawBallotStake(_name: string[255]):
        assert self.ballots[_name].active = False
        assert self.ballots[_name].ballotMakerStake > 0
        _ballotMaker = self.ballots[_name].ballotMaker
        _amount: wei_value = self.ballots[_name].ballotMakerStake
        self.ballots[_name].ballotMakerStake = 0
        send(_ballotMaker, _amount)

    @public
    @payable
    def sendObjection(_name: string[266]):
        assert block.timestamp < self.ballots[_name].deadline
        assert self.ballots[_name].objections_total < self.objections_threshold
        self.ballots[_name].objections[msg.sender] = msg.value
        _total = self.ballots[_name].objections_total
        self.ballots[_name].objections_total = total + msg.value

    @external
    def ballotResult()
        assert block.timestamp > self.ballots[_name].deadline
        assert self.ballots[_name].objections_total < self.objections_threshold
        some_action_stub()


<a id="org8b4ae83"></a>

## test for validator's requests contract

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
