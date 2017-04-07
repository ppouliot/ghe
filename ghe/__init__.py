__title__ = 'ghe'
__desc__ = 'GitHub Enterprise CLI Management Tool'
__version__ = '0.0.2'
__notes__ = 'Released 7 April 2017'
__author__ = 'Elliott Carlson'
__license__ = 'ISC'
__url__ = 'https://git.generalassemb.ly/ga-admin-utils/ghe'

from .ghe import GHE, GHECLI

if __name__ == '__main__':
    ghe = GHECLI()
