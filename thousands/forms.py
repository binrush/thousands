from wtforms import Form, TextField, IntegerField, HiddenField, TextAreaField, SelectField, validators

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

class SummitForm(Form):
    id = HiddenField('id')
    name = TextField('name')
    name_alt = TextField('name_alt')
    height = IntegerField('height', [ validators.NumberRange(1000, 1640) ])
    rid = SelectField('rid', coerce=int, choices=[(0, '---')])
    coordinates = TextField('coordinates', validators=[ validators.DataRequired(), validate_coordinates ])
    interpretation = TextAreaField('interpretation')
    description = TextAreaField('description')


