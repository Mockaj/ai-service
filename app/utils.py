import subprocess
from fastapi import HTTPException


def read_logs_once(n: int) -> str:
    with open('app/logs/app.log', 'r') as file:
        lines = file.readlines()
    return ''.join(lines[-n:])  # Return the last 'n' lines
