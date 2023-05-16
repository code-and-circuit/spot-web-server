from SpotSite.background_process import bg_process
from SpotSite.utils import output_to_socket, start_thread
from SpotSite.file_executing import execute


def do_action(action: str, socket_index: any, args: any = None) -> any:
    """
    Handles actions from the client


    Args:
        action (str): The name of the action
        socket_index any: The index of the socket to display to
        args (any, optional): Any arguments. Defaults to None.

    Returns:
        any: Requested information
    """
    if action == "start":
        # Makes sure that the background process is not already running before it starts it
        if bg_process.is_running:
            output_to_socket(socket_index,
                             "Cannot start background process because background process is already running")
            return

        if bg_process._is_connecting:
            output_to_socket(socket_index, "Robot is already connecting!")
            return

        bg_process.start_bg_process(socket_index)

    elif action == "end":
        # Makes sure that the background process is running before it ends it
        if not bg_process.is_running:
            output_to_socket(socket_index,
                             "Cannot end main loop because main loop is not running")
            return

        bg_process.end_bg_process()
        output_to_socket(socket_index, "Ending main loop...")
        while bg_process.robot:
            pass
        output_to_socket(socket_index, "Main loop ended")

    elif action == "toggle_accept_command":
        bg_process._is_accepting_commands = not bg_process._is_accepting_commands

        output_to_socket(-1, bg_process._is_accepting_commands,
                         type="toggle_accept_command", all=True)

    elif action == "run_program":
        # Makes sure that the background process is running (robot is connected) before it tries to run a program
        bg_process.active_program_name = args

        if not bg_process.is_running:
            output_to_socket(socket_index,
                             "Cannot run program because background process is not running")
            return
        # Makes sure that a program is not already running before it runs one
        if bg_process.program_is_running:
            output_to_socket(socket_index,
                             "Cannot run program because a program is already running")
            return

        bg_process.program_socket_index = socket_index
        bg_process.set_program_to_run(args)
        output_to_socket(socket_index, "Running Program")

    elif action == "remove_program":
        bg_process.remove_program(args)

    elif action == "estop":
        bg_process.estop()

    elif action == "estop_release":

        bg_process.release_estop()

    elif action == "connect":
        if bg_process._is_connecting:
            output_to_socket(socket_index, "Robot is already connecting!")
            return
        start_thread(bg_process._connect_to_robot, args=(socket_index))

    elif action == "disconnect_robot":
        output_to_socket(socket_index, "Disconnecting from robot...")
        bg_process._disconnect_from_robot()
        output_to_socket(socket_index, "Disconnected from robot")

    elif action == "clear_estop":
        bg_process._clear_estop()

    elif action == "clear_lease":
        bg_process._clear_lease()

    elif action == "acquire_estop":
        if bg_process._is_connecting:
            output_to_socket(socket_index, "Robot is already connecting!")
            return
        if not bg_process.robot:
            output_to_socket(
                socket_index, "Cannot acquire Estop because robot is not connected!")
            return
        start_thread(bg_process._acquire_estop, args=(socket_index))

    elif action == "acquire_lease":
        if bg_process._is_connecting:
            output_to_socket(socket_index, "Robot is already connecting!")
            return
        if not bg_process.robot:
            output_to_socket(
                socket_index, "Cannot acquire lease because robot is not connected!")
            return
        if not bg_process._estop_client:
            output_to_socket(
                socket_index, "Cannot acquire lease because Estop has not been acquired!")
            return
        start_thread(bg_process._acquire_lease, args=(socket_index))

    elif action == "check_if_running":
        return bg_process.is_running

    elif action == "toggle_auto_run":
        bg_process.toggle_auto_run()

    elif action == "step_command":
        if not bg_process.is_running:
            output_to_socket(
                socket_index, "Background process is not running!")
            return
        if bg_process._will_immediately_run_commands or bg_process.is_running_commands:
            output_to_socket(socket_index, "Already running commands!")
            return
        bg_process._should_run_commands = True

    elif action == "execute_file":
        execute(bg_process.robot, bg_process._command_client)

    else:
        output_to_socket(socket_index, f"Command not recognized: {action}")
