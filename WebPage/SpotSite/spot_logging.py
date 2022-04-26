import os
import glob
import datetime
import inspect


def log(text):
    time = str(datetime.datetime.now().time())
    files_path = os.path.join(str(os.getcwd()) + "\\SpotSite\\Logs", "*")
    files = sorted(
        glob.iglob(files_path), key=os.path.getctime, reverse=True)
    filename = files[0]

    with open(filename, 'a') as f:
        f.write("\n" + time + " " + text)
        f.close()


def create_log():
    now = datetime.datetime.now()
    path = str(os.getcwd()) + "\\SpotSite\\Logs\\"

    date = str(now.date())
    time = str(datetime.time(now.hour, now.minute,
               now.second)).replace(":", ".")
    date_time = date + "_" + time

    filename = path + date_time + ".txt"
    open(filename, 'w').close()


def join_args(args):
    joined = ""
    for arg in args:
        class_name = arg.__class__.__name__
        if class_name == "":
            joined += "WebSocket Class"
        else:
            joined += str(arg)
        joined += ", "

    return joined[:-2]


def log_action(func):
    def wrapper(*args, **kwargs):
        function_args = join_args(args)
        function_kwargs = ", ".join(str(arg) + "=" + str(val)
                                    for arg, val in kwargs.items())
        to_log = func.__name__ + ": " + function_args + ", " + function_kwargs
        log(to_log)
        return func(*args, **kwargs)

    return wrapper
