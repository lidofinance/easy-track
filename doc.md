
# Table of Contents

1.  [Intro](#orga4de207)
    1.  [Tracks variants](#orgf86ba25)
2.  [Vote initiation](#org48b832f)
3.  [Минимальный порог возражений](#org44c97ba)



<a id="orga4de207"></a>

# Intro

Предложение считается принятым, если оно подано претендентом
с определенной ролью и не было получено никаких возражений.

Для каждого EasyTrack процесса существуют свои ограничения
на подачу предложений. В остальном, процесс практически
общий.


<a id="orgf86ba25"></a>

## Tracks variants

-   validators requests
-   grant distibution
-   payments of rewards
-   regular insurance payments


<a id="org48b832f"></a>

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


<a id="org44c97ba"></a>

# Минимальный порог возражений
