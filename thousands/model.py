# coding: utf-8
from flask.ext.login import UserMixin
from flask import url_for
import datetime
from gpxpy import gpx

AUTH_SRC_VK = 1
AUTH_SRC_SU = 2


class ModelException(Exception):
    pass


class InexactDate(tuple):

    def __new__(cls, *args):

        if len(args) > 3:
            raise TypeError("InexactDate() takes at most 3 arguments, {} given"
                            .format(len(args)))

        if len(args) == 3:
            datetime.date(args[0], args[1], args[2])
        elif len(args) == 2:
            datetime.date(args[0], args[1], 1)
        elif len(args) == 1:
            datetime.date(args[0], 1, 1)

        return tuple.__new__(cls, args)

    @classmethod
    def fromdate(cls, date):
        return cls(date.year, date.month, date.day)

    @classmethod
    def fromstring(cls, data):
        if not data:
            return cls()
        try:
            if len(data) == 4:
                return cls(int(data))
            else:
                return cls(*(reversed([int(f) for f in data.split('.')])))

        except (ValueError, TypeError) as e:
            raise ValueError("Wrong inexact date format: " + data, e)

    @classmethod
    def fromdict(cls, d):
        return InexactDate(*(
            [v for v in (d.get('year'), d.get('month'), d.get('day'))
             if v is not None]))

    def format(self):
        months_genitive = [
            u'Января', u'Февраля', u'Марта', u'Апреля', u'Мая', u'Июня',
            u'Июля', u'Августа', u'Сентября', u'Октября', u'Ноября',
            u'Декабря']
        months = [
            u'Январь', u'Февраль', u'Март', u'Апрель', u'Май', u'Июнь',
            u'Июль', u'Август', u'Сентябрь', u'Октябрь', u'Ноябрь',
            u'Декабрь']

        if len(self) == 3:
            return u'{} {} {}'.format(self[2],
                                      months_genitive[self[1] - 1],
                                      self[0])
        elif len(self) == 2:
            return u'{} {}'.format(months[self[1]-1], self[0])
        elif len(self) == 1:
            return unicode(self[0])
        else:
            return u''

    def __getpart(self, idx):
        return self[idx] if len(self) > idx else None

    @property
    def year(self):
        return self.__getpart(0)

    @property
    def month(self):
        return self.__getpart(1)

    @property
    def day(self):
        return self.__getpart(2)


class Summit(object):

    def __to_mins_secs(self, value):
        deg = int(value)
        mins = (value - deg)*60
        secs = (mins - int(mins))*60
        return u"{}{}{}'{}''".format(deg, u'\u00b0', int(mins), secs)

    def format_name(self):
        return self.name if self.name else str(self.height)

    def format_coordinates(self):
        return u'{} {} ({}{} {}{})'.format(
            self.coordinates[0],
            self.coordinates[1],
            self.__to_mins_secs(self.coordinates[0]),
            'N' if self.coordinates[0] >= 0 else 'S',
            self.__to_mins_secs(self.coordinates[1]),
            'E' if self.coordinates[1] >= 0 else 'W')

    def to_geojson(self):
        ret = {'type': 'Feature',
               'geometry': {"type": "Point"},
               'properties': {}}
        ret['id'] = self.id
        ret['geometry']['coordinates'] = \
            [self.coordinates[1], self.coordinates[0]]
        ret['properties']['height'] = self.height
        ret['properties']['name'] = self.format_name()
        ret['properties']['ridge'] = self.ridge
        ret['properties']['color'] = self.color
        ret['properties']['climbed'] = self.climbed
        ret['properties']['main'] = self.main

        return ret

    def to_gpx(self):
        wp = gpx.GPXWaypoint(
            latitude=self.coordinates[0],
            longitude=self.coordinates[1],
            elevation=self.height,
            name=self.format_name(),
            description=u'хр. ' + self.ridge)
        wp.link = url_for('summit', summit_id=self.id, _external=True)
        return wp


class SummitImage(object):

    def __init__(self, **kwargs):
        for k in kwargs:
            if k in ('image', 'preview', 'summit_id', 'comment', 'main'):
                setattr(self, k, kwargs[k])


class User(UserMixin):

    __auth_sources = {
        AUTH_SRC_VK:
            u'<a href="https://vk.com/id{}" target="_blank">' +
            u'Профиль ВКонтакте</a>',
        AUTH_SRC_SU:
            u'<a href="http://www.southural.ru/user/{}" target="_blank">' +
            u'Профиль на southural.ru</a>'
    }

    def social_link(self):
        return self.__auth_sources[self.src].format(self.oauth_id)


class Image(object):
    pass


class Climb(object):
    pass
