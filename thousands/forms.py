# coding: utf-8

from wtforms import (
    Form, TextField, IntegerField, HiddenField,
    TextAreaField, SelectField, FileField, validators, Field)
from wtforms.widgets import TextInput, HiddenInput
from wtforms.csrf.session import SessionCSRF
import datetime
import dao


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
                    u'Широта должна быть между 0 и 90 градусов')

            if not (self.data[1] > 0 and self.data[1] < 180):
                raise validators.ValidationError(
                    u'Долгота должна быть между 0 и 180 градусов')


class ClimbDateField(Field):

    _date_format = '%d.%m.%Y'

    widget = TextInput()

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data:
            return \
                u'.'.join(
                    [str(f) for f in reversed(self.data)
                        if f is not None])
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = dao.InexactDate.fromstring(valuelist[0])
            except ValueError:
                raise validators.ValidationError(u'Неправильно указана дата')
        else:
            self.data = None

    def pre_validate(self, form):
        if self.process_errors:
            raise validators.StopValidation()
        if self.data is not None and self.data > \
                dao.InexactDate.fromdate(datetime.date.today()):
            raise validators.ValidationError(u'Указана дата в будущем')


class ThousandsBaseForm(Form):
    class Meta:
        csrf = True
        csrf_class = SessionCSRF
        csrf_time_limit = datetime.timedelta(minutes=60)


class SummitForm(ThousandsBaseForm):
    id = HiddenField()
    name = TextField(u'Название', filters=[lambda x: x or None])
    name_alt = TextField(u'Варианты названия', filters=[lambda x: x or None])
    height = IntegerField(u'Высота', [validators.NumberRange(1000, 1640)])
    rid = SelectField(u'Хребет', coerce=int, choices=[(0, '---')])
    coordinates = CoordinatesField(u'Координаты',
                                   validators=[validators.DataRequired()])
    interpretation = TextAreaField(u'Расшифровка названия',
                                   filters=[lambda x: x or None])
    description = TextAreaField(u'Описание', filters=[lambda x: x or None])


class SummitImageForm(ThousandsBaseForm):
    summit_id = HiddenField()
    comment = TextField(u'Название', filters=[lambda x: x or None])


class SummitImageEditForm(SummitImageForm):
    action = TextField(validators=[validators.AnyOf(('update', 'delete'))])


class SummitImageUploadForm(SummitImageForm):
    image = FileField(u'Файл изображения')


class ClimbForm(ThousandsBaseForm):
    MAX_COMMENT_SIZE = 1000

    summit_id = HiddenField()
    date = ClimbDateField(u'Дата')
    comment = TextAreaField(u'Комментарий',
                            [validators.Length(max=MAX_COMMENT_SIZE)])


class DeleteForm(ThousandsBaseForm):
    pass


class ImageUploadForm(ThousandsBaseForm):
    x = IntegerField(widget=HiddenInput(),
                     validators=[validators.DataRequired(),
                                 validators.NumberRange(0)])
    y = IntegerField(widget=HiddenInput(),
                     validators=[validators.DataRequired(),
                                 validators.NumberRange(0)])

    width = IntegerField(widget=HiddenInput(),
                         validators=[validators.DataRequired(),
                                     validators.NumberRange(0)])

    height = IntegerField(widget=HiddenInput(),
                          validators=[validators.DataRequired(),
                                      validators.NumberRange(0)])

    image = FileField()
