#!/usr/bin/env python

import setuptools

def long_description():
    with open('README.md', 'r') as f:
        return f.read()

setuptools.setup(
    name='pydv',
    version='0.1',
    author='Antony Chazapis',
    author_email='chazapis@gmail.com',
    description='D-STAR library and utilities in Python',
    long_description=long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/chazapis/pydv',
    license='GPLv2',
    packages=['pydv'],
    entry_points={'console_scripts': ['dv-recorder=pydv.recorder:main',
                                      'dv-player=pydv.player:main',
                                      'dv-decoder=pydv.decoder:main']},
    ext_modules=[setuptools.Extension(name='pydv.mbelib',
                                      sources=['pydv/mbelib.c'],
                                      libraries=['mbe'])],
    classifiers=['Environment :: Console',
                 'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python :: 2.7',
                 'Topic :: Communications :: Ham Radio']
)
