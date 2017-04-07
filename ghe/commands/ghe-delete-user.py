#!/usr/bin/env python
from seleniumrequests import PhantomJS
import os, sys

ghe_host = os.environ.get('ghe-host')
ghe_user = os.environ.get('ghe-user')
ghe_pass = os.environ.get('ghe-pass')

if not ghe_host:
    print('ghe-host variable not set.')
    sys.exit()

if not ghe_user:
    print('ghe-user variable not set.')
    sys.exit()

if not ghe_pass:
    print('ghe-pass variable not set.')
    sys.exit()

username = sys.argv[1]
if not username:
    print("usage: delete-user <username>")
    sys.exit()

driver = PhantomJS()
driver.implicitly_wait(10)
driver.set_window_size(1400, 850)
driver.get('https://%s/login' % (ghe_host))

driver.find_element_by_name('login').send_keys(ghe_user)
driver.find_element_by_name('password').send_keys(ghe_pass)
driver.find_element_by_name('commit').click()

driver.get('https://%s/stafftools/users/%s/admin' % (ghe_host, username))

if 'Page not found' in driver.title or username.lower() not in driver.title.lower():
    print('User not found, or insufficient access rights to admin users.')
    sys.exit()

base = '#confirm_deletion form input'
u = driver.find_element_by_css_selector('%s[name=utf8]' % base)
m = driver.find_element_by_css_selector('%s[name=_method]' % base)
t = driver.find_element_by_css_selector('%s[name=authenticity_token]' % base)

driver.request('POST', 'https://%s/stafftools/users/%s' % (ghe_host, username),
    data={
        'utf8': u.get_attribute('value'),
        '_method': m.get_attribute('value'),
        'authenticity_token': t.get_attribute('value')
    }
)
