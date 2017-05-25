#!/usr/bin/env python
"""
usage: ghe-reset-user-email.py [-h] [-ghe-host HOST] [-ghe-user USER]
                               [-ghe-pass PASS] [-ghe-totp KEY] [-debug]
                               USERNAME EMAIL

Tool to update a users email address on Github Enterprise.

positional arguments:
  USERNAME        username to update
  EMAIL           email address to set.

optional arguments:
  -h, --help      show this help message and exit
  -ghe-host HOST  the hostname to your GitHub Enterprise server (default:
                  value from `ghe-host` environment variable)
  -ghe-user USER  username of a Github Enterprise user with admin priveleges.
  -ghe-pass PASS  password of user passed in with -ghe-user.
  -ghe-totp KEY   base 32 secret to generate two-factor key
  -debug          enable debug mode
"""

import argparse, os, pyotp, re, sys
from seleniumrequests import PhantomJS

class FixUserEmail(object):

    def __init__(self, **kwargs):
        ''' Constructor. '''

        self.ghe_host = kwargs.get('ghe_host')
        self.ghe_user = kwargs.get('ghe_user')
        self.ghe_pass = kwargs.get('ghe_pass')
        self.ghe_totp = kwargs.get('ghe_totp')
        self.debug = kwargs.get('debug', False)

    def update(self, user, email):
        ''' Reset the users email address on Github Enterprise '''

        # Initialize the PhantomJS selenium driver
        driver = PhantomJS()
        driver.implicitly_wait(10)
        driver.set_window_size(1400, 850)

        # Login as the admin user
        driver.get('https://%s/login' % (self.ghe_host))
        driver.find_element_by_name('login').send_keys(self.ghe_user)
        driver.find_element_by_name('password').send_keys(self.ghe_pass)
        driver.find_element_by_name('commit').click()

        # Check for two-factor auth code request
        if driver.current_url == 'https://%s/sessions/two-factor' % self.ghe_host:
            if self.ghe_totp:
                base = '.auth-form-body input'
                u = driver.find_element_by_css_selector('%s[name=utf8]' % base)
                t = driver.find_element_by_css_selector('%s[name=authenticity_token]' % base)
                otp = pyotp.TOTP(self.ghe_totp)

                driver.request('POST', 'https://%s/sessions/two-factor' % self.ghe_host,
                    data={
                        'utf8': u.get_attribute('value'),
                        'otp': otp.now(),
                        'authenticity_token': t.get_attribute('value')
                    }
                )
            else:
                print('Two-Factor authentication required.')
                sys.exit()

        # Retrieve the email admin page for the designated user to be updated
        driver.get('https://%s/stafftools/users/%s/emails' % (self.ghe_host, user))

        # Ensure that we were able to access the requested admin page
        if 'Page not found' in driver.title or user.lower() not in driver.title.lower():
            print('User not found, or insufficient access rights.')
            sys.exit()

        # Locate the necessary inputs to be able to add an email address
        base = 'form[action="/stafftools/users/%s/emails"] input' % user
        u = driver.find_element_by_css_selector('%s[name=utf8]' % base)
        t = driver.find_element_by_css_selector('%s[name=authenticity_token]' % base)

        # Send the add email address request
        driver.request('POST', 'https://%s/stafftools/users/%s/emails' % (self.ghe_host, user),
            data={
                'utf8': u.get_attribute('value'),
                'email': email,
                'authenticity_token': t.get_attribute('value')
            }
        )

        # Send password reset to new email address
        base = 'form[action="/stafftools/users/%s/password/send_reset_email"] input' % user
        u = driver.find_element_by_css_selector('%s[name=utf8]' % base)
        t = driver.find_element_by_css_selector('%s[name=authenticity_token]' % base)
        m = driver.find_element_by_css_selector('%s[name=_method]' % base)
        driver.request('POST', 'https://%s/stafftools/users/%s/password/send_reset_email' % (self.ghe_host, user),
            data={
                'utf8': u.get_attribute('value'),
                'email': email,
                'authenticity_token': t.get_attribute('value'),
                '_method': m.get_attribute('value')
            }
        )

        # Get password reset link and display to console
        driver.get('https://%s/stafftools/users/%s/emails' % (self.ghe_host, user))
        if email in driver.page_source:
            print('Email added and password reset email sent.')
        else:
            print('New email not showing up on user page; please check manually.')


class EmailType(object):
    """
    Supports checking email agains different patterns. The current available patterns is:
    RFC5322 (http://www.ietf.org/rfc/rfc5322.txt)
    """

    patterns = {
        'RFC5322': re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
    }

    def __init__(self, pattern):
        if pattern not in self.patterns:
            raise KeyError('{} is not a supported email pattern, choose from:'
                           ' {}'.format(pattern, ','.join(self.patterns)))
        self._rules = pattern
        self._pattern = self.patterns[pattern]

    def __call__(self, value):
        if not self._pattern.match(value):
            raise argparse.ArgumentTypeError(
                "'{}' is not a valid email - does not match {} rules".format(value, self._rules))
        return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Tool to update a users email address on Github Enterprise.'
    )
    parser.add_argument('user',
        help='username to update',
        metavar='USERNAME'
    )
    parser.add_argument('email',
        help='email address to set.',
        metavar='EMAIL',
	type=EmailType('RFC5322')
    )
    parser.add_argument('-ghe-host',
        help=(
            'the hostname to your GitHub Enterprise server '
            '(default: value from `ghe-host` environment variable)'
        ),
        metavar='HOST',
        default=os.getenv('ghe-host')
    )
    parser.add_argument('-ghe-user',
        help='username of a Github Enterprise user with admin priveleges.',
        metavar='USER',
        type=str,
        default=os.getenv('ghe-user')
    )
    parser.add_argument('-ghe-pass',
        help='password of user passed in with -ghe-user.',
        metavar='PASS',
        type=str,
        default=os.getenv('ghe-pass')
    )
    parser.add_argument('-ghe-totp',
        help='base 32 secret to generate two-factor key',
        metavar='KEY',
        type=str,
        default=os.getenv('ghe-totp')
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

    if not (args.ghe_user):
        parser.error(
            'GitHub Enterprise admin user not set. Please use -ghe-user USER.'
        )

    if not (args.ghe_pass):
        parser.error(
            'GitHub Enterprise admin password not set. Please use -ghe-pass PASS.'
        )

    app = FixUserEmail(
        ghe_host=args.ghe_host,
        ghe_user=args.ghe_user,
        ghe_pass=args.ghe_pass,
        ghe_totp=args.ghe_totp,
        debug=args.debug
    )

    print('Setting "%s" email address to "%s"...' % (args.user, args.email))
    app.update(args.user, args.email)
