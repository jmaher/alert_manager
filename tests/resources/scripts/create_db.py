# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import sys

from config import get_config
from pyLibrary.sql.db import DB

configuration = get_config()

sys.stdout.write("THIS WILL OVERWRITE THE '%s' SCHEMA AT %s!! CONTINUE? [y/N]:" % (configuration["database"], configuration["host"]))
choice = raw_input().lower()
if choice not in ["yes", "y"]:
    exit()


DB.execute_file(configuration, "tests/resources/scripts/create_db.sql")
DB.execute_file(configuration, "tests/resources/sample_db/alerts.sql")
