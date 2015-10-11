import subprocess
from itertools import chain
import logging


logger = logging.getLogger(__name__)


class CustomPopen(subprocess.Popen):

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()
        if self.stdin:
            self.stdin.close()
        # Wait for the process to terminate, to avoid zombies.
        self.wait()


def run_command(command_definition):
    command_text = ' '.join(command_definition)
    logger.debug(command_text)
    with CustomPopen(command_definition, bufsize=1, stdout=subprocess.PIPE) as process:
        if process.stdout:
            return [line.rstrip('\r\n') for line in process.stdout.readlines()]
        else:
            raise Exception('No output from: {}'. format(command_text))


def run_git_command(arguments):
    return run_command(tuple(chain(('git',), arguments)))


def run_git_rev_list_command(arguments):
    return run_git_command(tuple(chain(('rev-list',), arguments)))


def run_git_log_command(arguments):
    return run_git_command(tuple(chain(('log',), arguments)))


def run_git_ls_tree_command(arguments):
    return run_git_command(tuple(chain(('ls-tree',), arguments)))


def run_git_blame_command(arguments):
    return run_git_command(tuple(chain(('blame',), arguments)))


def get_revision_range(revision_start=None, revision_end='HEAD'):
    if revision_start:
        return revision_start + '..' + revision_end
    else:
        return revision_end
