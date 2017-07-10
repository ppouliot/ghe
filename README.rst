GHE CLI
=======

GHE CLI is a tool to assist is managing Github Enterprise remotely from the
command line. It offers the ability to run sub-commands directly, or via an
interactive shell, and maintains access to safely secured variables.

Installation
------------

Using pip:

.. code-block:: bash

    $ sudo pip install https://git.generalassemb.ly/ga-admin-utils/ghe/releases/download/0.0.5/ghe-0.0.5.tar.gz

Interactive Shell
-----------------

To enter the interactive shell, run `ghe` from the command line:

.. code-block::

    $ ghe
    GHE> <command name> [...args]

Once you are in the interactive shell, you will see the `GHE>` prompt; this is
where you can type in commands that have been registered with the system. See
the `Commands` section for further details.

The interactive shell has various built in commands:

Get a list of registered commands:

.. code-block::

    GHE> help
    Available ghe commands are:
      migrate
      reset-user-email
      org-diff
      maintenance
      announce
      delete-user
    GHE>

Set a key-value pair in the keychain:

.. code-block::

    GHE> set keyname value
    GHE>

Get a value from the keychain based on the key name:

.. code-block::

    GHE> get keyname
    value
    GHE>

Clear a key-value pair from the keychain:

.. code-block::

    GHE> unset keyname
    GHE>

The interactive shell provides tab-completion of commands, and can provide a
listing of commands by pressing tab twice.

Direct Command Line Access
--------------------------

In addition to the interactive shell, commands can be executed directly from ghe
via the command line.

.. code-block::

    $ ghe <command name> [...args]

Running commands from the command line provides the same benefits that the
interactive shell offers.

Interactive Shell from Custom Code
----------------------------------

Finally, the interactive shell can be directly launched from python:

.. code-block:: python

    from ghe import GHE
    app = GHE()
    app.cmdloop() # Launches the interactive shell

Commands
--------
`ghe` registers commands by finding executable scripts following a specific naming
convention. On startup, ghe searches the `PATH` environment, as well as the
commands directory that comes with ghe to auto-register all executable scripts
based on the `ghe-<command>.<ext>`. The command portion of the filename is what
gets registered as the command in ghe. For example, if the file is named
`ghe-test.sh`, then the command `test` will execute the corresponding script name.

Following are a list of commands that are pre-installed with ghe (Wiki links to come):

* `ghe-announce`_
* `ghe-delete-user`_
* `ghe-maintenance`_
* `ghe-migrate`_
* `ghe-org-diff`_
* `ghe-reset-user-email`_

One key feature that ghe provides to the subcommands is access to the shared
keychain. Since ghe maintains the key-value pairs within the systems keychain
(OSX keyring), it is able to share the data privately to the subcommands via a
localized environment that is shared when ghe creates the subprocess to call the
subcommands. By setting these private environment variables, the secrets are
shared with all sub-commands, without requiring to give the subcommands access
to the keychain.

The keynames of the keychain values that are set in the local environment for
every process call are:

* `ghe-host` -  The hostname to the GHE server
* `ghe-ssh-user` - The SSH username to the GHE server
* `ghe-ssh-port` - The SSH port of the GHE server
* `ghe-user` - A GHE admin level user
* `ghe-pass` - The password for the GHE admin level account
* `ghe-token` - An access token for the GHE admin level account
* `gh-token` - An access token to your GitHub.com account
* `ghe-totp` - An authenticator code to generate OTP/2FA codes

Part of your initial setup of ghe should be setting the values of these keys.
See Setup for more information.

Additionally, if one were writing their subcommands in python, the keychain can
be directly accessed (for the primary set of key-value pairs that are needed by
ghe, or customized ones that your subcommands may need). This can be done using
the following example code:

.. code-block:: python

    from ghe import get_key, set_key, unset_key

    set_key('my_key_name', 'my_key_value')
    print(get_key('my_key_name')) # outputs my_key_value
    unset_key('my_key_name')
    print(get_key('my_key_name')) # outputs None

Setup
-----

On initial setup of ghe, it is recommended to set up the initial key-value pairs
in the keychain that most subcommands will expect to be set to function properly. 

.. code-block::

    GHE> set ghe-host git.generalassemb.ly
    GHE> set ghe-ssh-user admin
    GHE> set ghe-ssh-port 122
    GHE> set ghe-user ghe-admin
    GHE> set ghe-pass secretpassword
    GHE> set ghe-token ABCDEF1234567890
    GHE> set gh-token ABCDEF1234567890
    GHE> set ghe-totp ABCDEF1234567890

Additionally, you should have registered an SSH key on your machine within the
Github Enterprise Management Console. See SSH Access for more information.

.. _ghe-announce: https://git.generalassemb.ly/ga-admin-utils/ghe/wiki/ghe%E2%80%90announce
.. _ghe-delete-user: https://git.generalassemb.ly/ga-admin-utils/ghe/wiki/ghe%E2%80%90delete%E2%80%90user
.. _ghe-reset-user-email: https://git.generalassemb.ly/ga-admin-utils/ghe/wiki/ghe%E2%80%90reset%E2%80%90user%E2%80%90email
.. _ghe-maintenance: https://git.generalassemb.ly/ga-admin-utils/ghe/wiki/ghe%E2%80%90maintenance
.. _ghe-migrate: https://git.generalassemb.ly/ga-admin-utils/ghe/wiki/ghe%E2%80%90migrate
.. _ghe-org-diff: https://git.generalassemb.ly/ga-admin-utils/ghe/wiki/ghe%E2%80%90org%E2%80%90diff
