from requests import get
from json import loads
from re import compile as regexp
from xml.etree import ElementTree as ET # ... call home!

# Bunch of tokens that we're going to handle specially, the last
# rule matches all letters, in such case lexicographic comparison is
# used. In other cases the definition order of the token is used.
__tokens = (r'rc', r'pre', r'beta', r'alpha', '[a-zA-Z]*',)
# Select number from a string
__number = regexp(r'(\d*)')
# Split by dots (.), dashes (-) and whatever we define in `__tokens`
__splitter = regexp(r'\.|-|({})'.format('|'.join(__tokens))).split


def __split(data):
    """ Split the data using `__splitter` and filter out empties """
    return list(filter(None, __splitter(data)))


def __parse_vc(n):
    """ Parse version component """
    
    # Already an int, return
    if isinstance(n, int):
        return n

    # This part is one of our named `__tokens` so sort them
    # from left-right (hence the -1.0)
    if n in __tokens:
        return -1.0 * (__tokens.index(n) + 1)

    m = __number.match(n)
    if m.group():
        num = int(m.group())
        # Parsed number converted to a string is not equal
        # to the original string if the string contains some
        # extra characters and we sort these lower than 
        # purely numeric versions
        if str(num) == n:
            return num
        else:
            # these weirdos go last
            return len(__tokens)
    else:
        # Sort negatively so that 65 doesn't clash with ord('a') etc.
        # This also pushes textual version strings to the bottom
        # Note, one additional thing to do might be considering more than
        # the first character
        return -1.0 / ord(n[0])


def _version_compare(a, b, op=lambda x, y: x < y):
    """ Compare `a` and `b` using `op` """

    As, Bs = __split(a), __split(b)

    # Cardinalize
    La, Lb = len(As), len(Bs)
    if La > Lb:
        Bs += [0] * (La - Lb)
    elif Lb > La:
        As += [0] * (Lb - La)

    # Append length of the original string and compare by it as well
    As += [len(a)]
    Bs += [len(b)]

    # Remap as tuples so that we can use operators
    return op(tuple(map(__parse_vc, As)), tuple(map(__parse_vc, Bs)))


class ReleaseInfoModel:
    """ ReleaseInfoModel

    A class representing fetched information about release of 
    given `version` in the form of `released_at` date and, if 
    possible, SCM ID of the HEAD commit at the time of the release

    """
    def __init__(self, version, released_at, commit=None):
        self._version = version
        self._released_at = released_at
        self._commit = commit

    @property
    def version(self):
        return self._version

    @property
    def released_at(self):
        return self._released_at

    @property
    def commit(self):
        return self._commit

    def to_json_dict(self):
        return {'version': self.version, 
                'released_at': self.released_at.for_json(), 
                'commit': self.commit}

    def __lt__(self, other):
        return _version_compare(self.version, other.version)

    def __repr__(self):
        msg = '<Release version: {version}, released: {release}, commit={commit}>'
        return msg.format(version=self.version, 
                          release=self.released_at.humanize(),
                          commit=self.commit)


class BaseReleaseInfoFetcher:
    """ BaseReleaseInfoFetcher

    A base class for handling fetching release information
    from remote repositories

    """
    def __init__(self, url_base):
        self._url_base = url_base
        self._verbose = False

    @property
    def url_base(self):
        return self._url_base

    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, value):
        self._verbose = value

    def _url_for_package(self, package):
        """ Format URL with the package name so that we can call it """
        return self.url_base.format(package_name=package)

    def fetch_data(self, package):
        """ Fetch data for given `package` and return the `reuqets` object """
        import sys
        url = self._url_for_package(package)
        if self.verbose:
            msg = '{name} fetching info for `{package}` from: {url}'
            print(msg.format(name=self.__class__.__name__, url=url, 
                             package=package), 
                  file=sys.stderr)
        req = get(url)
        if self.verbose:
            print('- Status: {status}'.format(status=req.status_code), 
                  file=sys.stderr)
        return req

    def transform(self, data, package):
        """ Identity function by default """
        return data

    def fetch(self, package):
        """ Abstract method """
        raise NotImplementedError()


class JsonReleaseInfoFetcher(BaseReleaseInfoFetcher):
    """ JsonReleaseInfoFetcher

    A base class for JSON-based repositories

    """
    def fetch(self, package):
        return self.transform(self._fetch_json(package), package)

    def _fetch_json(self, package):
        return self.fetch_data(package).json()


class XmlReleaseInfoFetcher(BaseReleaseInfoFetcher):
    """ XmlReleaseInfoFetcher

    A base class for XML-based repositories
    
    """
    def fetch(self, package):
        return self.transform(self._fetch_xml(package), package)

    def _fetch_xml(self, package):
        return ET.fromstring(self.fetch_data(package).text)
