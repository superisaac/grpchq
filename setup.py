#!/usr/bin/env python

"""Setup tool for grpchq."""

import setuptools

setuptools.setup(
    name='grpchq',
    version='0.0.2',
    description='projects and utilities related to gRPC',
    author='zengke',
    author_email='superisaac.ke@gamil.com',
    url='https://github.com/superisaac/grpchq',
    license='MIT',
    install_requires=(
        'django >= 2.2.0',
        'grpcio >= 1.31.0',
        'grpcio-tools >= 1.31.0',
        'protobuf >= 3.12.4',
    ),
    packages=setuptools.find_packages(exclude=['examples']),
    entry_points={
        'console_scripts': [
            'grpcl = grpchqtools.grpcl:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
    ]
)
