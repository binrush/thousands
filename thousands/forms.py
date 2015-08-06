# coding: utf-8

from wtforms import Form, TextField, IntegerField, HiddenField, TextAreaField, SelectField, validators, Field
from wtforms.widgets import TextInput
import datetime

def validate_coordinates(form, field):
    try:
        str_lat, str_lng = field.data.split()
        lat = float(str_lat.strip())
        lng = float(str_lat.strip())
    except:
        raise validators.ValidationError('Wrong format for coordinates field')

    if not (lat > 0 and lat < 90):
        raise validators.ValidationError('Latitude should be between 0 and 90 degrees')

    if not (lng > 0 and lng < 180):
        raise validators.ValidationError('Longtitude should be between 0 and 180 degrees')

def validate_date(form, field):
    try:
        d = datetime.datetime.strptime('%d.%m.%Y', field.data)
    except ValueError:
        raise validators.ValidationError('Неправильно указана дата')

    if d > datetime.date.today():
        raise validators.ValidationError('Указана дата в будущем')

class ClimbDateField(Field):

    _date_format = '%Y-%m-%d'

    widget = TextInput()

    def _value(self):
        if self.data:
            return unicode(datetime.datetime.strftime(self._date_format, self.data))
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = datetime.datetime.strptime(self._date_format, valuelist)
        else:
            self.data = None

    def pre_validate(form):
        try:
            d = datetime.datetime.strptime('%d.%m.%Y', self.data)
        except ValueError:
            raise validators.ValidationError('Неправильно указана дата')

        if d > datetime.date.today():
            raise validators.ValidationError('Указана дата в будущем')


class SummitForm(Form):
    id = HiddenField('id')
    name = TextField('name')
    name_alt = TextField('name_alt')
    height = IntegerField('height', [ validators.NumberRange(1000, 1640) ])
    rid = SelectField('rid', coerce=int, choices=[(0, '---')])
    coordinates = TextField('coordinates', validators=[ validators.DataRequired(), validate_coordinates ])
    interpretation = TextAreaField('interpretation')
    description = TextAreaField('description')

class ClimbForm(Form):
    summit_id = HiddenField('sid')
    date = ClimbDateField(u'Дата', validators=[ validate_date ])
    comment = TextAreaField(u'Комментарий')
