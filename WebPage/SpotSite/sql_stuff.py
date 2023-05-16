
import threading
import os
from pathlib import Path
import sqlite3
import json

from SpotSite.spot_logging import log


lock = threading.Lock()


def lock_until_finished(func):
    """
    Locks the thread until a function is finished executing

    Necessary for using SQL in an asynchronous context

    Args:
        func (callable): The function
    """
    def wrapper(*args, **kwargs):
        lock.acquire(True)
        val = func(*args, **kwargs)
        lock.release()
        return val
    return wrapper


class SqliteConnection:
    """
    A class to manage the connection to the SQL database containing programs

    Attributes:
        _connection (sqlite3.Connection): the connection to the database
        _cursor (sqlite3.Cursor): the cursor used to interact with the database

    Methods:
        _name_exists(name):
            Tells whether a program already exists with the given name
        write_program(name, program):
            Writes a program to the database
        delete_program(name):
            Deletes a program from the database
        get_program(name):
            Returns a program with a given name
        get_all_programs():
            Returns all programs in the database
        close()
            Closes the cursor and the database connection
    """
    @lock_until_finished
    def __init__(self):
        path = Path(__file__).resolve().parent.parent
        path = os.path.join(path, 'db.sqlite3')
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._cursor = self._connection.cursor()

        self._cursor.execute(
            'CREATE TABLE IF NOT EXISTS Programs (name TEXT, program TEXT)')

    def _name_exists(self, name: str) -> bool:
        """Tells whether a program already exists with the given name

        Args:
            name (str): the name of the program

        Returns:
            bool: whether the program exists
        """
        query = self._cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM Programs WHERE name=? COLLATE NOCASE) LIMIT 1", (name,))
        return query.fetchone()[0]

    @lock_until_finished
    def write_program(self, name: str, program: tuple):
        log(f"Writing program to databse: {program}")
        """
        Writes a program to the database

        Args:
            name (str): the name of the database
            program (tuple, list): the program
        """
        if self._name_exists(name):
            self._cursor.execute(
                'UPDATE Programs SET program = ? WHERE name = ?', (program, name))
        else:
            self._cursor.execute(
                'INSERT INTO Programs VALUES (?, ?)', (name, program))
        self._connection.commit()

    @lock_until_finished
    def delete_program(self, name: str):
        log(f"Deleting program: {name}")
        """
        Deletes a program from the database

        Args:
            name (str): the name of the program
        """
        self._cursor.execute("DELETE FROM Programs WHERE name=?", (name,))
        self._connection.commit()

    @lock_until_finished
    def get_program(self, name: str) -> tuple:
        """
        Returns a program with a given name

        Args:
            name (str): the name of the program

        Returns:
            tuple: the program
        """
        query = self._cursor.execute(
            "SELECT program FROM Programs WHERE name = ?", (name,))
        command_string = ''.join(query.fetchone()[0])
        return json.loads(command_string)

    @lock_until_finished
    def get_all_programs(self) -> tuple:
        """
        Returns all programs in the database

        Returns:
            tuple: The list of programs
        """
        query = self._cursor.execute(
            "SELECT name, program FROM Programs").fetchall()
        return query

    @lock_until_finished
    def close(self):
        """
        Closes the cursor and the database connection
        """
        self._cursor.close()
        self._connection.close()
