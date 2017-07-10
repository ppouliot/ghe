__title__ = 'ghe'
__desc__ = 'GitHub Enterprise CLI Management Tool'
__version__ = '0.0.5'
__notes__ = 'Released 10 July 2017'
__author__ = 'Elliott Carlson'
__license__ = 'ISC'
__url__ = 'https://git.generalassemb.ly/ga-admin-utils/ghe'

from .ghe import GHE, GHECLI, get_key, set_key, unset_key

if __name__ == '__main__':
    ghe = GHECLI()
