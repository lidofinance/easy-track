
# Table of Contents

1.  [Intro](#orgc68b402)
2.  [Vote initiation](#org4f8b48f)
    1.  [Check credentials to start vote](#org8ea0abc)
        1.  [validator request](#orgca9f4c8)
        2.  [grant distibution](#org6f1b27d)
        3.  [payments of rewards](#org0717429)
        4.  [regular insurance payments](#orgd7eeb5b)
3.  [Минимальный порог возражений](#orgee09699)



<a id="orgc68b402"></a>

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


<a id="org4f8b48f"></a>

# Vote initiation

Чтобы начать голосование easy-track, необходимо вызвать
функцию start<sub>vote</sub>. Она в свою очередь вызовет `check_creds`
чтобы проверить, может ли `msg.sender` начинать голосование.

`check_creds`-функции свои для каждого easy-track.

    # Starting vote process
    @external
    def start_vote():
        # Check
        check_creds()


<a id="org8ea0abc"></a>

## Check credentials to start vote

Для каждого трека способ проверки прав для начала
голосования свой


<a id="orgca9f4c8"></a>

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


<a id="org6f1b27d"></a>

### grant distibution

Голосование начинается, если удовлетворены требования
пороговой подписи K из N ([TODO:gmm]я пока не знаю как это
правильно написать)


<a id="org0717429"></a>

### payments of rewards

[TODO:gmm] Как я понимаю, эти пэйменты будет вызывать арагон-агент. Как
он будет это делать?


<a id="orgd7eeb5b"></a>

### regular insurance payments

[TODO:gmm] Тут надо делать периодический вызов?


<a id="orgee09699"></a>

# Минимальный порог возражений
