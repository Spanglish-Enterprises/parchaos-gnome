# SPDX-License-Identifier: GPL-3.0-or-later
# Runs the desktop widgets' gjs tests (ticket #165) when gjs is installed. Run:
#   python3 packaging/parchaos-widgets/tests/test_widgets.py
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if not shutil.which('gjs'):
    print('widgets: skipped (gjs not installed)')
    sys.exit(0)
sys.exit(subprocess.run(['gjs', '-m', os.path.join(HERE, 'test_layout.js')]).returncode)
