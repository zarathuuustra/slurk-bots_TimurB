from pathlib import Path
import os

ROOT = Path(__file__).parent.resolve()

with open(Path(f"{ROOT}/data/instructions/explainer_instr_mixed.html")) as html_explainer:
    EXPLAINER_HTML = html_explainer.read()

with open(Path(f"{ROOT}/data/instructions/guesser_instr_mixed.html")) as html_guesser:
    GUESSER_HTML = html_guesser.read()

with open(Path(f"{ROOT}/data/empty_grid.html")) as html_guesser:
    EMPTY_GRID = html_guesser.read()

GRIDS = Path(f"{ROOT}/data/instances_unique.json")

GRIDS_PER_ROOM = 6

COLOR_MESSAGE = '<a style="color:{color};">{message}</a>'
STANDARD_COLOR = "Purple"
WARNING_COLOR = "FireBrick"

with open(Path(f"{ROOT}/data/task_greeting.txt"), "r", encoding="utf-8") as f:
    TASK_GREETING = f.read().split("\n\n\n")

TIMEOUT_TIMER = 5  # minutes of inactivity before the room is closed automatically
LEAVE_TIMER = 3  # minutes if a user is alone in a room/both users left
WAITING_ROOM_TIMER = 5 # minutes if a user is waiting for the other player


INPUT_FIELD_UNRESP_GUESSER = "You can't send messages, you can only get them"
INPUT_FIELD_UNRESP_EXPLAINER = "Wait for your partner's choice"

# THE NEW PICTURES for Eileens version of the game
PATH_1027 = Path(f"{ROOT}/data/3ds_images/1027.png")
PICTURE_DIC = {}
TRY = Path(f"{ROOT}/data/3ds_images/")
PIC_VARIABLE = 0
for filename in os.listdir(TRY):
    if filename.endswith(".png"): 
        # print(os.path.join(directory, filename))
        PICTURE_DIC[f"Picture_{filename}"] =Path (f"{ROOT}/data/3ds_images/{filename}")
        PIC_VARIABLE += 1
    else:
        continue