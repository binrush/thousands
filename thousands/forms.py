# coding: utf-8

from wtforms import (
    Form, TextField, IntegerField, HiddenField,
    TextAreaField, SelectField, validators, Field)
from wtforms.widgets import TextInput
import datetime


class CoordinatesField(Field):

    widget = TextInput()

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data:
            return u'%.10f %.10f' % self.data
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            try:
                self.data = tuple(map(float, valuelist[0].split(' ')))
            except ValueError:
                raise validators.ValidationError(
                    u'Неправильно заданы координаты')
        else:
            self.data = None

    def pre_validate(self, form):
        if self.process_errors:
            raise validators.StopValidation()
        if self.data is not None:
            if not (self.data[0] > 0 and self.data[1] < 90):
                raise validators.ValidationError(
                    'Latitude should be between 0 and 90 degrees')

            if not (self.data[1] > 0 and self.data[1] < 180):
                raise validators.ValidationError(
                    'Longtitude should be between 0 and 180 degrees')


class ClimbDateField(Field):

    _date_format = '%d.%m.%Y'

    widget = TextInput()

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data:
            return unicode(datetime.datetime.strftime(self.data,
                                                      self._date_format))
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            try:
                self.data = datetime.datetime.strptime(
                    valuelist[0],
                    self._date_format).date()
            except ValueError:
                raise validators.ValidationError(u'Неправильно указана дата')
        else:
            self.data = None

    def pre_validate(self, form):
        if self.process_errors:
            raise validators.StopValidation()
        if self.data is not None and self.data > datetime.date.today():
            raise validators.ValidationError('Указана дата в будущем')


class SummitForm(Form):
    id = HiddenField('id')
    name = TextField('name')
    name_alt = TextField('name_alt')
    height = IntegerField('height', [validators.NumberRange(1000, 1640)])
    rid = SelectField('rid', coerce=int, choices=[(0, '---')])
    coordinates = CoordinatesField('coordinates',
                                   validators=[validators.DataRequired()])
    interpretation = TextAreaField('interpretation')
    description = TextAreaField('description')


class ClimbForm(Form):
    summit_id = HiddenField('summit_id')
    date = ClimbDateField(u'Дата')
    comment = TextAreaField(u'Комментарий')
