import os


# Configure the environment before pytest imports application or test modules.
os.environ["ENV"] = "TEST"

from consts import ENV, Environment


assert ENV == Environment.TEST
assert ENV == "TEST"
