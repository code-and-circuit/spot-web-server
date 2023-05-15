import importlib.util
import sys, os


PATH_TO_FILE = "/home/admin/spot-web-server/WebPage/test/test.py"
MODULE_NAME = "main_123"

def execute(robot, command_client):
    spec = importlib.util.spec_from_file_location(MODULE_NAME, PATH_TO_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
        module.main(robot, command_client)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]

        print(f"Exception\n\ttype: {exc_type}\n\tobject: {exc_obj}\n\tfilename: {fname}\n\tline:\n\t{exc_tb.tb_lineno}")




