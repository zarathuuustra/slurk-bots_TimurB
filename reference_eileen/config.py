from pathlib import Path
import os
from reference_eileen.base64encode import encode_image_to_base64 as encode 
import re

ROOT = Path(__file__).parent.resolve()

# 3ds instruction htmls
with open(Path(f"{ROOT}/data/instructions/explainer_instr_3ds.html")) as html_explainer:
    EXPLAINER_OLD_3DS = html_explainer.read()

with open(Path(f"{ROOT}/data/instructions/guesser_instr_3ds.html")) as html_guesser:
    GUESSER_OLD_3DS = html_guesser.read()

# tuna instruction htmls
with open(Path(f"{ROOT}/data/instructions/explainer_instr_tuna.html")) as html_explainer:
    EXPLAINER_OLD_TUNA = html_explainer.read()

 
with open(Path(f"{ROOT}/data/instructions/guesser_instr_tuna.html")) as html_guesser:
    GUESSER_OLD_TUNA = html_guesser.read()

# mixed instruction htmls
with open(Path(f"{ROOT}/data/instructions/explainer_instr_mixed.html")) as html_explainer:
    EXPLAINER_OLD_MIXED = html_explainer.read()

 
with open(Path(f"{ROOT}/data/instructions/guesser_instr_mixed.html")) as html_guesser:
    GUESSER_OLD_MIXED = html_guesser.read()

INSTANCES = Path(f"{ROOT}/data/slurk_instances.json")

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
PICTURE_DIC = {}
PATH_3DS = Path(f"{ROOT}/data/3ds_images/")
PATH_TUNA = Path(f"{ROOT}/data/tuna_images/")
PATHNAME = ""
PICTURE_ENCRYPT = ""
for filename in os.listdir(PATH_3DS):
    if filename.endswith(".png"): 
        # print(os.path.join(directory, filename))
        PATHNAME = Path (f"{ROOT}/data/3ds_images/{filename}")
        PICTURE_ENCRYPT = encode(PATHNAME)
        PICTURE_DIC[f"Picture_3ds_images/{filename}"] = PICTURE_ENCRYPT
    else:
        continue

for filename in os.listdir(PATH_TUNA):
    if filename.endswith(".png"): 
        # print(os.path.join(directory, filename))
        PATHNAME = Path (f"{ROOT}/data/tuna_images/{filename}")
        PICTURE_ENCRYPT = encode(PATHNAME)
        PICTURE_DIC[f"Picture_tuna_images/{filename}"] = PICTURE_ENCRYPT
    else:
        continue

# 3ds EXPLAINER HTML PICTURE CHANGE- Picture 1 = 1915.png, Picture 2 = 1393.png, Picture 3 = 15698.png, Picture 4 = 12800.png
EXPLAINER_NEW_3DS = re.sub("3ds_images/1915.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/1915.png']}", EXPLAINER_OLD_3DS)
EXPLAINER_NEW_3DS = re.sub("3ds_images/1393.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/1393.png']}", EXPLAINER_NEW_3DS)
EXPLAINER_NEW_3DS = re.sub("3ds_images/15698.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/15698.png']}", EXPLAINER_NEW_3DS)
EXPLAINER_NEW_3DS = re.sub("3ds_images/12800.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/12800.png']}", EXPLAINER_NEW_3DS)

# 3ds GUESSER HTML PICTURE CHANGE - Picture 1 = 1915.png, Picture 2 = 1393.png, Picture 3 = 1393.png, Picture 4 = 12800.png
GUESSER_NEW_3DS = re.sub("3ds_images/1915.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/1915.png']}", GUESSER_OLD_3DS)
GUESSER_NEW_3DS = re.sub("3ds_images/1393.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/1393.png']}", GUESSER_NEW_3DS)
GUESSER_NEW_3DS = re.sub("3ds_images/1393.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/1393.png']}", GUESSER_NEW_3DS)
GUESSER_NEW_3DS = re.sub("3ds_images/12800.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/12800.png']}", GUESSER_NEW_3DS)

# Tuna EXPLAINER HTML PICTURE CHANGE - Picture 1 = 13.png, Picture 2 = 42.png, Picture 3 = 53.png, Picture 4 = 23.png
EXPLAINER_NEW_TUNA = re.sub("tuna_images/13.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/13.png']}", EXPLAINER_OLD_TUNA)
EXPLAINER_NEW_TUNA = re.sub("tuna_images/42.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/42.png']}", EXPLAINER_NEW_TUNA)
EXPLAINER_NEW_TUNA = re.sub("tuna_images/53.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/53.png']}", EXPLAINER_NEW_TUNA)
EXPLAINER_NEW_TUNA = re.sub("tuna_images/23.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/23.png']}", EXPLAINER_NEW_TUNA)

