from collections import OrderedDict, Iterable
from collections.abc import MutableMapping, Mapping
from inspect import isgenerator

class CaseInsensitiveDict(MutableMapping):
    def __init__(self, data=None, **kwargs):
        self._store = OrderedDict()
        if data is None:
            data = {}
        if isinstance(data, list) or isgenerator(data):
            self.add_items(data)
        else:
            self.update(data, **kwargs)

    def __setitem__(self, key, value):
        # Use the lowercased key for lookups, but store the actual
        # key alongside the value.
        self._store[key.lower()] = (key, [value])

    def __getitem__(self, key):
        return self._store[key.lower()][1][0]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (casedkey for casedkey, mappedvalues in self._store.values())

    def __len__(self):
        return sum(len(keyval[1]) for keyval in self._store.values())

    def iteritems(self):
        for key, values in self._store.values():
            for value in values:
                yield key, value

    def items(self):
        return list(self.iteritems())
    
    def add_items(self, item_iter):
        for key, value in item_iter:
            if not key.lower() in self._store:
                self._store[key.lower()] = (key, [])
            self._store[key.lower()][1].append(value)

    def get_all(self, key):
        if key.lower() in self._store:
            return self._store[key.lower()][1]

    def lower_items(self):
        """Like iteritems(), but with all lowercase keys."""
        return (
            (lowerkey, val)
            for val in keyval[1]
            for (lowerkey, keyval)
            in self._store.items()
        )

    def __eq__(self, other):
        if isinstance(other, Mapping):
            other = CaseInsensitiveDict(other)
        else:
            return NotImplemented
        # Compare insensitively
        return dict(self.lower_items()) == dict(other.lower_items())

    # Copy is required
    def copy(self):
        return CaseInsensitiveDict(self._store.values())

    def __repr__(self):
        return str(dict(self.items()))