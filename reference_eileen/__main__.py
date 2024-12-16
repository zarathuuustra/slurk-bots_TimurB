import logging
import os
import string
import random
from time import sleep
from threading import Timer, Lock
import requests
# deleted the re
from templates import TaskBot

from reference_eileen.config import (
    EXPLAINER_NEW_3DS,
    GUESSER_NEW_3DS,
    EXPLAINER_NEW_TUNA,
    GUESSER_NEW_TUNA,
    EXPLAINER_NEW_MIXED,
    GUESSER_NEW_MIXED,
    INSTANCES, # PICS_JSON
    TASK_GREETING,
    COLOR_MESSAGE,
    STANDARD_COLOR,
    WARNING_COLOR,
    TIMEOUT_TIMER,
    LEAVE_TIMER,
    WAITING_ROOM_TIMER,
    INPUT_FIELD_UNRESP_GUESSER,
    INPUT_FIELD_UNRESP_EXPLAINER,
    PICTURE_DIC,
)
from reference_eileen.dataloader import NewLoader

LOG = logging.getLogger(__name__)

class RoomTimer:
    """ Timer functions"""
    def __init__(self, function, room_id):
        self.function = function
        self.room_id = room_id
        self.start_timer()
        self.left_room = dict()

    def start_timer(self):
        self.timer = Timer(
            TIMEOUT_TIMER * 60, self.function, args=[self.room_id, "timeout"]
        )
        self.timer.start()

    def reset(self):
        self.timer.cancel()
        self.start_timer()
        logging.info("reset timer")

    def cancel(self):
        self.timer.cancel()

    def cancel_all_timers(self):
        self.timer.cancel()
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

class Session:
    "Session variables and close function"
    def __init__(self):
        self.players = list()
        self.grids = NewLoader(INSTANCES)
        self.guesser = None
        self.explainer = None
        self.points = {
            "score": 0,
            "history": [{"correct": 0, "wrong": 0, "warnings": 0}],
        }
        self.game_over = False
        self.timer = None
        self.turn = 0
        self.maxturn = 0
        self.target_pos = 0
        self.button_number = 0
        # to make sure parallel processes of closing game do not interfere
        self.lock = Lock()

    def close(self):
        self.timer.cancel_all_timers()


class SessionManager(dict):
    "Session Manager and its functions"
    waiting_room_timers = dict()

    def create_session(self, room_id):
        self[room_id] = Session()

    def clear_session(self, room_id):
        if room_id in self:
            self[room_id].close()
            self.pop(room_id)


