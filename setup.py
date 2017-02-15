#!/usr/bin/env python3
import setuptools
setuptools.setup(
    name = 'releaser',
    version = open('VERSION').read(),
    packages = setuptools.find_packages(),
    install_requires = ['requests', 'arrow'],
    package_data = {
       '': ['LICENSE', 'README.md', 'VERSION']
    },
    author = 'Pavel Odvody',
    author_email = 'podvody@redhat.com',
    description = 'Release version/date information fetcher',
    license = 'GNU/GPLv2',
    keywords = 'release version name fetcher',
    url = '',
    classifiers=[
        "Programming Language :: Python :: 3 :: Only"
    ]
)
