from setuptools import setup

setup(name='thousands',
      version='0.3.0',
      description='Site for South Ural moultains climbers',
      author='Rushan Shaymardanov',
      author_email='rush.ru@gmail.com',
      install_requires=['psycopg2', 'Flask', 'flask-login', 'wtforms', 'yoyo-migrations', 'google-api-python-client']
     )
