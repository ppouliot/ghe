#!/usr/bin/env python
"""
"""

import argparse, os, paramiko, sys

class Announce(object):

    def __init__(self, **kwargs): #token, source_org):
        ''' Constructor. '''

        self.ghe_host = kwargs.get('ghe_host')
        self.ghe_ssh_port = kwargs.get('ghe_ssh_port')
        self.ghe_ssh_user = kwargs.get('ghe_ssh_user')
        self.debug = kwargs.get('debug', False)

        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        args = {
            'username': self.ghe_ssh_user,
            'port': self.ghe_ssh_port,
            'look_for_keys': False
        }

        self.client.connect(self.ghe_host, **args)

    def announce(self, announcement):
        ''' Set an announcement banner on Github Enterprise '''

        print('Setting announcement banner...')
        self.run_ssh('ghe-announce -s "{0!s}"'.format(announcement))

    def clear(self):
        ''' Clear announcement banner on Github Enterprise '''

        print('Clearing announcement banner...')
        res = self.run_ssh('ghe-announce -u')

    def status(self):
        ''' Get the status of an announcement banner on Github Enterprise '''

        res = self.run_ssh('ghe-announce -g')

        return res[0].rstrip()

    def run_ssh(self, cmd):
        ''' Run the command on the SSH connection to the GHE server. '''

        if self.debug: print(' - {0}'.format(cmd))
        stdin, stdout, stderr = self.client.exec_command(cmd)

        ret = []
        for line in stdout:
            if self.debug: print(' + {0}'.format(line.encode('utf-8').rstrip()))
            ret.append(line)

        return ret

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Tool to manage Github Enterprises announcement banner.',
        epilog=(
            'To retrieve the current status of the announcement banner on the GHE server:\n'
            '	GHE> announce\n\n'
            'To set the announcement banner on the GHE server:\n'
            '	GHE> announce Your announcement message\n\n'
            'To clear the announcement banner on the GHE server:\n'
            '	$ ghe announce --clear'
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('message',
        help='the message to be set as the announcement banner',
        nargs='*',
        metavar='ANNOUNCEMENT'
    )
    parser.add_argument('-clear',
        help='clear the announcement banner from the GHE server.',
        action='store_true'
    )
    parser.add_argument('-ghe-host',
        help=(
            'the hostname to your GitHub Enterprise server '
            '(default: value from `ghe-host` environment variable)'
        ),
        metavar='HOST',
        default=os.getenv('ghe-host')
    )
    parser.add_argument('-ghe-ssh-port',
        help=(
            'the port to your GitHub Enterprise SSH server '
            '(default: 122, or value from `ghe-ssh-port` environment variable)'
        ),
        metavar='PORT',
        type=int,
        default=os.getenv('ghe-ssh-port', 122)
    )
    parser.add_argument('-ghe-ssh-user',
        help=(
            'the user to use for SSH access to your GitHub Enterprise server '
            '(default: value from `ghe-ssh-user` environment variable)'
        ),
        metavar='USER',
        type=str,
        default=os.getenv('ghe-ssh-user')
    )
    parser.add_argument('-debug',
        help='enable debug mode',
        action='store_true'
    )

    args, unknown = parser.parse_known_args()

    if not (args.ghe_host):
        parser.error(
            'GitHub Enterprise host not set. Please use -ghe-host HOST.'
        )

    if not (args.ghe_ssh_user):
        parser.error(
            'GitHub Enterprise SSH user not set. Please use -ghe-ssh-user USER.'
        )

    app = Announce(
        ghe_host=args.ghe_host,
        ghe_ssh_port=args.ghe_ssh_port,
        ghe_ssh_user=args.ghe_ssh_user,
        debug=args.debug
    )

    if args.clear:
        app.clear()
    elif len(args.message):
        app.announce(' '.join(*[args.message]))

    print(app.status())
