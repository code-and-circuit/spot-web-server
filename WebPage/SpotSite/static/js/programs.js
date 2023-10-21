const program_handler = {
    programs : [],
    selected_program : "",

    show_programs() {
        $(".program-list").html("");
            for (const program in this.programs) {
                // Create a button that allows the program to be selected
                $(".program-list").html(
                    $(".program-list").html() +
                    `<br><button id='program' onclick=program_handler.display_program('${program}')>${program}</button>`
                );
            }
    },

    // Sends a request to retrieve the program list, which is sent back through the websocket
    get_programs() {
        $.ajax({
            type: "GET",
            url: urls.get_program,
            data: {},
            success: (response) => {
                this.programs = response["programs"];
                this.show_programs();
            },
            error: (response) => {
                addOutput("<red>Server error: " + response["status"] + ".</red>");
                // A 500 error is generally caused by the socket being closed when output tries to be sent back
                if (response["status"] == "500") {
                    addOutput("Did the socket close? If so, try reloading.", true);
                }
            },
        });
    },

    display_command(command) {
        let line = command["Command"] + "("; // Start the new line to be displayed

        // Display arguments in the command
        for (const arg in command["Args"]) {
            line += command["Args"][arg] + ", ";
        }

        // Remove the trailing comma and space before adding the closing parenthese
        // - If there were no arguments, there will simply be an opening parenthese,
        //      so no action required
        if (line.substring(line.length - 1, line.length) != "(") {
            line = line.substring(0, line.length - 2);
        }
        line += ")<br>"; //Add the ending parenthese and move to the next line
        return line
    },

    display_program(name) {
        this.selected_program = name;
        $("#program-name").html(this.selected_program);
        $("#program-info").html("");
        for (const c in this.programs[name]) {
            const command = this.programs[name][c]; // Get the command object

            const line = this.display_command(command);
            $("#program-info").html($("#program-info").html() + line);
        }
    }

}