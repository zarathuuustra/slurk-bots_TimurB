# -*- coding: utf-8 -*-

# University of Potsdam
"""Wordle bot logic including dialog and game phases."""

import logging
import os
import random
import string
from threading import Timer
from time import sleep

import requests
import socketio

from lib.image_data import ImageData
from lib.config import (
    COLOR_MESSAGE,
    DATA_PATH,
    GAME_MODE,
    N,
    PLATFORM,
    PROLIFIC_URL,
    PUBLIC,
    SEED,
    SHUFFLE,
    STANDARD_COLOR,
    TASK_GREETING,
    TASK_TITLE,
    TIME_LEFT,
    TIME_ROUND,
    TIME_WAITING,
    WARNING_COLOR,
    WORD_LIST,
)


LOG = logging.getLogger(__name__)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RoomTimers:
    """A number of timed events during the game.

    :param round_timer: After 15 minutes the image will change
        and players get no points
    """

    def __init__(self):
        self.left_room = dict()
        self.round_timer = None

    def cancel_all_timers(self):
        self.round_timer.cancel()
        for timer in self.left_room.values():
            timer.cancel()

    def user_joined(self, user):
        timer = self.left_room.get(user)
        if timer is not None:
            self.left_room[user].cancel()

    def user_left(self, user):
        self.left_room[user] = Timer(
            LEAVE_TIMER * 60, self.function, args=[self.room_id, "user_left"]
        )
        self.left_room[user].start()

    def start_round_timer(self, function, room_id):
        # cancel old timer if still running
        if isinstance(self.round_timer, Timer):
            self.round_timer.cancel()

        timer = Timer(TIME_ROUND * 60, function, args=[room_id])
        timer.start()
        self.round_timer = timer


class Session:
    def __init__(self):
        self.timer = RoomTimers()
        self.images = ImageData(DATA_PATH, N, GAME_MODE, SHUFFLE, SEED)
        self.players = list()
        self.guesses = dict()
        self.guesses_history = list()
        self.points = 0
        self.game_over = False

    def close(self):
        self.timer.cancel_all_timers()


class SessionManager(dict):
    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)


