from setuptools import setup, find_packages

version = '1.0-beta'

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
    ]

setup(name='domopyc',
      version=version,
      description="Asychronous python utilities for domotic applications",
      author='Bruno Thomas',
      author_email='bthomas.domopyc@dune.io',
      url='http://github.com/bamthomas/DomoPyc',
      license='MIT',
      packages=find_packages('src', exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      package_dir = {'': 'src'},
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      tests_require=test_requires,
      test_suite="nose.collector",
      )

