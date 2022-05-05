from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name = 'PySwitchbee',
    packages = ['switchbee'],
    install_requires=['asyncio', 'aiohttp'],
    version = '1.0.0',
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
        ],
    python_requires=">=3.6",
)