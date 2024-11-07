# -*- coding: utf-8 -*-
"""File contains global variables meant to be used read-only."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROLIFIC_URL = "https://app.prolific.co/submissions/complete?cc="

# Path to a comma separated (csv) file with two columns.
# Each column containing the url to one image file.
DATA_PATH = os.path.join(ROOT, "data", "image_data.tsv")
WORD_LIST = os.path.join(ROOT, "data", "wordlist.txt")

# This many game rounds will be played per room and player pair.
N = 1
# Set this seed to make the random process reproducible.
SEED = None
# Whether to randomly sample images or present them in linear order.
SHUFFLE = True
# What mode the game uses for showing images. one of "same", "different", "one_blind"
GAME_MODE = "one_blind"

# Whether the bot runs a public version or not
# - This influences the kind of goodbye message
# - Public data collections will not get a token but a tweetable message
# - Set this to False when running data collections with AMT, Prolific, or similar
# - Individual tokens will be generated when this is False
# - PLATFORM influences how the confirmation token will be supplied
# - For Prolific, participants will receive a link
# - For AMT, participants will get a token to copy
PUBLIC = False
PLATFORM = "Prolific"

# All below *TIME_* variables are in minutes.
# They indicate how long a situation has to persist for something to happen.

TIME_LEFT = 5  # how many minutes a user can stay in a room before closing it
TIME_WAITING = 10  # how many minutes a user can wait for a partner
TIME_ROUND = 20  # how many minutes users can play on a single image

# colored messages
COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"

TASK_TITLE = "Find the word."

with open(
    os.path.join(ROOT, "data", "task_description.txt"), "r", encoding="utf-8"
) as f:
    TASK_DESCR = f.read()

with open(os.path.join(ROOT, "data", "task_greeting.txt"), "r", encoding="utf-8") as f:
    TASK_GREETING = f.read().split("\n\n\n")
