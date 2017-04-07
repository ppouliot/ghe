ghe
===

GitHub Enterprise CLI Management Tool

Installation
------------

Using `pip <http://www.pip-installer.org>`_::

    [sudo] pip install https://git.generalassemb.ly/ga-admin-utils/ghe/releases/download/0.0.2/ghe-0.0.2.tar.gz

Usage
-----

To enter an interactive shell:

    $ ghe

To run a command directly:

    $ ghe <command name> [...args]

You can also import ghe directly; to run the interactive shell:

    from ghe import GHE
    app = GHE()
    app.cmdloop()

Extending ghe
-------------

Create a new executable file in your disired programming language of choice, named in a format of

    ghe-<command>.<ext>
    
As long as the file is named in this format, marked as an executable, and is located within the systems PATH, it will be
automatically found by ghe and added as a command.

If you are using python to create a new sub command, you can import ghe to access the shared keychain.

    from ghe import set_key, get_key, unset_key
    set_key('password', 'secret password')
    print(get_key('password'))
    unset_key('password')


    
