#!/usr/bin/env python
"""
ghe-org-diff.py - GitHub.com and GitHub Enterprise Org Diff

usage: ghe-org-diff.py [-h] [-ghe-host HOST] [-ghe-token TOKEN]
                       [-gh-token TOKEN]
                       source [dest]

Tool to determine if the repos on two organizations match on the source
GitHub.com and destination GitHub Enterprise server.


positional arguments:
  source            the organization on GitHub.com
  dest              the organization on your GitHub Enterprise instance.

optional arguments:
  -h, --help        show this help message and exit
  -ghe-host HOST    the hostname to your GitHub Enterprise server (default:
                    value from `ghe-host` environment variable)
  -ghe-token TOKEN  GitHub Enterprise access token for user set with -ghe-user
                    (default: value from `ghe-token` environment variable)
  -gh-token TOKEN   GitHub.com access token for an account with admin
                    priveleges on source organization (default: value from
                    `gh-token` environment variable)
"""

import argparse, csv, math, os, paramiko, re, requests, sys, tempfile, time

from ghe import get_key
from github import Github
from github.GithubException import GithubException
from subprocess import call
from io import StringIO

from builtins import input
from pprint import pprint

class OrgDiff(object):

    def __init__(self, **kwargs): #token, source_org):
        ''' Constructor. '''

        self.source_org = kwargs.get('source')
        self.dest_org = kwargs.get('dest', self.source_org)
        self.ghe_host = kwargs.get('ghe_host')
        self.ghe_token = kwargs.get('ghe_token')
        self.gh_token = kwargs.get('gh_token')

        self.gh_repos = []
        self.ghe_repos = []

        self.gh = Github(self.gh_token)
        self.ghe = Github(self.ghe_token, base_url=self.ghe_host)

    def load_repos(self, gh, org):
        ''' Retrieve all the repositories in the organization. '''

        repos = []

        try:
            for repo in gh.get_organization(org).get_repos():
                repos.append(repo.name)
        except:
            print((
                'Unable to retrieve the organization. Please confirm you have '
                'the right organization name and have sufficient credentials '
                'to access the organization on GitHub.'
            ))
            sys.exit(1)

        return repos

    def get_repo(self, gh, org, name):
        return gh.get_organization(org).get_repo(name)

    def diff_repos(self, repos):
        for repo in repos:
            gh_repo = self.get_repo(self.gh, self.source_org, repo)
            ghe_repo = self.get_repo(self.ghe, self.dest_org, repo)

            if self.get_repo_head(gh_repo) != self.get_repo_head(ghe_repo):
                print('??? {0}'.format(repo))
                print('--- GH SHA: {0}'.format(self.get_repo_head(gh_repo)))
                print('--- GHE SHA: {0}'.format(self.get_repo_head(ghe_repo)))

    def get_repo_head(self, repo):
        try:
            return repo.get_commits()[0].sha
        except GithubException as err:
            if err.status == 409:
                return err.data.get('message')
            else:
                print('UNKNOWN ERR')
                pprint(err)
                sys.exit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=('Tool to determine if the repos on two organizations '
            'match on the source GitHub.com and destination GitHub Enterprise '
            'server.'
        )
    )
    parser.add_argument('source',
        help='the organization on GitHub.com'
    )
    parser.add_argument('dest',
        nargs='?',
        help='the organization on your GitHub Enterprise instance.'
    )

    parser.add_argument('-ghe-host',
        help=(
            'the hostname to your GitHub Enterprise server '
            '(default: value from `ghe-host` environment variable)'
        ),
        metavar='HOST',
        default=os.getenv('ghe-host')
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

    if not (args.ghe_token):
        parser.error((
            'GitHub Enterprise Admin access token not set. Please use '
            '-ghe-token TOKEN.'
        ))

    if not (args.gh_token):
        parser.error(
            'GitHub.com User access token not set. Please use -gh-token TOKEN.'
        )

    app = OrgDiff(
        source=args.source,
        dest=args.dest,
        ghe_host='https://{0}/api/v3'.format(args.ghe_host),
        ghe_token=args.ghe_token,
        gh_token=args.gh_token
    )

    print('Comparing https://github.org/{0}/* to {1}/{2}'.format(
        app.source_org,
        app.ghe_host,
        app.dest_org
    ))

    app.gh_repos = app.load_repos(app.gh, app.source_org)
    app.ghe_repos = app.load_repos(app.ghe, app.dest_org)

    if len(app.gh_repos) == 0:
        print('No repositories found in source org.')
        sys.exit(1)

    if len(app.ghe_repos) == 0:
        print('No repositories found in destnation org.')
        sys.exit(1)

    # Find the intersection of the two -- TODO: Do something with repos that do
    # not exist on both!!
    repos = list(set(app.gh_repos).intersection(app.ghe_repos))

    app.diff_repos(repos)
    sys.exit()

