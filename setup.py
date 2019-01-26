# -*- coding: utf-8 -*-
import os

from distutils.core import setup


here = os.path.abspath(os.path.dirname(__file__))

version_ns = {}

with open(os.path.join(here, "pyswrve", "__version__.py")) as f:
    exec(f.read(), version_ns)

setup(
    name='pyswrve',
    version=version_ns['__version__'],
    license='MIT License',
    url='https://github.com/xxblx/pyswrve',

    author='Oleg Kozlov',
    author_email='xxblx@posteo.org',

    description='Unofficial Python wrapper for Swrve Non-Client APIs',
    long_description="""pyswrve is an unofficial Python wrapper for
Swrve Non-Client APIs: Export API (ready) and Items API (todo).""",

    requires=['requests'],
    platforms=['any'],
    packages=['pyswrve'],

    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
    ],
    keywords='swrve api wrapper'
)
