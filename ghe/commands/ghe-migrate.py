#!/usr/bin/env python
"""
ghe-migrate.py - GitHub to GitHub Enterprise Migration Helper Tool

usage: ghe-migrate.py [-h] [-repos REPOS] [-file REPOS] [-all] [-batch INT]
                      [-ghe-host HOST] [-ghe-port PORT] [-ghe-user USER]
                      source [dest]

Tool to perform GitHub to GitHub Enterprise migrations.

positional arguments:
  source          the organization to migrate
  dest            the destination organization

optional arguments:
  -h, --help           show this help message and exit
  -repos REPOS         comma separated list of repos
  -file REPOS          file with one repo per line
  -all                 use all repos from organization
  -batch INT           number of repos to process per batch (default: 100)
  -ghe-host HOST       the hostname to your GitHub Enterprise server (default:
                       value from `ghe-host` environment variable)
  -ghe-ssh-port PORT   the port to your GitHub Enterprise SSH server (default:
                       122, or value from `ghe-ssh-port` environment variable)
  -ghe-ssh-user USER   the user to use for SSH access to your GitHub Enterprise
                       server (default: value from `ghe-ssh-user` environment
                       variable)
  -gh-token TOKEN      GitHub access token for account with admin priveleges on
                       the source organization (default: value from `gh-token`
                       environment variable)
  -ghe-user USER       GitHub Enterprise admin username on the destination GHE
                       instance (default: value from `ghe-user` environment
                       variable)
  -ghe-token TOKEN     GitHub Enterprise access token for an admin account on
                       the destination GHE instance (default: value from
                       `ghe-token` environment variable)
  -resolve-all         attempt to automatically resolve all conflicts

You must use one of -repos, -file or -all.

If you are running ghe-migrate.py as a sub-command to ghe, then all environment
variables will be passed on to it appropriately from the central keyring
provider (MacOSX Keychain). This method is prefered as all you will need to
provide are the repos, source and destination organizations.
"""

import argparse, csv, math, os, paramiko, re, requests, sys, tempfile, time

from github import Github
from subprocess import call
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from builtins import input
from pprint import pprint

