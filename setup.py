from setuptools import setup

setup(name='thousands',
      version='1.0.1',
      description='Site for South Ural moultains climbers',
      author='Rushan Shaymardanov',
      author_email='rush.ru@gmail.com',
      install_requires=[
          'psycopg2',
          'Flask==0.10.1',
          'flask-login==0.3.2',
          'wtforms',
          'yoyo-migrations==4.2.5',
          'google-api-python-client',
          'bleach'],
      tests_require=['mock'],
      test_suite="tests")
