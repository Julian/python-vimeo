#!/usr/bin/env python

from distutils.core import setup

VERSION = '0.1.0'

setup(name='python-vimeo',
      version=VERSION,
      author='Julian Berman',
      author_email='Julian+Vimeo@GrayVines.com',
      url='http://github.com/mishk/python-vimeo',
      description='Python Vimeo API Bindings',
      download_url = 'http://github.com/mishk/python-vimeo',
      license='MIT',
      packages=['vimeo'],
      requires=['httplib2', 'oauth2'],
      classifiers = [
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Multimedia :: Video',
          ]
     )