class Migrate(object):

    def __init__(self, **kwargs): #token, source_org):
        ''' Constructor. '''

        self.source_org = kwargs.get('source')
        self.dest_org = kwargs.get('dest')
        self.ghe_host = kwargs.get('ghe_host')
        self.ghe_ssh_port = kwargs.get('ghe_ssh_port')
        self.ghe_ssh_user = kwargs.get('ghe_ssh_user')
        self.ghe_user = kwargs.get('ghe_user')
        self.ghe_token = kwargs.get('ghe_token')
        self.gh_token = kwargs.get('gh_token')
        self.verbose = kwargs.get('verbose')

        self.repos = []

        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        args = {
            'username': self.ghe_ssh_user,
            'port': self.ghe_ssh_port,
            'look_for_keys': False
        }

        self.client.connect(self.ghe_host, **args)

    def load_repos(self):
        ''' Retrieve all the repositories in the source organization. '''

        print('Retrieving repos from %s.' % self.source_org)

        gh = Github(self.gh_token)

        try:
            for repo in gh.get_organization(self.source_org).get_repos():
                self.repos.append('%s/%s' % (self.source_org, repo.name))
        except:
            print((
                'Unable to retrieve the organization. Please confirm you have '
                'the right organization name and have sufficient credentials '
                'to access the organization on GitHub.'
            ))
            sys.exit(1)

        print('Found %s repos in %s.' % (len(self.repos), self.source_org))

    def validate_repos(self, source, repos):
        ''' Validate the provided repositories in the source organization. '''

        print('Verifying repos exist in organization.')

        gh = Github(self.gh_token)
        remote_repos = gh.get_organization(self.source_org).get_repos()

        remote_repos = [ repo_name.full_name for repo_name in remote_repos ]
        repos = [ '%s/%s' % (source, repo_name) for repo_name in repos ]

        diff = set(repos) - set(remote_repos)

        if len(diff):
            print('%d repos could not be found.' % len(diff))
            print('The following %d repos do not exist:' % len(diff))
            for repo_name in diff:
                print(' - %s' % repo_name)
            return []

        print('Found %s repos in %s.' % (len(repos), self.source_org))
        return repos

    def start_repo_export(self, repos):
        ''' Request an export of the provided repositories from GitHub. '''

        print('Requesting migration from GitHub for %s repos.' % len(repos))

        url = 'https://api.github.com/orgs/%s/migrations' % (self.source_org)
        ret = requests.post(url, json={
            'lock_repositories': False,
            'repositories': repos
        }, headers={
            'Authorization': 'token %s' % self.gh_token,
            'Accept': 'application/vnd.github.wyandotte-preview+json'
        })

        self.migration_url = ret.json()['url']

        while ret.json()['state'] != 'exported':
            time.sleep(5)
            ret = requests.get(self.migration_url, headers={
                'Authorization': 'token %s' % self.gh_token,
                'Accept': 'application/vnd.github.wyandotte-preview+json'
            })

            if ret.json()['state'] == 'failed':
                print('Migration failed on GitHub. Retrying with less repos.')
                repos = repos[:int(math.ceil(len(repos)/2))]
                if len(repos) <= 20:
                    pprint(repos)

                return self.start_repo_export(repos)

        print('Migration archive created.')
        return repos

    def download_archive(self):
        ''' Download the exported archive of repositories to the GHE server. '''

        print('Downloading migration archive.')

        self.run_ssh((
            'ARCHIVE_URL=`curl '
            '-H "Authorization: token %s" '
            '-H "Accept: application/vnd.github.wyandotte-preview+json" '
            '%s/archive`; '
            'curl "${ARCHIVE_URL}" -o migration_archive.tar.gz'
        ) % (self.gh_token, self.migration_url))

        print('Archive downloaded.')

    def prepare_migration(self):
        ''' Prepare the exported archive of repositories for migration. '''

        print('Preparing downloaded archive for migration.')

        res = self.run_ssh('ghe-migrator prepare migration_archive.tar.gz')

        self.guid = None
        for line in res:
            if 'Migration GUID:' in line:
                self.guid = re.search('Migration GUID: (.*)\n', line).group(1)

        if not self.guid:
            print('An error occured while preparing the migration.')
            sys.exit()

        print('Migration GUID: {0}'.format(self.guid))

    def resolve_conflicts(self):
        ''' Resolve any conflicts with the migration. '''

        if self.dest_org:
            print('Mapping source organization to destination organization.')
            self.run_ssh('ghe-migrator map %s %s rename -g %s' % (
                'https://github.com/{0}'.format(self.source_org),
                'https://{0}/{1}'.format(self.ghe_host, self.dest_org),
                self.guid
            ))

        print('Checking for conflicts.')

        editor = os.environ.get('EDITOR', 'vim')
        conflicts = self.run_ssh('ghe-migrator conflicts -g %s' % self.guid)

        with tempfile.NamedTemporaryFile(suffix='.tmp', mode='wt') as tf:
            conflict_cnt = 0

            for line in conflicts:
                conflict_cnt += 1

                if self.dest_org:
                    orig = line
                    line = self.resolve_destination_org(line)
                    if orig is not line:
                        conflict_cnt -= 1

                tf.write('%s' % line)
            tf.flush()

            if conflict_cnt > 1:
                input('Press Enter key to manually edit conflicts...')
                call([editor, '+set backupcopy=yes', tf.name])

            tf.seek(0)
            sftp = self.client.open_sftp()
            sftp.put(tf.name, 'conflicts.csv')

        print('Attempting to resolve conflicts.')
        res = self.run_ssh('ghe-migrator map -i conflicts.csv -g %s' % self.guid)
        for line in res:
            if 'Conflicts still exist' in line:
                print('Additional conflicts detected.')
                self.resolve_conflicts()

    def resolve_destination_org(self, line):
        ''' Re-map the source organization to the destination organization. '''

        host = self.ghe_host
        source = self.source_org
        dest = self.dest_org

        rx = r'organization,https://github.com/{0},https://{1}/{2},{3},{4}'
        if re.search(rx.format(source, host, source, 'map', '(.+)?'), line):
            line = re.sub(
                rx.format(source, host, source, 'map', '(.+)?'),
                rx.format(source, host, dest, 'rename', 'ghe-migrate'),
                line
            )

        return line

    def import_migration(self):
        ''' Perform the migration from the archived data. '''

        print('Importing archive data in to GHE.')

        self.run_ssh((
            'ghe-migrator import migration_archive.tar.gz -g '
            '%s -u %s -p %s') % (self.guid, self.ghe_user, self.ghe_token)
        )

        self.run_ssh('ghe-migrator unlock -g %s' % self.guid)

        print('Migration complete.')

    def run_ssh(self, cmd):
        ''' Run the command on the SSH connection to the GHE server. '''

        if self.verbose:
            print(' - {0}'.format(cmd))

        stdin, stdout, stderr = self.client.exec_command(cmd)

        ret = []
        for line in stdout:
            ret.append(line)
            if self.verbose:
                print(' + {0}'.format(line.encode('utf-8').rstrip()))

        return ret


