[![Build Status](https://travis-ci.org/binrush/thousands.svg?branch=master)](https://travis-ci.org/binrush/thousands)

# South Ural summits project

This is a source code for http://1000.southural.ru/

## Running locally

1. You need python 2.7
2. Prepare empty postgresql database
3. Create virtualenv `virtualenv ~/virtualenv/thousands`
4. Clone repository
5. Install dependencies `~/virtualenv/thousands/bin/python setup.py develop`
6. Create configuration file (see below)
7. Run application. `THOUSANDS_CONF` environment variable should point to your configuration file `THOUSANDS_CONF="~/thousands.conf" ~/virtualenv/thousands/bin/python wsgi.py`

## Sample configuration file

```python
# Debug mode (should be disabled on production)
DEBUG=True
# Sessions secret key
SECRET_KEY="somesecretkey"
# Client secret for vk auth
VK_CLIENT_SECRET="vksecret"
# Client secret for southural.ru auth
SU_CLIENT_SECRET="susecret"
# Posgresql connection data
PG_DSN="host=localhost user=myuser password=mypassword dbname=mydb"
```
