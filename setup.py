from setuptools import setup, find_packages

version = '1.0b10'

install_requires = [
    'setuptools',
    'rfxcom',
    'asyncio_redis',
    'iso8601',
    'tzlocal',
    'aiomysql',
    'aiohttp',
    'aiohttp_jinja2',
    ]

test_requires = [
    'nose',
    'asynctest',
    ]

setup(name='domopyc',
      version=version,
      description="Asychronous python utilities for domotic applications",
      author='Bruno Thomas',
      author_email='bthomas.domopyc@dune.io',
      url='http://github.com/bamthomas/DomoPyc',
      license='LICENSE',
      packages=find_packages(exclude=("*.tests", "*.tests.*", "tests.*", "tests", "*.test_utils")),
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      tests_require=test_requires,
      test_suite="nose.collector",
      entry_points = {
              'console_scripts': [
                  'domopyc = domopyc.domopyc_main:run_application'
              ]
          }
      )

