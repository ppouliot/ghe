import os
import sys
import glob
import argparse
import inspect
import subprocess
import logging
import keyring
import pyparsing
import shlex

# Fix OS X Tab completion due to libedit not being fully readline compatible.
import readline, rlcompleter
if 'libedit' in readline.__doc__:
    readline.parse_and_bind('bind ^I rl_complete')
else:
    readline.parse_and_bind('tab: complete')

from cmd2 import Cmd, ParsedString

logger = logging.getLogger(__name__)

from . import __title__, __desc__, __version__

keyring_keys = [
    'ghe-host',     # The hostname to the GHE server
    'ghe-ssh-user', # The SSH username to the GHE server (default: admin)
    'ghe-ssh-port', # The SSH port of the GHE server (default: 122)
    'ghe-user',     # A GHE admin level user
    'ghe-pass',     # The password for the GHE admin level account
    'ghe-token',    # An access token for the GHE admin level account
    'gh-token',     # An access token to your GitHub.com account
    'ghe-totp'      # A base32 seed for the OTP two-factor code generation
]

class GHE(Cmd):

    def __init__(self):
        """ Initial setup. """

        self.set_logger()
        self.log.info('%s v%s', __title__, __version__)

        self.parser = pyparsing.Word(self.legalChars + '/\\')

        self.terminators = []
        Cmd.__init__(self)

        if sys.platform == 'darwin':
            _fix_mac_codesign()

        self.commands = self._get_commands()
        self.prompt = '%s> ' % __title__.upper()

        for key in keyring_keys:
            if not keyring.get_password(__title__, key):
                print(('Missing keyring entry for {0}. Please use `set {0} '
                       '<value>` to save to keyring.').format(key))

        self.env = os.environ.copy()

    def set_logger(self, logger=None):
        """ Set the logger. """

        self.log = logger or logging.getLogger(__name__)

    def _get_commands(self):
        """ Find commands in PATH and commands directory. """

        commands = {}

        path = os.environ.get('PATH', '')
        paths = [
            os.path.expanduser(item)
            for item in path.split(os.pathsep)
        ]

        path = inspect.getsourcefile(lambda:0)
        cmd_path = os.path.abspath(os.path.join(
            os.path.dirname(os.path.abspath(path)),
            'commands'
        ))

        if os.path.isdir(cmd_path):
            paths.append(cmd_path)

        for path in paths:
            files = glob.glob(os.path.join(path, '%s-*' % __title__))

            for fname in files:
                if os.path.isfile(fname) and os.access(fname, os.X_OK):
                    cmd_name = os.path.basename(fname).split('-', 1)[1]
                    cmd_name = os.path.splitext(cmd_name)[0]
                    commands[cmd_name] = fname

        return commands

    def _run_command(self, cmd, opts):
        """ Run a subcommand. """

        env = os.environ.copy()
        for key in keyring_keys:
            env[key] = get_key(key)

        if type(opts) == str:
            opts = shlex.split(opts)

        subprocess.call([cmd] + opts, env=env)

    def onecmd(self, line):
        """ Override cmd2's command line parsing for interactive shell. """

        statement = self.parsed(line)
        cmd = statement.parsed.raw
        args = ''
        if ' ' in cmd:
            cmd, args = cmd.split(' ', 1)

        if cmd == 'exit' or cmd == 'quit':
            self._should_quit = True
            return self._STOP_AND_EXIT

        if cmd == 'help':
            print('Available %s commands are:' % __title__)
            for command in self.commands.keys():
                print('  %s' % command)
            return

        if cmd == 'set':
            key, val = args.split(' ', 1)
            if key and val:
                set_key(key, val)
            return

        if cmd == 'get':
            print(get_key(args.split(' ')[0]))
            return

        if cmd == 'unset':
            unset_key(args.split(' ')[0])
            return

        if cmd not in self.commands:
            print('%s: command not found' % cmd)
            return

        return self._run_command(self.commands.get(cmd), args)

    def completenames(self, text, *ignored):
        """ Override cmd's completenames to auto complete sub commands. """

        return [a for a in self.get_names() if a.startswith(text)]

    def get_names(self):
        """ Override cmd's get_names to only return sub commands. """

        return self.commands.keys()


class GHECLI(GHE):

    def __init__(self):
        """ Initial setup. """

        GHE.__init__(self)

        self._process_cl_args()

    def _process_cl_args(self):
        """ Process command line arguments. """

        app = self

        class Parser(argparse.ArgumentParser):
            def error(self, message):
                if message == 'too few arguments':
                    app.cmdloop()
                    exit(0)

                print('usage: %s <command>\n' % self.prog)
                print('Available %s commands are:' % __title__)
                actions = [
                    action for action in self._actions
                    if isinstance(action, argparse._SubParsersAction)
                ]
                for action in actions:
                    for choice, subparser in sorted(action.choices.items()):
                        print('  %s' % choice)

                exit(1)

        parser = Parser(
            description=__desc__,
            add_help=False
        )

        parser.add_argument('--help', '-h', action='store')

        subparsers = parser.add_subparsers(title='commands',
                description='command to run',
                dest='cmd'
        )

        for command in self.commands:
            cmd = subparsers.add_parser(command)
            cmd.set_defaults(action=command)

        args, opts = parser.parse_known_args()

        if args.cmd not in self.commands:
            self.cmdloop()
            exit(1)

        self._run_command(self.commands.get(args.cmd), opts)

        exit(0)

def set_key(key, val):
    keyring.set_password(__title__, key, val)

def get_key(key):
    return keyring.get_password(__title__, key) or ''

def unset_key(key):
    keyring.delete_password(__title__, key)

def _fix_mac_codesign():
    """If the running Python interpreter isn't property signed on macOS
    it's unable to get/set password using keyring from Keychain.
    In such case, we need to sign the interpreter first.
    https://github.com/jaraco/keyring/issues/219
    """
    global fix_mac_codesign
    logger = logging.getLogger(__name__ + '.fix_mac_codesign')
    p = subprocess.Popen(['codesign', '-dvvvvv', sys.executable],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()

    def prepend_lines(c, text):
        return ''.join(c + l for l in text.decode('utf-8').splitlines(True))
    logger.debug('codesign -dvvvvv %s:\n%s\n%s',
                 sys.executable,
                 prepend_lines('| ', stdout),
                 prepend_lines('> ', stderr))
    if b'\nSignature=' in stderr:
        logger.debug('%s: already signed', sys.executable)
        return
    logger.info('%s: not signed yet; try signing...', sys.executable)
    p = subprocess.Popen(['codesign', '-f', '-s', '-', sys.executable],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    os.waitpid(p.pid, 0)
    logger.debug('%s: signed\n%s\n%s',
                 sys.executable,
                 prepend_lines('| ', stdout),
                 prepend_lines('> ', stderr))
    logger.debug('respawn the equivalent process...')
    raise SystemExit(subprocess.call(sys.argv))
