
import os
import sys
from importlib import import_module

from managed_settings import *


TARGET_ENV = os.environ.get('TARGET_ENVIRONMENT', 'PRODUCTION')
_settings_path = os.path.join('local_settings.%s' % TARGET_ENV.lower())
_settings_module = import_module(_settings_path)


this_module = sys.modules[__name__]
for setting in dir(_settings_module):
    if setting.isupper():
        setting_value = getattr(_settings_module, setting)
        setattr(this_module, setting, setting_value)

del this_module

TEMP_CSET_DIR = 'tmpcset'
MAILDIR = '/var/spool/news/mozilla/dev/tree-management'
