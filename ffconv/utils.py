"""
Utility functions used by processors.
"""
import subprocess
from subprocess import CalledProcessError


def execute_cmd(cmd):
    """
    Wrapper around subprocess' Popen/communicate usage pattern, capturing
    output and errors (which are raised).

    :param cmd: shell command as string
    :return: output of command as unicode
    """
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        output = b''
        for line in iter(process.stdout.readline, b''):
            if b'Error' in line:
                raise ValueError(line.decode('utf-8'))
            else:
                output += line

        retcode = process.poll()
        if retcode:
            raise CalledProcessError(retcode, process.args, output=output)

    # All good, decode output and return it
    return output.decode('utf-8').lower()


def log(msg, level=0):
    """
    Print a message with the defined indentation level.
    """
    parts = [' ' * (2 * level - 1), '- ' if level else '', msg]
    print(''.join(parts))
