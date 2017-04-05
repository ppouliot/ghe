import os
import sys
import glob
import argparse
import inspect
import subprocess
from cmd2 import Cmd
from pprint import pprint

class GHE(Cmd):

    def __init__(self):
        """ Initial setup. """

        Cmd.__init__(self)

        self.commands = self._get_commands()
        self.prompt = 'GHE> '

        self.env = os.environ.copy()


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
            files = glob.glob(os.path.join(path, 'ghe-*'))

            for fname in files:
                if os.path.isfile(fname) and os.access(fname, os.X_OK):
                    cmd_name = os.path.basename(fname).split('-', 1)[1]
                    cmd_name = os.path.splitext(cmd_name)[0]
                    commands[cmd_name] = fname

        return commands

    def _run_command(self, cmd, opts):
        """ Run a subcommand. """

        env = os.environ.copy()
        env['TESTER'] = 'this is fun.'


        subprocess.call([cmd] + opts, env=env)

    def onecmd(self, line):
        """ Override cmd2's command line parsing for interactive shell. """

        statement = self.parsed(line)
        cmd = statement.parsed.command
        args = statement.parsed.args

        if cmd == 'exit' or cmd == 'quit':
            self._should_quit = True
            return self._STOP_AND_EXIT

        if cmd == 'help':
            return self._shell_help(line)

        if cmd not in self.commands:
            print('%s: command not found' % cmd)
            return

        return self._run_command(self.commands.get(cmd), [args])

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

        ghe = self

        class Parser(argparse.ArgumentParser):
            def help(self):
                print('!')
        
            def error(self, message):
                if message == 'too few arguments':
                    ghe.cmdloop()
                    exit(0)
                    
                print('usage: %s <command>\n' % self.prog)
                print('Available ghe commands are:')
                actions = [
                    action for action in self._actions
                    if isinstance(action, argparse._SubParsersAction)
                ]
                for action in actions:
                    for choice, subparser in sorted(action.choices.items()):
                        print('  %s' % choice)

                exit(1)

        parser = Parser(
            description='GitHub Enterprise CLI Management Tool',
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
            print('Unrecognized command')
            parser.print_help()
            exit(1)

        self._run_command(self.commands.get(args.cmd), opts)

        exit(0)
