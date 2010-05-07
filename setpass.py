import keyring
import getpass
import sys

u = sys.argv[2]
e = sys.argv[1]
p = getpass.getpass("password?: ")

keyring.set_password(e, u, p)
