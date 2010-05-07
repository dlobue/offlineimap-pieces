from sqlobject import *
from collections import namedtuple


class folder(SQLObject):
    #uuid = StringCol(alternateID=True)
    name = StringCol()
    path = StringCol(alternateID=True)
    ruidvalidity = IntCol()
    luidvalidity = IntCol()
    messages = MultipleJoin('message')

class content(SQLObject):
    hash = StringCol(alternateID=True)
    msgid = StringCol(alternateID=True)
    rfcsize = StringCol()
    internaldate = StringCol()
    messages = MultipleJoin('message')

class message(SQLObject):
    flags = StringCol()
    remoteuid = StringCol()
    #remoteuidIndex = DatabaseIndex('folder', 'remoteuid', unique=True)
    localuid = StringCol()
    #localuidIndex = DatabaseIndex('folder', 'localuid', unique=True)
    folder = ForeignKey('folder', cascade=False)
    content = ForeignKey('content', cascade=False)


synctoken_fields = ('localrepo', 'remoterepo', 'folder')
_synctoken = namedtuple('synctoken', synctoken_fields)

class synctoken(_synctoken): pass

class flags(object):
    __slots__ = 'D', 'F', 'R', 'S', 'T'

    def __init__(self, flags):
        self._reset()
        self._update(flags)

    def __eq__(self, other):
        lambid = lambda x: getattr(self, x) is getattr(other, x)
        res = all(map(lambid, self.__slots__))
        return res

    def __ne__(self, other):
        return not self.__eq__(other)

    def __iter__(self):
        return (getattr(self, x) for x in self.__slots__)

    def __reprno__(self):
        s = '<flags %s>' % self.__str__()
        return s

    def __str__(self):
        s = [x for x in self.__slots__ if getattr(self, x)]
        s = ''.join(s)
        return s

    __repr__ = __str__

    def _combined(self, update):
        self._reset()
        zupdate = zip(*[update, self.__slots__])
        [ setattr(self, y, x) for x,y in zupdate ]

    def _reset(self):
        map(lambda x: setattr(self, x, False), self.__slots__)

    def _update(self, new_flags):
        flagmap = {'seen': 'S',
                   'answered': 'R',
                   'flagged': 'F',
                   'deleted': 'T',
                   'draft': 'D'}
        if type(new_flags) is flags:
            map(lambda x:
                    setattr(self, x, getattr(new_flags, x)), self.__slots__)
            return
        elif not hasattr(new_flags, '__iter__'):
            if '\\' in new_flags or ' ' in new_flags:
                new_flags = new_flags.split()
            new_flags = (x for x in new_flags)

        def lambset(x):
            try:
                setattr(self, flagmap.get(x.strip('\\ ').lower(),
                                                    x.upper()), True)
            except AttributeError, e:
                #FIXME add in logging system of some sort to capture more data
                pass

        map(lambset, new_flags)

def combine_flags(cached, local, remote):
    zflags = zip(*[cached, local, remote])
    results = [ flag_distill(c,a,b) for c,a,b in zflags ]
    cached._combined(results)
    return cached

def flag_distill(cached, a,b):
    cached = cached, 0
    def combine(a,b):
        if a[1]: return a
        if a[0] is b: return a
        return b,1
    cached = combine(cached, a)
    cached = combine(cached, b)
    return cached[0]
