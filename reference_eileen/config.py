from pathlib import Path
import os
from reference_eileen.base64encode import encode_image_to_base64 as encode 
import re

ROOT = Path(__file__).parent.resolve()

with open(Path(f"{ROOT}/data/instructions/explainer_instr_3ds.html")) as html_explainer:
    EXPLAINER_HTML = html_explainer.read()
# Picture 1 = 1915.png, Picture 2 = 1393.png, Picture 3 = 15698.png, Picture 4 = 12800.png
 
with open(Path(f"{ROOT}/data/instructions/guesser_instr_3ds.html")) as html_guesser:
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
PATHNAME = ""
PICTURE_ENCRYPT = ""
PIC_VARIABLE = 0
for filename in os.listdir(TRY):
    if filename.endswith(".png"): 
        # print(os.path.join(directory, filename))
        PATHNAME = Path (f"{ROOT}/data/3ds_images/{filename}")
        PICTURE_ENCRYPT = encode(PATHNAME)
        PICTURE_DIC[f"Picture_{filename}"] = PICTURE_ENCRYPT
        PIC_VARIABLE += 1
    else:
        continue

EXPLAINER_NEW = re.sub("3ds_images/1915.png", f"data:image/png;base64,{PICTURE_DIC['Picture_1915.png']}", EXPLAINER_HTML)
EXPLAINER_NEW = re.sub("3ds_images/1393.png", f"data:image/png;base64,{PICTURE_DIC['Picture_1393.png']}", EXPLAINER_NEW)
EXPLAINER_NEW = re.sub("3ds_images/15698.png", f"data:image/png;base64,{PICTURE_DIC['Picture_15698.png']}", EXPLAINER_NEW)
EXPLAINER_NEW = re.sub("3ds_images/12800.png", f"data:image/png;base64,{PICTURE_DIC['Picture_12800.png']}", EXPLAINER_NEW)