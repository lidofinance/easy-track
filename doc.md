
# Table of Contents

1.  [Intro](#org3414471)
2.  [Vote initiation](#org2e5a21c)
    1.  [Check credentials to start vote](#org56cd085)
        1.  [validator request](#org9b89274)
        2.  [grant distibution](#orgbb0478d)
        3.  [payments of rewards](#orge2476b1)
        4.  [regular insurance payments](#org56acb25)
3.  [Objections](#org163c915)
    1.  [Avoidance of malicious objections](#org43c4188)
    2.  [Send objection function](#orgad3c816)
4.  [Expiration of the voting period](#org8edb535)
    1.  [Objection threshold](#org4615de2)
5.  [Monitoring of voting](#org0c478ac)



<a id="org3414471"></a>

# Intro

Предложение считается принятым, если оно подано претендентом
с определенной ролью и не было получено никаких возражений.

Для каждого EasyTrack процесса существуют свои ограничения
на подачу предложений. В остальном, процесс практически
общий. Поэтому, чтобы сгенерировать все треки, я просто
скомпоную их из общих и специфичных фрагментов.

Tracks variants:

-   validators requests
-   grant distibution
-   payments of rewards
-   regular insurance payments


<a id="org2e5a21c"></a>

# Vote initiation

Чтобы начать голосование easy-track, необходимо вызвать
функцию start<sub>vote</sub>. Она в свою очередь вызовет `check_creds`
чтобы проверить, может ли `msg.sender` начинать голосование.

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
        check_creds()


<a id="org56cd085"></a>

## Check credentials to start vote

Для каждого трека способ проверки прав для начала
голосования свой


<a id="org9b89274"></a>

### validator request

Тот кто хочет начать голосование должен быть
валидатором. Допустим, мы ведем хеш-таблицу валидаторов,
тогда нужна роль, которая может добавлять и удалять
валидаторов и соответствующие функции

    # Defining a validator's map
    validators: HashMap[uint256, bool]

    # Check for validator
    @internal
    def check_creds():
        assert validators(msg.sender), "not a validator"

    # Defining a admins's map
    admins: HashMap[uint256, bool]

    # Init admins
    def init_admins():
        # assert TODO: только при старте, добавляем админа?

    # Add validator
    def add_validator(param):
        assert admins(msg.sender), "not a admin"
        validators[param] = true

    # Del validator
    def del_validator
        assert admins(msg.sender), "not a admin"
        validators[param] = false


<a id="orgbb0478d"></a>

### grant distibution

Голосование начинается, если удовлетворены требования
пороговой подписи K из N ([TODO:gmm]я пока не знаю как это
правильно написать)


<a id="orge2476b1"></a>

### payments of rewards

[TODO:gmm] Как я понимаю, эти пэйменты будет вызывать арагон-агент. Как
он будет это делать?


<a id="org56acb25"></a>

### regular insurance payments

[TODO:gmm] Тут надо делать периодический вызов?


<a id="org163c915"></a>

# Objections


<a id="org43c4188"></a>

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


<a id="orgad3c816"></a>

## Send objection function

[TODO:gmm] send<sub>objection</sub> fun

[TODO:gmm] проверка не истекло ли время голосования

    # Starting vote process
    @external
    def send_objection():


<a id="org8edb535"></a>

# Expiration of the voting period

[TODO:gmm] - Как я могу получить время, чтобы определить что
голосование пора завершать?

[TODO:gmm] - Если я завершил голосование, то здесь нужен
event?

[TODO:gmm] - Подсчет возражений

[TODO:gmm] - Как мне запустить что-то по результатам?


<a id="org4615de2"></a>

## Objection threshold

[TODO:gmm] Нужен свой порог для каждого трека


<a id="org0c478ac"></a>

# Monitoring of voting

[TODO:gmm] - Как это делать?
