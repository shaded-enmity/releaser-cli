from releaser import JsonReleaseInfoFetcher, XmlReleaseInfoFetcher, ReleaseInfoModel
from requests import head
from arrow import get as datetime_new


class Urls:
    """ Definition of ecosystem specific urls """

    Cargo = 'https://crates.io/api/v1/crates/{package_name}/versions'
    Maven = 'http://repo1.maven.org/maven2/{package_name}/maven-metadata.xml'
    MavenHead = 'http://repo1.maven.org/maven2/{package_name}/{version}/{artifact}-{version}.jar'
    Npm = 'https://registry.npmjs.org/{package_name}'
    Nuget = 'https://api.nuget.org/v3/registration1/{package_name}/index.json'
    Pypi = 'https://pypi.python.org/pypi/{package_name}/json'
    RubyGems = 'https://rubygems.org/api/v1/versions/{package_name}.json'


class CargoReleaseFetcher(JsonReleaseInfoFetcher):
    """ CargoReleaseFetcher

    """
    def __init__(self):
        super().__init__(Urls.Cargo)

    def transform(self, data, packages):
        releases = []
        for release in data['versions']:
            releases.append(ReleaseInfoModel(release['num'], 
                            datetime_new(release['created_at'])))
        return releases


class MavenReleaseFetcher(XmlReleaseInfoFetcher):
    """ MavenReleaseFetcher

    """
    def __init__(self):
        super().__init__(Urls.Maven)

    def __sync_info_fetcher(self, package, version):
        # Get artifact name from the coordinate
        rest, artifact = package.rsplit('/', 1)
        url = Urls.MavenHead.format(package_name=package, artifact=artifact, 
                                    version=version)
        if self.verbose:
            import sys
            msg = '{name} fetching info for `{package}` at version `{version}` from: {url}'
            print(msg.format(name=self.__class__.__name__, url=url, 
                             package=package.replace('/', '.'), version=version), 
                  file=sys.stderr)

        # Since there's no metadata API/file to inspect we have to figure out
        # the age of the artifact by sending a HEAD request to the main
        # package Jar and inspect the `last-modified` HTTP header
        res = head(url)
        # Remove consecutive whitespaces
        last_mod = ' '.join(res.headers.get('last-modified', '').split())

        if last_mod:
            return datetime_new(last_mod, 'ddd, DD MMM YYYY H:mm:ss ZZZ')
        else:
            return None

    def fetch(self, package):
        return super().fetch(package.replace('.', '/'))

    def transform(self, data, package):
        releases = []
        versions = [v.text for v in data.find('versioning').find('versions').iter('version')]
        for version in versions:
            released_at = self.__sync_info_fetcher(package, version)
            releases.append(ReleaseInfoModel(version, released_at))
        return releases


class NpmReleaseFetcher(JsonReleaseInfoFetcher):
    """ NpmReleaseFetcher

    """
    bad_keys = ('modified', 'created',)

    def __init__(self):
        super().__init__(Urls.Npm)

    def transform(self, data, packages):
        releases = []
        for version, date in data['time'].items():
            commit = data['versions'].get(version, {}).get('gitHead')
            if version in NpmReleaseFetcher.bad_keys:
                continue
            releases.append(ReleaseInfoModel(version, datetime_new(date), 
                                             commit=commit))
        return releases


class NugetReleaseFetcher(JsonReleaseInfoFetcher):
    """ NugetReleaseFetcher

    """
    def __init__(self):
        super().__init__(Urls.Nuget)

    def fetch(self, package):
        # Nuget requires lowercase package names
        return super().fetch(package.lower())

    def transform(self, data, package):
        releases = []
        # there's always 1 element
        for item in data['items'][0]['items']:
            release = item['catalogEntry']
            releases.append(ReleaseInfoModel(release['version'], 
                                             datetime_new(release['published']), 
                                             commit=item['commitId']))
        return releases


class PypiReleaseFetcher(JsonReleaseInfoFetcher):
    """ PypiReleaseFetcher

    """
    def __init__(self):
        super().__init__(Urls.Pypi)

    def transform(self, data, package):
        releases = []
        for version, artifacts in data['releases'].items():
            times = [datetime_new(ri['upload_time']) for ri in artifacts]
            if times:
                releases.append(ReleaseInfoModel(version, min(times)))
        return releases


class RubyGemsReleaseFetcher(JsonReleaseInfoFetcher):
    """ RubyGemsReleaseFetcher

    """
    def __init__(self):
        super().__init__(Urls.RubyGems)

    def transform(self, data, package):
        releases = []
        for release in data:
            releases.append(ReleaseInfoModel(release['number'], 
                            datetime_new(release['created_at'])))
        return releases