def _is_valid_repo_name(s):
    ''' Argparse type helper - is passed repo a valid name. '''

    if re.match(r'^(?!\.{1,2}$)[a-zA-Z0-9-_\.]+$', s.strip()):
        return s.strip()
    else:
        raise ValueError('"%s" is not a valid repo name.' % s.strip())

def _is_valid_repo_list(s):
    ''' Argparse type helper - is list of repos valid. '''

    try:
        string = StringIO(s)
        reader = csv.reader(string)
        repos = []
        for row in reader:
            for repo in row:
                repos.append(_is_valid_repo_name(repo))
        return repos
    except ValueError as err:
        msg = 'Not a valid comma separated list of repos: %s' % s
        raise argparse.ArgumentTypeError(err or msg)

def _is_valid_repo_file(s):
    ''' Argparse type helper - is passed file a valid list of repos. '''

    if not os.path.exists(s):
        raise argparse.ArgumentTypeError('%s: file not found' % s)

    repos = []
    with open(s, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            for repo in row:
                try:
                    repos.append(_is_valid_repo_name(repo))
                except ValueError as err:
                    raise argparse.ArgumentTypeError(err)

    return repos


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Tool to perform GitHub to GitHub Enterprise migrations.',
        epilog='You must use one of -repos, -file or -all.'
    )
    parser.add_argument('source',
        help='the organization to migrate'
    )
    parser.add_argument('dest',
        nargs='?',
        help='the destination organization'
    )

    parser.add_argument('-repos',
        dest='repos',
        help='comma separated list of repos',
        type=_is_valid_repo_list
    )
    parser.add_argument('-file',
        dest='repos',
        help='file with one repo per line',
        type=_is_valid_repo_file
    )
    parser.add_argument('-all',
        action='store_true',
        help='use all repos from organization'
    )
    parser.add_argument('-verbose',
        action='store_true',
        help='be extra verbose in all communication with the GHE server'
    )

    parser.add_argument('-batch',
        action='store',
        default=100,
        metavar='INT',
        help='number of repos to process per batch (default: 100)',
        type=int
    )
    parser.add_argument('-skip',
        action='store',
        default=0,
        metavar='INT',
        help='number of repos to skip from the start (default: 0)',
        type=int
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
    parser.add_argument('-ghe-user',
        help=(
            'GitHub Enterprise admin level username on the destination GHE '
            'instance (default: vaklue from `ghe-user` environment variable)'
        ),
        metavar='USER',
        type=str,
        default=os.getenv('ghe-user')
    )
    parser.add_argument('-ghe-token',
        help=(
            'GitHub Enterprise access token for user set with -ghe-user '
            '(default: value from `ghe-token` environment variable)'
        ),
        metavar='TOKEN',
        type=str,
        default=os.getenv('ghe-token')
    )
    parser.add_argument('-gh-token',
        help=(
            'GitHub.com access token for an account with admin priveleges on '
            'source organization (default: value from `gh-token` environment '
            'variable)'
        ),
        metavar='TOKEN',
        type=str,
        default=os.getenv('gh-token')
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

    if not (args.ghe_ssh_user):
        parser.error(
            'GitHub Enterprise Admin User not set. Please use -ghe-user USER.'
        )

    if not (args.ghe_user):
        parser.error(
            'GitHub Enterprise Admin user not set. Please use -ghe-user USER.'
        )

    if not (args.ghe_token):
        parser.error((
            'GitHub Enterprise Admin access token not set. Please use '
            '-ghe-token TOKEN.'
        ))

    if not (args.gh_token):
        parser.error(
            'GitHub.com User access token not set. Please use -gh-token TOKEN.'
        )

    if not (args.repos or args.all):
        parser.error(
            'No repos specified. Please select -repos, -file or -all.'
        )

    app = Migrate(
        source=args.source,
        dest=args.dest,
        ghe_host=args.ghe_host,
        ghe_ssh_port=args.ghe_ssh_port,
        ghe_ssh_user=args.ghe_ssh_user,
        ghe_user=args.ghe_user,
        ghe_token=args.ghe_token,
        gh_token=args.gh_token,
        verbose=args.verbose
    )

    if (args.all):
        app.load_repos()
    else:
        app.repos = app.validate_repos(args.source, args.repos)

    if len(app.repos) == 0:
        print('No repositories available to migrate.')
        sys.exit(1)

    repo_limit = args.batch
    if (args.skip > 0):
        print('Skipping first %d repositories.' % args.skip)
        app.repos = app.repos[args.skip:]

    while len(app.repos):
        repos = app.repos[:repo_limit]

        repos = app.start_repo_export(repos)
        repo_limit = len(repos)
        app.repos = app.repos[repo_limit:]

        app.download_archive()
        app.prepare_migration()
        app.resolve_conflicts()
        app.import_migration()
