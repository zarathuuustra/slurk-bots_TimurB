$(document).ready(function () {

    socket.on("command", (data) => {
        if (typeof (data.command) === "object") {
            switch(data.command.event){
                case "send_instr":
                    $("#text_to_modify").html(data.command.message)
                    break;
                case "mark_target_picture_1":
                    $("#pic1_title").html(data.command.message)
                    break;
                case "mark_target_picture_2":
                    $("#pic2_title").html(data.command.message)
                    break;
                case "mark_target_picture_3":
                    $("#pic3_title").html(data.command.message)
                    break;
                case "mark_target_picture_4":
                    $("#pic4_title").html(data.command.message)
                    break;
                case "unmark_target_picture_1":
                    $("#pic1_title").html(data.command.message)
                    console.log("Unmarking picture 1");
                    break;
                case "unmark_target_picture_2":
                    $("#pic2_title").html(data.command.message)
                    console.log("Unmarking picture 2");
                    break;
                case "unmark_target_picture_3":
                    $("#pic3_title").html(data.command.message)
                    console.log("Unmarking picture 3");
                    break;
                case "unmark_target_picture_4":
                    $("#pic4_title").html(data.command.message)
                    console.log("Unmarking picture 4");
                    break;
                case "update_grid1":
                    console.log("Updating picture state 1");
                    updateimage1(data.command.message);
                    break;
                case "update_grid2":
                    console.log("Updating picture state 2");
                    updateimage2(data.command.message);
                    break;
                case "update_grid3":
                    console.log("Updating picture state 3");
                    updateimage3(data.command.message);
                    break;
                case "update_grid4":
                    console.log("Updating picture state 4");
                    updateimage4(data.command.message);
                    break;
            }
        }
    });
})

function confirm_ready(answer){
    socket.emit("message_command",
        {
            "command": {
                "event": "confirm_ready",
                "answer": answer
            },
            "room": self_room
        }
    )
}

function choose_grid(answer){
    console.log("The grid which was the choooooosen one was:" + answer);
    socket.emit("message_command",
        {
            "command": {
                "event": "choose_grid",
                "answer": answer
            },
            "room": self_room
        }
    )
}

function updateimage1(base64_encoded_string) {
    console.log("Updating the board 1 with the string...Let's see how it works out.");
    image_id = document.getElementById("pic1");
    console.log("Current image source code is: " + image_id.src)
    image_id.src = "data:image/png;base64," + base64_encoded_string;
    console.log("New image source: " + image_id.src);
}

function updateimage2(base64_encoded_string) {
    console.log("Updating the board 2 with the string...Let's see how it works out.");
    image_id = document.getElementById("pic2");
    console.log("Current image source code is: " + image_id.src)
    image_id.src = "data:image/png;base64," + base64_encoded_string;
    console.log("New image source: " + image_id.src);
}

function updateimage3(base64_encoded_string) {
    console.log("Updating the board 3 with the string...Let's see how it works out.");
    image_id = document.getElementById("pic3");
    console.log("Current image source code is: " + image_id.src)
    image_id.src = "data:image/png;base64," + base64_encoded_string;
    console.log("New image source: " + image_id.src);
}

function updateimage4(base64_encoded_string) {
    console.log("Updating the board 4 with the string...Let's see how it works out.");
    image_id = document.getElementById("pic4");
    console.log("Current image source code is: " + image_id.src)
    image_id.src = "data:image/png;base64," + base64_encoded_string;
    console.log("New image source: " + image_id.src);
}