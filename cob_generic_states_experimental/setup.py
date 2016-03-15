#!/usr/bin/env python

from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup

d = generate_distutils_setup(
    # #  don't do this unless you want a globally visible script
    #scripts=['bin/cob_generic_states_experimental'], 
    packages=['cob_generic_states_experimental'],
    package_dir={'': 'src'}
)

setup(**d)