# Tuna GUESSER HTML PICTURE CHANGE - # Picture 1 = 13.png, Picture 2 = 42.png, Picture 3 = 53.png, Picture 4 = 23.png
GUESSER_NEW_TUNA = re.sub("tuna_images/13.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/13.png']}", GUESSER_OLD_TUNA)
GUESSER_NEW_TUNA = re.sub("tuna_images/42.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/42.png']}", GUESSER_NEW_TUNA)
GUESSER_NEW_TUNA = re.sub("tuna_images/53.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/53.png']}", GUESSER_NEW_TUNA)
GUESSER_NEW_TUNA = re.sub("tuna_images/23.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/23.png']}", GUESSER_NEW_TUNA)

# MIXED EXPLAINER HTML PICTURE CHANGE
# First row of pictures: Picture 1 = tuna_images/13.png, Picture 2 = tuna_images/42.png,
# Picture 3 = tuna_images/53.png, Picture 4 = tuna_images/23.png
# Second row of pictures: Picture 1 = 3ds_images/1915.png, Picture 2 = 3ds_images/6135.png,
# Picture 3 = 3ds_images/15698.png, Picture 4 = 3ds_images/12800.png
EXPLAINER_NEW_MIXED = re.sub("tuna_images/13.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/13.png']}", EXPLAINER_OLD_MIXED)
EXPLAINER_NEW_MIXED = re.sub("tuna_images/42.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/42.png']}", EXPLAINER_NEW_MIXED)
EXPLAINER_NEW_MIXED = re.sub("tuna_images/53.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/53.png']}", EXPLAINER_NEW_MIXED)
EXPLAINER_NEW_MIXED = re.sub("tuna_images/23.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/23.png']}", EXPLAINER_NEW_MIXED)

EXPLAINER_NEW_MIXED = re.sub("3ds_images/1915.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/1915.png']}", EXPLAINER_NEW_MIXED)
EXPLAINER_NEW_MIXED = re.sub("3ds_images/6135.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/6135.png']}", EXPLAINER_NEW_MIXED)
EXPLAINER_NEW_MIXED = re.sub("3ds_images/15698.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/15698.png']}", EXPLAINER_NEW_MIXED)
EXPLAINER_NEW_MIXED = re.sub("3ds_images/12800.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/12800.png']}", EXPLAINER_NEW_MIXED)

# MIXED GUESSER HTML PICTURE CHANGE
# First row of pictures: Picture 1 = tuna_images/13.png, Picture 2 = tuna_images/42.png,
# Picture 3 = tuna_images/53.png, Picture 4 = tuna_images/23.png
# Second row of pictures: Picture 1 = 3ds_images/1915.png, Picture 2 = 3ds_images/1393.png,
# Picture 3 = 3ds_images/1393.png, Picture 4 = 3ds_images/12800.png
GUESSER_NEW_MIXED = re.sub("tuna_images/13.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/13.png']}", GUESSER_OLD_MIXED)
GUESSER_NEW_MIXED = re.sub("tuna_images/42.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/42.png']}", GUESSER_NEW_MIXED)
GUESSER_NEW_MIXED = re.sub("tuna_images/53.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/53.png']}", GUESSER_NEW_MIXED)
GUESSER_NEW_MIXED = re.sub("tuna_images/23.png", f"data:image/png;base64,{PICTURE_DIC['Picture_tuna_images/23.png']}", GUESSER_NEW_MIXED)

GUESSER_NEW_MIXED = re.sub("3ds_images/1915.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/1915.png']}", GUESSER_NEW_MIXED)
GUESSER_NEW_MIXED = re.sub("3ds_images/1393.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/1393.png']}", GUESSER_NEW_MIXED)
GUESSER_NEW_MIXED = re.sub("3ds_images/1393.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/1393.png']}", GUESSER_NEW_MIXED)
GUESSER_NEW_MIXED = re.sub("3ds_images/12800.png", f"data:image/png;base64,{PICTURE_DIC['Picture_3ds_images/12800.png']}", GUESSER_NEW_MIXED)