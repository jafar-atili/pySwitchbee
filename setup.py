from setuptools import setup

setup(
    name = 'PySwitchbee',
    packages = ['switchbee'],
    install_requires=['request'],
    version = '0.1.0',
    description = 'A library to communicate with SwitchBee',
    author='Jafar Atili',
    url='https://github.com/jafar-atili/pySwitchbee/',
    license='',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules'
        ]
)