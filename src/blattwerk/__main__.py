"""`python -m blattwerk invite [--admin]` prints the path of a one-use sign-up link."""

import sys

from blattwerk.auth import new_link
from blattwerk.db import open_db

if sys.argv[1:2] != ["invite"]:
    sys.exit(__doc__)
print("/einladung/" + new_link(open_db(), admin="--admin" in sys.argv))