class ReferenceBot(TaskBot):
    "The Reference Bot and its functions"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.received_waiting_token = set()
        self.sessions = SessionManager()

    def post_init(self, waiting_room):
        """
        save extra variables after the __init__() method has been called
        and create the init_base_dict: a dictionary containing
        needed arguments for the init event to send to the JS frontend
        """
        self.waiting_room = waiting_room

    def on_task_room_creation(self, data):
        """This function is executed as soon as 2 users are paired and a new
        task took is created
        """
        room_id = data["room"]
        task_id = data["task"]
        logging.debug(f"A new task room was created with id: {data['room']}")
        logging.debug(f"A new task room was created with task id: {data['task']}")
        logging.debug(f"This bot is looking for task id: {self.task_id}")

        if task_id is not None and task_id == self.task_id:
            # modify layout
            for usr in data["users"]:
                self.received_waiting_token.discard(usr["id"])
            logging.debug("Create data for the new task room...")

            self.move_divider(room_id, 20, 80)

            self.sessions.create_session(room_id)

            for usr in data["users"]:
                self.sessions[room_id].players.append(
                    {**usr, "msg_n": 0, "status": "joined"}
                )
            for usr in data["users"]:
                # cancel waiting-room-timers
                if usr["id"] in self.sessions.waiting_room_timers:
                    logging.debug(f"Cancelling waiting room timer for user {usr['id']}")
                    self.sessions.waiting_room_timers[usr["id"]].cancel()
                    self.sessions.waiting_room_timers.pop(usr["id"])

            timer = RoomTimer(self.timeout_close_game, room_id)
            self.sessions[room_id].timer = timer

            # join the newly created room
            response = requests.post(
                f"{self.uri}/users/{self.user}/rooms/{room_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.request_feedback(response, "letting task bot join room")
            logging.debug(f"Request URL: {self.uri}/users/{self.user}/rooms/{room_id}")
            logging.debug(f"Response status: {response.status_code}")
            logging.debug(f"Response body: {response.text}")

            # 2) Choose an explainer/guesser
            self.assign_roles(room_id)
            game_name = self.sessions[room_id].grids.data["GameName"]
            self.log_event("game_name", {"content": f"{game_name}"}, room_id)
            logging.debug(f"This is the game name: {game_name}")
            if game_name == "mixed":
                self.sessions[room_id].maxturn = 6
            elif game_name == "3ds":
                self.sessions[room_id].maxturn = 9
            elif game_name == "tuna":
                self.sessions[room_id].maxturn = 9
            logging.debug(f"Maximum amount of turns = {self.sessions[room_id].maxturn}")

            # send_instructions
            for player in self.sessions[room_id].players:
                self.send_instr(room_id, player["id"], game_name)
            
            # So the explainer can send messages: 
            self.set_message_privilege(room_id, self.sessions[room_id].explainer, False) 
            self.make_input_field_unresponsive(
                room_id, self.sessions[room_id].explainer
            )

            self.set_message_privilege(room_id, self.sessions[room_id].guesser, False)
            self.make_input_field_unresponsive(room_id, self.sessions[room_id].guesser)

    def assign_roles(self, room_id):
        """This function assigns roles to the players: explainer and guesser
        """
        experiment_id = self.sessions[room_id].grids.data[f"Experiment_Id"]
        logging.debug(f"This is the experiment_id: {experiment_id}")
        self.log_event("Experiment_Id", {"content": f"{experiment_id}"}, room_id)
        # assuming there are 2 players
        session = self.sessions[room_id]

        guesser_index = random.randint(0, len(session.players) - 1)
        explainer_index = 1 - guesser_index
        
        # Set the explainer
        session.players[explainer_index]["role"] = "explainer"
        session.explainer = session.players[explainer_index]["id"]
        self.log_event("player", session.players[explainer_index], room_id)
        
        # Set the guesser
        session.players[guesser_index]["role"] = "guesser"
        session.guesser = session.players[guesser_index]["id"]
        self.log_event("player", session.players[guesser_index], room_id)

    def register_callbacks(self):
        @self.sio.event
        def joined_room(data):
            """Triggered once after the bot joins a room."""
            room_id = data["room"]
            if room_id in self.sessions:
                for line in TASK_GREETING:
                    self.sio.emit(
                        "text",
                        {
                            "message": COLOR_MESSAGE.format(color="#800080", message=line),
                            "room": room_id,
                            "html": True,
                        },
                    )
                sleep(1)

                self.send_message_to_user(
                    STANDARD_COLOR,
                    "Are you ready?"
                    " Once you click on 'yes' you will see the images. <br> <br>"
                    "<button class='message_button' onclick=\"confirm_ready('yes')\">YES</button> "
                    "<button class='message_button' onclick=\"confirm_ready('no')\">NO</button>",
                    room_id,
                )
        @self.sio.event
        def status(data):
            """Triggered when a user enters or leaves a room."""
            room_id = data["room"]
            event = data["type"]
            user = data["user"]
            user_id = data["user"]["id"]

            # check whether the user is eligible to join this task
            task = requests.get(
                f"{self.uri}/users/{user['id']}/task",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            if not task.ok:
                logging.error(
                    f"Could not set task instruction title: {task.status_code}"
                )
                task.raise_for_status()
            if not task.json() or task.json()["id"] != int(self.task_id):
                return

            # someone joined waiting room
            if room_id == self.waiting_room:
                if event == "join":
                    if user["id"] not in self.sessions.waiting_room_timers:
                        # start no_partner timer
                        timer = Timer(
                            WAITING_ROOM_TIMER * 60,
                            self.timeout_waiting_room,
                            args=[user],
                        )
                        timer.start()
                        logging.debug(
                            f"Started a waiting room/no partner timer: {WAITING_ROOM_TIMER}"
                        )
                        self.sessions.waiting_room_timers[user["id"]] = timer
                return

            elif room_id in self.sessions:
                this_session = self.sessions[room_id]
                curr_usr, other_usr = this_session.players # -> The current user and the other user are from the class session and a type of player
                if curr_usr["id"] != data["user"]["id"]:
                    curr_usr, other_usr = other_usr, curr_usr
                # someone joined a task room
                if event == "join":
                    # inform everyone about the join event
                    self.send_message_to_user(
                        STANDARD_COLOR,
                        f"{user['name']} has joined the game.",
                        room_id,
                        other_usr["id"],
                    )

                    # user joined
                    self.sessions[room_id].timer.user_joined(curr_usr["id"])

                    # cancel timer
                    logging.debug(
                        f"Cancelling Timer: left room for user {curr_usr['id']}"
                    )
                    timer = this_session.timer.left_room.get(curr_usr["id"])
                    if timer is not None:
                        timer.cancel()

                    # reload game after user reconnected
                    if (
                        self.sessions[room_id].guesser is not None
                        and self.sessions[room_id].explainer is not None
                    ):
                        if (curr_usr["status"] != "ready" or other_usr["status"] != "ready"):
                            LOG.debug("RELOAD ONLY INSTR")
                            self.send_instr(room_id, curr_usr["id"], self.sessions[room_id].grids.data["GameName"])
                        else:
                            LOG.debug("RESTART ROUND")
                            self.reload_state(room_id, curr_usr["id"], self.sessions[room_id].grids.data["GameName"])

                elif event == "leave":
                    if self.sessions[room_id].game_over is False:
                        self.send_message_to_user(
                            STANDARD_COLOR,
                            f"{user['name']} has left the game. "
                            f"Please wait a bit, your partner may rejoin.",
                            room_id,
                            other_usr["id"],
                        )

                        # start timer since user left the room
                        logging.debug(
                            f"Starting Timer: left room for user {curr_usr['id']}"
                        )
                        self.sessions[room_id].timer.user_left(curr_usr["id"])

        @self.sio.event
        def text_message(data):
            """Parse user messages."""
            room_id = data["room"]
            user_id = data["user"]["id"]

            if room_id not in self.sessions or user_id == self.user:
                return
            # LOG.debug(f"{user_id, type(user_id)}, {self.user, type(self.user)}")
            LOG.debug(f"Received a message from {data['user']['name']}.")
            this_session = self.sessions[room_id]
            this_session.timer.reset()

            if this_session.explainer == user_id:
                # EXPLAINER sent the command
                self.log_event("clue", {"content": data["message"]}, room_id)

                self.set_message_privilege(
                    room_id, self.sessions[room_id].explainer, False
                )
                self.make_input_field_unresponsive(
                    room_id, self.sessions[room_id].explainer
                )

                LOG.debug(f"Button{this_session.button_number}")
                self.send_message_to_user(
                    STANDARD_COLOR,
                    f" Click on the number of the image the description above matches. <br> <br>"
                    f"<button class='message_button' id='Button{this_session.button_number}' onclick=\"choose_grid('1')\">1</button> "
                    f"<button class='message_button' id='Button{this_session.button_number + 1}' onclick=\"choose_grid('2')\">2</button> "
                    f"<button class='message_button' id='Button{this_session.button_number + 2}' onclick=\"choose_grid('3')\">3</button> " 
                    f"<button class='message_button' id='Button{this_session.button_number + 3}' onclick=\"choose_grid('4')\">4</button>",
                    room_id,
                    this_session.guesser,
                )

        @self.sio.event
        def command(data):
            """Parse user commands."""
            room_id = data["room"]
            user_id = data["user"]["id"]

            # do not process commands from itself/make sure session exists
            if room_id not in self.sessions or user_id == self.user:
                return

            logging.debug(
                f"Received a command from {data['user']['name']}: {data['command']}"
            )

            self.sessions[room_id].timer.reset()

            if isinstance(data["command"], dict):
                # commands from interface
                event = data["command"]["event"]
                if event == "confirm_ready":
                    if data["command"]["answer"] == "yes":
                        self._command_ready(room_id, user_id)
                    elif data["command"]["answer"] == "no":
                        self.send_message_to_user(
                            STANDARD_COLOR,
                            "OK, read the instructions carefully and click on <yes> once you are ready.",
                            room_id,
                            user_id,
                        )
                    return
                elif event == "choose_grid":
                    LOG.debug(f"{self.sessions[room_id].button_number}")
                    LOG.debug(f"Button{self.sessions[room_id].button_number}")
                    self.send_message_to_user(
                        STANDARD_COLOR,
                        f"Guess was submitted. You can not change it."
                        f"<script> document.getElementById('Button{self.sessions[room_id].button_number}').disabled = true;</script>"
                        f"<script> document.getElementById('Button{self.sessions[room_id].button_number + 1}').disabled = true;</script>"
                        f"<script> document.getElementById('Button{self.sessions[room_id].button_number + 2}').disabled = true;</script>"
                        f"<script> document.getElementById('Button{self.sessions[room_id].button_number + 3}').disabled = true;</script>",
                        room_id,
                        self.sessions[room_id].guesser,
                    )
                    guess = data["command"]["answer"] # The saved guess of the guesser
                    LOG.debug(f"The COOOOMAND was {data['command']}")
                    LOG.debug(f"GUESS was {guess}")

                    self.log_event("guess", {"content": guess}, room_id)

                    guess_correct = correct_guess(self, room_id, self.sessions[room_id].turn, guess)
                    if guess_correct:
                        self.send_message_to_user(
                            STANDARD_COLOR,
                            f"GUESS was correct ✅!" f"You both win this round.",
                            room_id,
                        )
                        self.update_reward(room_id, 1)
                        self.log_event("correct guess", {"content": guess}, room_id)
                    else:
                        self.send_message_to_user(
                            WARNING_COLOR,
                            f"GUESS was false ❌." f"You both lose this round.",
                            room_id,
                        )
                        self.update_reward(room_id, 0)
                        self.log_event("false guess", {"content": guess}, room_id)

                    self.load_next_game(room_id)

    def _command_ready(self, room_id, user):
        """Must be sent to begin a conversation."""
        # identify the user that has not sent this event
        curr_usr, other_usr = self.sessions[room_id].players
        if curr_usr["id"] != user:
            curr_usr, other_usr = other_usr, curr_usr
        logging.debug(f"The user id 1 = {curr_usr}")
        logging.debug(f"The user id 2 = {other_usr}")
        # only one user has sent /ready repetitively
        if curr_usr["status"] in {"ready", "done"}:
            sleep(0.5)
            self.send_message_to_user(
                STANDARD_COLOR,
                "You have already  clicked 'ready'.",
                room_id,
                curr_usr["id"],
            )

            return
        curr_usr["status"] = "ready"

        # both
        if other_usr["status"] == "ready":
            self.send_message_to_user(
                STANDARD_COLOR, "Woo-Hoo! The game will begin now.", room_id
            )
            self.start_round(room_id)
        else:
            self.send_message_to_user(
                STANDARD_COLOR,
                "Now, waiting for your partner to click 'ready'.",
                room_id,
                curr_usr["id"],
            )

    def send_instr(self, room_id, user_id, game_name):
        """Sends the instruction html to the players (explainer and guesser)"""
        if user_id == self.sessions[room_id].explainer:
            if game_name == "3ds":
                message = f"{EXPLAINER_NEW_3DS}"
            elif game_name == "tuna":
                message = f"{EXPLAINER_NEW_TUNA}"
            else: 
                message = f"{EXPLAINER_NEW_MIXED}"

        else:
            if game_name == "3ds":
                message = f"{GUESSER_NEW_3DS}"
            elif game_name == "tuna":
                message = f"{GUESSER_NEW_TUNA}"
            else: 
                message = f"{GUESSER_NEW_MIXED}"

            logging.debug(f"The instructions are getting send for the game name: {game_name}")

        self.sio.emit(
            "message_command",
            {
                "command": {"event": "send_instr", "message": message},
                "room": room_id,
                "receiver_id": user_id,
            },
        )
        sleep(1)
        
    def mark_target_round(self, room_id, round_nr, user_id):
        """Marks the target picture"""
        starting_pos = self.sessions[room_id].target_pos
        target_thisround =  self.sessions[room_id].grids.data[f"Runde_{round_nr}_player_1_target_position"]
        self.log_event("target_explainer", {"content": f"{target_thisround}"}, room_id)

        if starting_pos == 0 or starting_pos == target_thisround: # Either 0 or 3=3
            logging.debug(f"Marking targets for round: {round_nr}")
            logging.debug(f"The target for the explainer this round is: {target_thisround}")
            # The target position is detetermined by the explainer
            self.sio.emit(
                "message_command",
                {
                    "command": {"event": f"mark_target_picture_{target_thisround}", "message": "Target Image"},
                    "room": room_id,
                    "receiver_id": user_id,
                },
                )
            self.sessions[room_id].target_pos = self.sessions[room_id].grids.data[f"Runde_{round_nr}_player_1_target_position"] # only import for when 0
        
        elif starting_pos != target_thisround:
            # Delete target mark from previous target
            # Create new target
            logging.debug(f"Start and target pos are not the same!!! Start: {starting_pos} & Target Pos: {target_thisround}")
            self.sio.emit(
                "message_command",
                {
                    "command": {"event": f"unmark_target_picture_{starting_pos}", "message": f"Image {starting_pos}"},
                    "room": room_id,
                    "receiver_id": user_id,
                },
                )
            self.sio.emit(
                "message_command",
                {
                    "command": {"event": f"mark_target_picture_{target_thisround}", "message": "Target Image"},
                    "room": room_id,
                    "receiver_id": user_id,
                },
                )
            self.sessions[room_id].target_pos = self.sessions[room_id].grids.data[f"Runde_{round_nr}_player_1_target_position"]

    def load_next_game(self, room_id):
        """ Prepare for starting the next round for both players """
        self.sessions[room_id].timer.reset()
        if self.sessions[room_id].turn == self.sessions[room_id].maxturn:
            self.terminate_experiment(room_id)
            return
        self.start_round(room_id)

    def reload_state(self, room_id, user, game_name):
        """Restart the round for a player; if the ready was already initialised"""
        if self.sessions[room_id].turn == self.sessions[room_id].maxturn:
            self.terminate_experiment(room_id)
            return

        LOG.debug(f"Reload state for {user}")
        explainer_num = self.sessions[room_id].explainer
        guesser_num = self.sessions[room_id].guesser
        self.send_instr(room_id, user, game_name)
        self.set_message_privilege(room_id, user, True)
        self.give_writing_rights(room_id, user)
        logging.debug(f"This is how the explainer looks like: {explainer_num}")
        logging.debug(f"This is how the guesser looks like: {guesser_num}")
        
        if user == explainer_num:
            self.show_pictures(room_id, explainer_num, self.sessions[room_id].turn)
            self.mark_target_round(room_id, self.sessions[room_id].turn, explainer_num)
        else:
            self.show_pictures(room_id, guesser_num, self.sessions[room_id].turn)
            self.set_message_privilege(room_id, self.sessions[room_id].guesser, False)
            self.make_input_field_unresponsive(room_id, self.sessions[room_id].guesser)

    def start_round(self, room_id):
        """ Start the round x for both players"""
        if self.sessions[room_id].turn == self.sessions[room_id].maxturn:
            self.terminate_experiment(room_id)
            return
        self.sessions[room_id].turn += 1
        logging.debug(f"Es ist die {self.sessions[room_id].turn} Runde")

        # in this game 1 round consists of only 1 turn!
        self.log_event("round", {"number": self.sessions[room_id].turn}, room_id)
        self.log_event("turn", dict(), room_id)

        self.send_message_to_user(
            STANDARD_COLOR,
            f"Let's start round {self.sessions[room_id].turn}, the images are updated!",
            room_id,
        )
        
        
        self.show_pictures(room_id, self.sessions[room_id].explainer, self.sessions[room_id].turn)
        self.show_pictures(room_id, self.sessions[room_id].guesser, self.sessions[room_id].turn)
        self.mark_target_round(room_id, self.sessions[room_id].turn, self.sessions[room_id].explainer)
        self.send_message_to_user(
            STANDARD_COLOR,
            "Generate the description for the given target.",
            room_id,
            self.sessions[room_id].explainer,
        )
        self.send_message_to_user(
            STANDARD_COLOR,
            "Wait for the description from the explainer.",
            room_id,
            self.sessions[room_id].guesser,
        )

        # update writing_rights
        self.set_message_privilege(room_id, self.sessions[room_id].explainer, True)
        # assign writing rights to other user
        self.give_writing_rights(room_id, self.sessions[room_id].explainer)
        self.set_message_privilege(room_id, self.sessions[room_id].guesser, False)
        self.make_input_field_unresponsive(room_id, self.sessions[room_id].guesser)
        self.sessions[room_id].timer.reset()
    
    # experimental 
    def show_pictures(self, room_id, user_id, round_nr):
        """This function sends out the picture for each player"""
        # logging.debug(f"This is the string from the picture path: {picture_string}")
        if user_id == self.sessions[room_id].explainer:
            player = "player_1"
            log_name = "explainer"
            logging.debug("PLAYYYYER 1")
        else:
            player = "player_2"
            log_name = "guesser"
            logging.debug("PLAYYYYER 2")
        stimuli_id = self.sessions[room_id].grids.data[f"Runde_{round_nr}_stimuli_id"]
        game_id = self.sessions[room_id].grids.data[f"Runde_{round_nr}_game_id"]
        self.log_event("game_id", {"content": f"{game_id}"}, room_id)
        self.log_event("stimuli_id", {"content": f"{stimuli_id}"}, room_id)
        
        # The paths of the pictures, depending on round and player
        pic_1 = self.sessions[room_id].grids.data[f"Runde_{round_nr}_{player}_first_image"]
        pic_2 = self.sessions[room_id].grids.data[f"Runde_{round_nr}_{player}_second_image"]
        pic_3 = self.sessions[room_id].grids.data[f"Runde_{round_nr}_{player}_third_image"]
        pic_4 = self.sessions[room_id].grids.data[f"Runde_{round_nr}_{player}_fourth_image"]
        all_pic = [pic_1, pic_2, pic_3, pic_4]

        logging.debug(f"This is pic_1: {pic_1}")
        logging.debug(f"This is pic_2: {pic_2}")
        logging.debug(f"This is pic_3: {pic_3}")
        logging.debug(f"This is pic_4: {pic_4}")
         
        self.log_event(f"pictures_round_{round_nr}_for_{log_name}", {"content": f"{all_pic}"}, room_id)
        
        pic_1_encrypt = PICTURE_DIC[f"Picture_{pic_1}"]
        pic_2_encrypt = PICTURE_DIC[f"Picture_{pic_2}"]
        pic_3_encrypt = PICTURE_DIC[f"Picture_{pic_3}"]
        pic_4_encrypt = PICTURE_DIC[f"Picture_{pic_4}"]

        for i in range(4):
            if i == 0:
                self.sio.emit(
                "message_command",
                {
                    "command": {"event": f"update_grid{i+1}", "message": pic_1_encrypt},
                    "room": room_id,
                    "receiver_id": user_id,
                },
                )
            elif i == 1:
                self.sio.emit(
                "message_command",
                {
                    "command": {"event": f"update_grid{i+1}", "message": pic_2_encrypt},
                    "room": room_id,
                    "receiver_id": user_id,
                },
                )
            elif i == 2:
                self.sio.emit(
                "message_command",
                {
                    "command": {"event": f"update_grid{i+1}", "message": pic_3_encrypt},
                    "room": room_id,
                    "receiver_id": user_id,
                },
                )
            elif i == 3:
                self.sio.emit(
                "message_command",
                {
                    "command": {"event": f"update_grid{i+1}", "message": pic_4_encrypt},
                    "room": room_id,
                    "receiver_id": user_id,
                },
                )

    def send_message_to_user(self, color, message, room, receiver=None):
        if receiver:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        message=(message),
                        color=color,
                    ),
                    "room": room,
                    "receiver_id": receiver,
                    "html": True,
                },
            )
        else:
            self.sio.emit(
                "text",
                {
                    "message": COLOR_MESSAGE.format(
                        message=(message),
                        color=color,
                    ),
                    "room": room,
                    "html": True,
                },
            )
        sleep(1)

    def timeout_waiting_room(self, user):
        # get layout_id
        response = requests.get(
            f"{self.uri}/tasks/{self.task_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        layout_id = response.json()["layout_id"]

        # create a new task room for this user
        room = requests.post(
            f"{self.uri}/rooms",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"layout_id": layout_id},
        )
        room = room.json()

        # remove user from waiting_room
        self.remove_user_from_room(user["id"], self.waiting_room)

        # move user to new task room
        response = requests.post(
            f"{self.uri}/users/{user['id']}/rooms/{room['id']}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if not response.ok:
            LOG.error(f"Could not let user join room: {response.status_code}")
            exit(4)

        sleep(2)

        self.send_message_to_user(
            STANDARD_COLOR,
            "Unfortunately we were not able to find a partner for you, "
            "you will now get a token.",
            room["id"],
            user["id"],
        )
        self.confirmation_code(room["id"], "timeout_waiting_room", user["id"])
        self.remove_user_from_room(user["id"], room["id"])

    def remove_user_from_room(self, user_id, room_id):
        response = requests.get(
            f"{self.uri}/users/{user_id}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "getting user")
        etag = response.headers["ETag"]

        response = requests.delete(
            f"{self.uri}/users/{user_id}/rooms/{room_id}",
            headers={"If-Match": etag, "Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "removing user from task toom")

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

    def room_to_read_only(self, room_id):
        """Set room to read only."""
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "readonly", "value": "True"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "setting room to read_only")
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={"attribute": "placeholder", "value": "This room is read-only"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "setting room title to read_only")

        # remove user from room
        if room_id in self.sessions:
            for usr in self.sessions[room_id].players:
                self.remove_user_from_room(usr["id"], room_id)

    def terminate_experiment(self, room_id):
        self.send_message_to_user(
            STANDARD_COLOR,
            "The experiment is over 🎉 🎉 thank you very much for your time!",
            room_id,
        )
        for player in self.sessions[room_id].players:
            self.confirmation_code(room_id, "success", player["id"])
        self.close_game(room_id)

    def timeout_close_game(self, room_id, status):
        # lock processes for other threads
        self.sessions[room_id].lock.acquire()
        logging.debug(f"timeout_close")
        if room_id in self.sessions:
            self.send_message_to_user(
                STANDARD_COLOR, "The room is closing because of inactivity", room_id
            )
            for player in self.sessions[room_id].players:
                self.confirmation_code(room_id, status, player["id"])
            self.close_game(room_id)

    def close_game(self, room_id):
        logging.debug(f"close_game")
        self.send_message_to_user(
            STANDARD_COLOR, "The room is closing, see you next time 👋", room_id
        )
        self.sessions[room_id].game_over = True
        self.room_to_read_only(room_id)
        # open processes for other threads if there was a lock
        if self.sessions[room_id].lock.locked():
            self.sessions[room_id].lock.release()

        # remove any task room specific objects
        self.sessions.clear_session(room_id)

    def update_reward(self, room_id, reward):
        score = self.sessions[room_id].points["score"]
        score += reward
        score = round(score, 2)
        self.sessions[room_id].points["score"] = max(0, score)
        self.update_title_points(room_id, reward)

    def update_title_points(self, room_id, reward):
        score = self.sessions[room_id].points["score"]
        correct = self.sessions[room_id].points["history"][0]["correct"]
        wrong = self.sessions[room_id].points["history"][0]["wrong"]
        if reward == 0:
            wrong += 1
        elif reward == 1:
            correct += 1
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/text/title",
            json={
                "text": f"Score: {score} 🏆 | Correct: {correct} ✅ | Wrong: {wrong} ❌"
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.sessions[room_id].points["history"][0]["correct"] = correct
        self.sessions[room_id].points["history"][0]["wrong"] = wrong
        self.request_feedback(response, "setting point stand in title")

    def confirmation_code(self, room_id, status, user_id):
        """Generate AMT token that will be sent to each player."""
        amt_token = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if room_id in self.sessions:
            points = self.sessions[room_id].points
        else:
            points = 0
            logging.debug(f"Room not in self sessions {points}")
        self.log_event(
            "confirmation_log",
            {
                "status_txt": status,
                "amt_token": amt_token,
                "receiver": user_id,
                "points": points,
            },
            room_id,
        )
        self.send_message_to_user(
            STANDARD_COLOR,
            "Please remember to "
            "save your token before you close this browser window. "
            f"Your token: {amt_token}",
            room_id,
            user_id,
        )

    def set_message_privilege(self, room_id, user_id, value):
        """
        change user's permission to send messages
        """
        # get permission_id based on user_id
        response = requests.get(
            f"{self.uri}/users/{user_id}/permissions",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.request_feedback(response, "retrieving user's permissions")

        permission_id = response.json()["id"]
        requests.patch(
            f"{self.uri}/permissions/{permission_id}",
            json={"send_message": value},
            headers={
                "If-Match": response.headers["ETag"],
                "Authorization": f"Bearer {self.token}",
            },
        )
        self.request_feedback(response, "changing user's message permission")

    def make_input_field_unresponsive(self, room_id, user_id):
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "readonly",
                "value": "true",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        message = INPUT_FIELD_UNRESP_GUESSER
        if user_id == self.sessions[room_id].explainer:
            message = INPUT_FIELD_UNRESP_EXPLAINER

        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "placeholder",
                "value": f"{message}",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def give_writing_rights(self, room_id, user_id):
        response = requests.delete(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "readonly",
                "value": "placeholder",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = requests.patch(
            f"{self.uri}/rooms/{room_id}/attribute/id/text",
            json={
                "attribute": "placeholder",
                "value": "Enter your message here!",
                "receiver_id": user_id,
            },
            headers={"Authorization": f"Bearer {self.token}"},
        )


def correct_guess(self, room_id, round_nr, guess):
    """ Analyses if the answer is correct"""
    
    right_answer = self.sessions[room_id].grids.data[f"Runde_{round_nr}_player_2_target_position"] # Any number between 1 and 4
    logging.debug(f"The function correct_guess was used. It's round: {round_nr}")
    logging.debug(f"The function correct_guess was used. The guess of the guesser is: {guess}")
    logging.debug(f"The right answer is...{right_answer}")
    self.log_event("target_guesser", {"content": f"{right_answer}"}, room_id)

    if guess == right_answer:
        result = True
    else:
        result = False
    return result

if __name__ == "__main__":
    # set up logging configuration
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")

    # create commandline parser
    parser = ReferenceBot.create_argparser()

    if "WAITING_ROOM" in os.environ:
        waiting_room = {"default": os.environ["WAITING_ROOM"]}
    else:
        waiting_room = {"required": True}
    parser.add_argument(
        "--waiting_room",
        type=int,
        help="room where users await their partner",
        **waiting_room,
    )

    args = parser.parse_args()
    logging.debug(args)

    # create bot instance
    bot = ReferenceBot(args.token, args.user, args.task, args.host, args.port)

    bot.post_init(args.waiting_room)

    # connect to chat server
    bot.run()
