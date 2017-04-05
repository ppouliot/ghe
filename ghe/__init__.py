__version__ = '0.0.1'
__notes__ = 'Released 4 April 2017'
__author__ = 'Elliott Carlson'
__license__ = 'ISC'
__url__ = 'https://git.generalassemb.ly/ga-admin-utils/ghe'

from ghe import GHE, GHECLI 

if __name__ == '__main__':
    ghe = GHECLI()
