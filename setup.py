from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        pytest.main(self.test_args)


setup(name='thousands',
      version='1.0.0',
      description='Site for South Ural moultains climbers',
      author='Rushan Shaymardanov',
      author_email='rush.ru@gmail.com',
      install_requires=[
          'psycopg2',
          'Flask==0.12.1',
          'flask-login==0.4',
          'Flask-WTF',
          'yoyo-migrations==4.2.5',
          'bleach',
          'gpxpy',
          'Pillow',
          'transliterate',
          'Flask-OAuthlib'],
      tests_require=['mock', 'pytest', 'blinker'],
      cmdclass = {'test': PyTest})