class WordleBot:
    sio = socketio.Client(logger=True)
    """The ID of the task the bot is involved in."""
    task_id = None
    """The ID of the room where users for this task are waiting."""
    waiting_room = None

    def __init__(self, token, user, host, port):
        """This bot allows two players to play wordle together

        :param token: A uuid; a string following the same pattern
            as `0c45b30f-d049-43d1-b80d-e3c3a3ca22a0`
        :type token: str
        :param user: ID of a `User` object that was created with
        the token.
        :type user: int
        :param uri: Full URL including protocol and hostname,
            followed by the assigned port if any.
        :type uri: str
        :param images_per_room: Each room is mapped to a list
            of pairs with two image urls. Each participant
            is presented exactly one image per pair and round.
        :type images_per_room: dict
        :param timers_per_room: Each room is mapped to
            an instance of RoomTimers.
        :type timers_per_room: dict
        :param players_per_room: Each room is mapped to a list of
            users. Each user is represented as a dict with the
            keys 'name', 'id', 'msg_n' and 'status'.
        :type players_per_room: dict
        :param guesses_per_room: each room is mapped to a current guess.
            this is used to make sure that both users sent the same
            guess for the current wordle, only so it is possible to
            advance in the game
        :type guesses_per_room: dict
        :param points_per_room: a dictionary that saves for each room
            the current point stand
        :type points_per_room: dict
        """
        self.token = token
        self.user = user

        self.uri = host
        if port is not None:
            self.uri += f":{port}"

        self.url = self.uri
        self.uri += "/slurk/api"

        self.sessions = SessionManager()

        self.public = PUBLIC
        self.data_collection = PLATFORM

        # maps number of guesses to points
        self.point_system = dict(zip([6, 5, 4, 3, 2, 1], [100, 50, 25, 10, 5, 1]))

        # read wordlist
        with open(WORD_LIST) as infile:
            self.wordlist = set((line.strip()) for line in infile)
        # ensure all the words from the initial image file are guessable
        with open(DATA_PATH) as infile:
            self.wordlist.update(line.split("\t")[0] for line in infile)

        self.waiting_timer = None
        self.received_waiting_token = set()

        LOG.info(f"Running wordle bot on {self.uri} with token {self.token}")
        # register all event handlers
        self.register_callbacks()

    def run(self):
        # establish a connection to the server
        self.sio.connect(
            self.uri,
            headers={"Authorization": f"Bearer {self.token}", "user": self.user},
            namespaces="/",
        )
        # wait until the connection with the server ends
        self.sio.wait()

    @staticmethod
    def request_feedback(response, action):
        if not response.ok:
            LOG.error(f"Could not {action}: {response.status_code}")
            response.raise_for_status()
        else:
            LOG.debug(f"Successfully did {action}.")

    def register_callbacks(self):
        @self.sio.event
        def new_task_room(data):
            """Triggered after a new task room is created.

            An example scenario would be that the concierge
            bot emitted a room_created event once enough
            users for a task have entered the waiting room.
            """
            room_id = data["room"]
            task_id = data["task"]

            LOG.debug(f"A new task room was created with id: {data['task']}")
            LOG.debug(f"This bot is looking for task id: {self.task_id}")

            if task_id is not None and task_id == self.task_id:
                for usr in data["users"]:
                    self.received_waiting_token.discard(usr["id"])

                # create image items for this room
                LOG.debug("Create data for the new task room...")
                LOG.debug(data)

                self.move_divider(room_id, 20, 80)

                self.sessions.create_session(room_id)

                # self.images_per_room.get_word_image_pairs(room_id)
                self._update_guessable_words(room_id)
                LOG.debug(self.sessions[room_id].images)
                self.sessions[room_id].players = []
                for usr in data["users"]:
                    self.sessions[room_id].players.append(
                        {**usr, "msg_n": 0, "status": "joined"}
                    )

                response = requests.post(
                    f"{self.uri}/users/{self.user}/rooms/{room_id}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "let wordle bot join room")

                logging.info(room_id)
                self.sio.emit(
                    "message_command",
                    {"command": {"command": "wordle_init"}, "room": room_id},
                )

                self.show_item(room_id)

                # begin timers
                self.sessions[room_id].timer.start_round_timer(
                    self.time_out_round, room_id
                )

                # show info to users
                self._update_score_info(room_id)

        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]

            mode_message = "In this game mode, "
            if GAME_MODE == "same":
                mode_message += "both of you see the same image."
            elif GAME_MODE == "different":
                mode_message += (
                    "each of you sees a different image. "
                    "Both images are connected to the same word."
                )
            else:
                mode_message += (
                    "only one of you sees the image and "
                    "needs to describe it to the other person."
                )

            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/mode",
                json={"text": mode_message},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            self.request_feedback(response, "add mode explanation")

            if room_id in self.sessions:
                # read out task greeting
                for line in TASK_GREETING:
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                color=STANDARD_COLOR, message=line
                            ),
                            "room": room_id,
                            "html": True,
                        },
                    )
                    sleep(0.5)

                self.sio.emit(
                    "text",
                    {
                        "message": COLOR_MESSAGE.format(
                            color=STANDARD_COLOR,
                            message=f"Let's start with the first "
                            f"of {self.sessions[room_id].images.n} images",
                        ),
                        "room": room_id,
                        "html": True,
                    },
                )

                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/text/instr_title",
                    json={"text": line},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "set task instruction title")

        @self.sio.event
        def status(data):
            """Triggered if a user enters or leaves a room."""
            # check whether the user is eligible to join this task
            task = requests.get(
                f"{self.uri}/users/{data['user']['id']}/task",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(task, "get task")
            if not task.json() or task.json()["id"] != int(self.task_id):
                return

            room_id = data["room"]
            # someone joined waiting room
            if room_id == self.waiting_room:
                if self.waiting_timer is not None:
                    LOG.debug("Waiting Timer stopped.")
                    self.waiting_timer.cancel()
                if data["type"] == "join":
                    LOG.debug("Waiting Timer restarted.")
                    self.waiting_timer = Timer(
                        TIME_WAITING * 60,
                        self._no_partner,
                        args=[room_id, data["user"]["id"]],
                        )
                    self.waiting_timer.start()
                    sleep(10)
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                color=STANDARD_COLOR,
                                message=f"If nobody shows up within "
                                        f"{TIME_WAITING} minutes, I will give "
                                        f"you a submission link, so that you "
                                        f"can get paid for your waiting time."
                            ),
                            "room": room_id,
                            "receiver_id": data['user']['id'],
                            "html": True,
                        },
                    )

        # some joined a task room
            elif room_id in self.sessions:
                curr_usr, other_usr = self.sessions[room_id].players
                if curr_usr["id"] != data["user"]["id"]:
                    curr_usr, other_usr = other_usr, curr_usr

                if data["type"] == "join":
                    # inform game partner about the rejoin event
                    if room_id in self.sessions:
                        if self.sessions[room_id].game_over is False:
                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        color=STANDARD_COLOR,
                                        message=f"{curr_usr['name']} has joined the game. ",
                                    ),
                                    "room": room_id,
                                    "receiver_id": other_usr["id"],
                                    "html": True,
                                },
                            )

                            # reset the front-end of the user who just joined
                            word, _, _ = self.sessions[room_id].images[0]
                            self.sio.emit(
                                "message_command",
                                {
                                    "command": {
                                        "command": "wordle_init",
                                    },
                                    "room": room_id,
                                    "receiver_id": curr_usr["id"],
                                },
                            )
                            self.show_item(room_id)

                            # enter all the guesses that this user sent to the bot
                            # to catch up with the other user
                            for guess in self.sessions[room_id].guesses_history:
                                self.sio.emit(
                                    "message_command",
                                    {
                                        "command": {
                                            "command": "wordle_guess",
                                            "guess": guess,
                                            "correct_word": word,
                                        },
                                        "room": room_id,
                                        "receiver_id": curr_usr["id"],
                                    },
                                )

                            # cancel timer
                            LOG.debug(
                                f"Cancelling Timer: left room for user {curr_usr['name']}"
                            )
                            self.sessions[room_id].timer.user_joined(curr_usr["id"])

                elif data["type"] == "leave":
                    # send a message to the user that was left alone
                    if room_id in self.sessions:
                        if self.sessions[room_id].game_over is False:
                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        color=STANDARD_COLOR,
                                        message=f"{curr_usr['name']} has left the game.",
                                    ),
                                    "room": room_id,
                                    "receiver_id": other_usr["id"],
                                    "html": True,
                                },
                            )

                            # close game, this user gets failure, other user success
                            self.sessions[room_id].game_over = True
                            self.end_game(
                                room_id,
                                {
                                    curr_usr["id"]: "disconnection",
                                    other_usr["id"]: "success",
                                },
                            )
                            sleep(1)
                            self.close_room(room_id)

        @self.sio.event
        def text_message(data):
            """Triggered once a text message is sent (no leading /).

            Count user text messages.
            If encountering something that looks like a command
            then pass it on to be parsed as such.
            """
            LOG.debug(f"Received a message from {data['user']['name']}.")
            room_id = data["room"]
            user_id = data["user"]["id"]

            # filter irrelevant messages
            if room_id not in self.sessions or user_id == self.user:
                return

            # if the message is part of the main discussion count it
            for usr in self.sessions[room_id].players:
                if usr["id"] == user_id and usr["status"] == "ready":
                    usr["msg_n"] += 1

        @self.sio.event
        def command(data):
            """Parse user commands."""
            LOG.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself
            if str(user_id) == self.user:
                return

            if room_id in self.sessions:
                # only accept commands from the javascript
                # frontend (commands are dictionaries)
                if isinstance(data["command"], dict):
                    if "guess" in data["command"]:
                        if data["command"]["guess"].strip() == "":
                            self.sio.emit(
                                "text",
                                {
                                    "message": COLOR_MESSAGE.format(
                                        color=WARNING_COLOR,
                                        message="**You need to provide a guess!**",
                                    ),
                                    "room": room_id,
                                    "receiver_id": user_id,
                                    "html": True,
                                },
                            )
                        else:
                            self._command_guess(room_id, user_id, data["command"])

                # bot has no user defined commands
                else:
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(
                                color=STANDARD_COLOR,
                                message="Sorry, but I do not understand this command.",
                            ),
                            "room": room_id,
                            "receiver_id": user_id,
                            "html": True,
                        },
                    )

    def move_divider(self, room_id, chat_area=50, task_area=50):
        """move the central divider and resize chat and task area
        the sum of char_area and task_area must sum up to 100
        """
        if chat_area + task_area != 100:
            LOG.error("Could not resize chat and task area: invalid parameters.")
            raise ValueError("chat_area and task_area must sum up to 100")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/sidebar",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"attribute": "style", "value": f"width: {task_area}%"},
        )
        self.request_feedback(response, "resize sidebar")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/content",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"attribute": "style", "value": f"width: {chat_area}%"},
        )
        self.request_feedback(response, "resize content area")

    def _command_guess(self, room_id, user_id, command):
        """Must be sent to end a game round."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr["id"] != user_id:
            curr_usr, other_usr = other_usr, curr_usr

        LOG.debug(command)

        # get the wordle for this room and the guess from the user
        word, _, _ = self.sessions[room_id].images[0]
        guess = command["guess"]
        remaining_guesses = command["remaining"]

        # make sure the guess has the right length
        if len(word) != len(guess):
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message=f"Unfortunately this word is not valid. "
                        f"Your guess needs to have {len(word)} letters.",
                    ),
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                    "html": True,
                },
            )
            self.sio.emit(
                "message_command",
                {
                    "command": {"command": "unsubmit"},
                    "room": room_id,
                    "receiver_id": curr_usr["id"],
                },
            )
            return

        # make sure it's a good guess
        if guess not in self.wordlist:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=WARNING_COLOR,
                        message="**Unfortunately this word is not valid. "
                        "Make sure that there aren't any typos**",
                    ),
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                    "html": True,
                },
            )
            self.sio.emit(
                "message_command",
                {
                    "command": {"command": "unsubmit"},
                    "room": room_id,
                    "receiver_id": curr_usr["id"],
                },
            )
            return

        # add the guess to the current guess_dictionary
        # guess_dictionary = {
        #     room_id : {user_id: guess, other_user_id: guess},
        #     ...
        # }
        old_guess = self.sessions[room_id].guesses.get(curr_usr["id"])
        if old_guess is not None:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=WARNING_COLOR,
                        message=(
                            f"**You already entered the guess: {old_guess}, "
                            "let's wait for your partner to also enter a guess.**"
                        ),
                    ),
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                    "html": True,
                },
            )
            return

        self.sessions[room_id].guesses[curr_usr["id"]] = guess

        # only one entry in dict, notify other user he should send a guess
        if len(self.sessions[room_id].guesses) == 1:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message="Let's wait for your partner to also enter a guess.",
                    ),
                    "receiver_id": curr_usr["id"],
                    "room": room_id,
                    "html": True,
                },
            )
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message="Your partner thinks that you have "
                        "found the right word. Enter your guess.",
                    ),
                    "receiver_id": other_usr["id"],
                    "room": room_id,
                    "html": True,
                },
            )
            return

        # 2 users sent different words, notify them
        if (len(self.sessions[room_id].guesses) == 2) and (
            len(set(self.sessions[room_id].guesses.values())) == 2
        ):
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message="You and your partner sent a different word, "
                        "please discuss and enter the same guess.",
                    ),
                    "room": room_id,
                    "html": True,
                },
            )
            self.sessions[room_id].guesses = dict()
            self.sio.emit(
                "message_command",
                {
                    "command": {"command": "unsubmit"},
                    "room": room_id,
                },
            )

            return

        # both users think they are done with the game
        # conditions: 2 users already sent their guess and it's the same word
        if (len(self.sessions[room_id].guesses) == 2) and (
            len(set(self.sessions[room_id].guesses.values())) == 1
        ):
            # reset guess and send it to client to check
            self.sessions[room_id].guesses = dict()
            self.sessions[room_id].guesses_history.append(guess)
            self.sio.emit(
                "message_command",
                {
                    "command": {
                        "command": "wordle_guess",
                        "guess": guess,
                        "correct_word": word,
                    },
                    "room": room_id,
                },
            )

            if (word == guess) or (remaining_guesses == 1):
                sleep(2)

                result = "LOST"
                points = 0

                if word == guess:
                    result = "WON"
                    points = self.point_system[int(remaining_guesses)]

                # update points for this room
                self.sessions[room_id].points += points

                # self.timers_per_room[room_id].done_timer.cancel()
                self.sio.emit(
                    "text",
                    {
                        "message": COLOR_MESSAGE.format(
                            color=STANDARD_COLOR,
                            message=(
                                f"**YOU {result}! For this round you get {points} points. "
                                f"Your total score is: {self.sessions[room_id].points}**"
                            ),
                        ),
                        "room": room_id,
                        "html": True,
                    },
                )

                self.next_round(room_id)

    def _update_score_info(self, room):
        response = requests.patch(
            f"{self.uri}/rooms/{room}/text/subtitle",
            json={
                "text": f"Your score is {self.sessions[room].points} – You have {len(self.sessions[room].images)} rounds to go."
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "update score")

    def _update_guessable_words(self, room_id):
        word_count_1 = len(self.wordlist)
        self.wordlist.update(pair[0] for pair in self.sessions[room_id].images)
        word_count_2 = len(self.wordlist)
        LOG.debug(f"Added {word_count_2-word_count_1} words to wordlist.")

    def next_round(self, room_id):
        """
        Load the next image and wordle and move to the next round if possible
        """
        self.sessions[room_id].images.pop(0)
        self.sessions[room_id].guesses_history = list()
        self.sessions[room_id].guesses = dict()

        # was this the last game round?
        if not self.sessions[room_id].images:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message="The game is over! Thank you for participating!",
                    ),
                    "room": room_id,
                    "html": True,
                },
            )
            self._update_score_info(room_id)
            sleep(1)

            # close the game, bot users get a success token
            curr_usr, other_usr = self.sessions[room_id].players
            self.sessions[room_id].game_over = True
            self.end_game(
                room_id, {curr_usr["id"]: "success", other_usr["id"]: "success"}
            )
            sleep(1)
            self.close_room(room_id)
        else:
            # load the next image
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        color=STANDARD_COLOR,
                        message=f"Ok, let's move on to the next round. "
                        f"{len(self.sessions[room_id].images)} rounds to go!",
                    ),
                    "room": room_id,
                    "html": True,
                },
            )

            self._update_score_info(room_id)
            sleep(2)
            self.sio.emit(
                "message_command",
                {"command": {"command": "wordle_init"}, "room": room_id},
            )

            # reset attributes for the new round
            for usr in self.sessions[room_id].players:
                usr["status"] = "ready"
                usr["msg_n"] = 0

            self.show_item(room_id)

            # restart next_round_timer
            self.sessions[room_id].timer.start_round_timer(self.time_out_round, room_id)

    def time_out_round(self, room_id):
        """
        function called by the round timer once the time is over.
        Inform the users that the time is up and move to the next round
        """
        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    color=WARNING_COLOR,
                    message="**Your time is up! Unfortunately you get no points for this round.**",
                ),
                "room": room_id,
                "html": True,
            },
        )
        self.next_round(room_id)

    def _no_partner(self, room_id, user_id):
        """Handle the situation that a participant waits in vain."""
        if user_id not in self.received_waiting_token:
            self.sio.emit(
                "text",
                {"message": "Unfortunately we could not find a partner for you!",
                 "room": room_id,
                 "receiver_id": user_id,
                },
            )
            # create token and send it to user
            self.confirmation_code(room_id, "no_partner", receiver_id=user_id)
            sleep(5)
            self.sio.emit(
                "text",
                {
                    "message": "You may also wait some more :)",
                    "room": room_id,
                    "receiver_id": user_id,
                },
            )
            # no need to cancel
            # the running out of this timer triggered this event
            self.waiting_timer = Timer(
                TIME_WAITING * 60, self._no_partner, args=[room_id, user_id]
            )
            self.waiting_timer.start()
            self.received_waiting_token.add(user_id)
        else:
            self.sio.emit(
                "text",
                {"message": "You won't be remunerated for further waiting time.",
                 "room": room_id,
                 "receiver_id": user_id,
                },
            )

    def show_item(self, room_id):
        """Update the image of the players."""
        LOG.debug("Update the image and task description of the players.")
        # guarantee fixed user order - necessary for update due to rejoin
        users = sorted(self.sessions[room_id].players, key=lambda x: x["id"])
        user_1 = users[0]
        user_2 = users[1]

        if self.sessions[room_id].images:
            word, image_1, image_2 = self.sessions[room_id].images[0]
            LOG.debug(f"{image_1}\n{image_2}")

            # show a different image to each user. one image can be None

            # remove image and description for both
            self._hide_image(room_id)
            self._hide_image_desc(room_id)

            # Player 1
            if image_1:
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/attribute/id/current-image",
                    json={
                        "attribute": "src",
                        "value": image_1,
                        "receiver_id": user_1["id"],
                    },
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "set image 1")
                # enable the image
                response = requests.delete(
                    f"{self.uri}/rooms/{room_id}/class/image-area",
                    json={"class": "dis-area", "receiver_id": user_1["id"]},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "enable image 1")

            else:
                # enable the explanatory text
                response = requests.delete(
                    f"{self.uri}/rooms/{room_id}/class/image-desc",
                    json={"class": "dis-area", "receiver_id": user_1["id"]},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "enable explanation")

            # Player 2
            if image_2:
                response = requests.patch(
                    f"{self.uri}/rooms/{room_id}/attribute/id/current-image",
                    json={
                        "attribute": "src",
                        "value": image_2,
                        "receiver_id": user_2["id"],
                    },
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "set image 2")
                # enable the image
                response = requests.delete(
                    f"{self.uri}/rooms/{room_id}/class/image-area",
                    json={"class": "dis-area", "receiver_id": user_2["id"]},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "enable image 2")
            else:
                # enable the explanatory text
                response = requests.delete(
                    f"{self.uri}/rooms/{room_id}/class/image-desc",
                    json={"class": "dis-area", "receiver_id": user_2["id"]},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "enable explanation")

            # the task for both users is the same - no special receiver
            response = requests.patch(
                f"{self.uri}/rooms/{room_id}/text/instr_title",
                json={"text": TASK_TITLE},
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "set task instruction title")

    def _hide_image(self, room_id):
        response = requests.post(
            f"{self.uri}/rooms/{room_id}/class/image-area",
            json={"class": "dis-area"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "hide image")

    def _hide_image_desc(self, room_id):
        response = requests.post(
            f"{self.uri}/rooms/{room_id}/class/image-desc",
            json={"class": "dis-area"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "hide description")

    def confirmation_code(self, room_id, status, receiver_id=None):
        """Generate AMT token that will be sent to each player."""
        kwargs = dict()
        # either only for one user or for both
        if receiver_id is not None:
            kwargs["receiver_id"] = receiver_id

        confirmation_token = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        # post confirmation token to logs
        response = requests.post(
            f"{self.uri}/logs",
            json={
                "event": "confirmation_log",
                "room_id": room_id,
                "data": {"status_txt": status, "confirmation_token": confirmation_token},
                **kwargs,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "post confirmation token to logs")

        if self.data_collection == "AMT":
            self._show_amt_token(room_id, receiver_id, confirmation_token)
        elif self.data_collection == "Prolific":
            self._show_prolific_link(room_id, receiver_id)

        self._hide_image(room_id)
        self._hide_image_desc(room_id)

        return confirmation_token

    def _show_prolific_link(self, room, receiver, token=None):

        if token is None:
            # use the username
            response = requests.get(
                f"{self.uri}/users/{receiver}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "get user")
            token = response.json().get("name", f"{room}–{receiver}")

        url = f"{PROLIFIC_URL}{token}"
        self.sio.emit(
            "text",
            {"message": f"Please return to <a href='{url}'>{url}</a> to complete your submission.",
             "room": room,
             "html": True,
             "receiver_id": receiver
             }
        )

    def _show_amt_token(self, room, receiver, token):
        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR,
                    message="Please enter the following token into "
                            "the field on the HIT webpage, and close "
                            "this browser window.",
                ),
                "room": room,
                "html": True,
                "receiver_id": receiver
            },
        )
        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR, message=f"Here's your token: {token}"
                ),
                "room": room,
                "html": True,
                "receiver_id": receiver
            },
        )

        # TODO: show token also in display area

    def social_media_post(self, room_id, this_user_id, other_user_name):
        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR,
                    message=(
                        "Please share the following text on social media: "
                        "I played slurdle and helped science! "
                        f"Together with {other_user_name}, "
                        f"I got {self.sessions[room_id].points} "
                        f"points for {self.sessions[room_id].images.n} puzzle(s). "
                        f"Play here: {self.url}. #slurdle"
                    ),
                ),
                "receiver_id": this_user_id,
                "room": room_id,
                "html": True,
            },
        )

    def end_game(self, room_id, user_dict):
        if self.public:
            curr_usr, other_usr = self.sessions[room_id].players
            self.social_media_post(room_id, curr_usr["id"], other_usr["name"])
            self.social_media_post(room_id, other_usr["id"], curr_usr["name"])
        else:
            for user_id, status in user_dict.items():
                self.confirmation_code(room_id, status, user_id)
                sleep(0.5)

    def close_room(self, room_id):
        self.sio.emit(
            "text",
            {
                "message": COLOR_MESSAGE.format(
                    color=STANDARD_COLOR,
                    message="This room is closing now.",
                ),
                "room": room_id,
                "html": True,
            },
        )

        self.room_to_read_only(room_id)

        # remove any task room specific objects
        self.sessions.clear_session(room_id)

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        # set room to read-only
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "set room to read_only")

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "set room to read_only")

        # remove user from room
        if room_id in self.sessions:
            for usr in self.sessions[room_id].players:
                response = requests.get(
                    f"{self.uri}/users/{usr['id']}",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "get user")
                etag = response.headers["ETag"]

                response = requests.delete(
                    f"{self.uri}/users/{usr['id']}/rooms/{room_id}",
                    headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
                )
                self.request_feedback(response, "remove user from task room")
