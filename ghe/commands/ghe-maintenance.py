#!/usr/bin/env python
"""
usage: ghe-maintenance.py [-h] [-ghe-host HOST] [-ghe-ssh-port PORT]
                          [-ghe-ssh-user USER] [-debug]
                          [value]

Tool to manage Github Enterprises maintenance status.

positional arguments:
  value               boolean value to set maintenance mode to (on|off,
                      true|false, 1|0)

optional arguments:
  -h, --help          show this help message and exit
  -ghe-host HOST      the hostname to your GitHub Enterprise server (default:
                      value from `ghe-host` environment variable)
  -ghe-ssh-port PORT  the port to your GitHub Enterprise SSH server (default:
                      122, or value from `ghe-ssh-port` environment variable)
  -ghe-ssh-user USER  the user to use for SSH access to your GitHub Enterprise
                      server (default: value from `ghe-ssh-user` environment
                      variable)
  -debug              enable debug mode

To retrieve the current maintenance status of the GHE server:
	$ ghe maintenance

To enable maintenance mode on the GHE server:
	$ ghe maintenance on

To disable maintenance mode on the GHE server:
	$ ghe maintenance off

Accepted values: 'on'|'off', 'yes'|'no', 'true'|'false', 't'|'f', 'y'|'n, '1'|'0'
"""

import argparse, os, paramiko

class Maintenance(object):

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

    def enable(self):
        ''' Enable maintenance mode on Github Enterprise '''

        print('Enabling maintenance mode...')
        self.run_ssh('ghe-maintenance -s')

    def disable(self):
        ''' Disable maintenance mode on Github Enterprise '''

        print('Disabling maintenance mode...')
        self.run_ssh('ghe-maintenance -u')

    def status(self):
        ''' Get the status of maintenance mode on Github Enterprise '''

        res = self.run_ssh('ghe-maintenance -q')
        if 'maintenance mode not set' in res[0]:
            return False
        else:
            return True

    def run_ssh(self, cmd):
        ''' Run the command on the SSH connection to the GHE server. '''

        if self.debug: print(' - {0}'.format(cmd))
        stdin, stdout, stderr = self.client.exec_command(cmd)

        ret = []
        for line in stdout:
            if self.debug: print(' + {0}'.format(line.encode('utf-8').rstrip()))
            ret.append(line)

        return ret

def str2bool(v):
    if v.lower() in ('on', 'yes', 'true', 't', 'y', '1'):
        return True
    if v.lower() in ('off', 'no', 'false', 'f', 'n', '0'):
        return False
    raise argparse.ArgumentTypeError('Boolean value expected.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Tool to manage Github Enterprises maintenance status.',
        epilog=(
            'To retrieve the current maintenance status of the GHE server:\n'
            '	$ ghe maintenance\n\n'
            'To enable maintenance mode on the GHE server:\n'
            '	$ ghe maintenance on\n\n'
            'To disable maintenance mode on the GHE server:\n'
            '	$ ghe maintenance off\n\n'
            'Accepted values: "on"|"off", "yes"|"no", "true"|"false", "t"|"f", "y"|"n, "1"|"0"'
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('value',
        help='boolean value to set maintenance mode to (on|off, true|false, 1|0)',
        nargs='?',
        type=str2bool
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

    app = Maintenance(
        ghe_host=args.ghe_host,
        ghe_ssh_port=args.ghe_ssh_port,
        ghe_ssh_user=args.ghe_ssh_user,
        debug=args.debug
    )

    if args.value is True:
        app.enable()
    elif args.value is False:
        app.disable()

    print('Maintenance mode is currently: %s' % ('ON' if app.status() else 'OFF'))
