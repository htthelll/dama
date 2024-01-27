import os
import sys


def start_celery():
    python_executable = sys.executable
    os.system(f'{python_executable} -m celery -A djangoProject worker -l info -P solo')
