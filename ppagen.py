import datetime
import argparse
import os
import urlparse
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import yaml

# NAMES OF THE XML ELEMENTS
REL_REL = 'release:release'
REL_PN = 'release:productName'
REL_PSN = 'release:productShortName'
REL_TP = 'release:technologyProvider'
REL_TPSN = 'release:technologyProviderShortName'
REL_CONT = 'release:contact'
REL_TECHCONT = 'release:technicalContact'
REL_DESC = 'release:description'
REL_DOCLINK = 'release:documentationLink'
REL_ISODATE = 'release:ISODate'
REL_INC = 'release:incremental'
REL_EMRGC = 'release:emergency'
REL_MAJOR = 'release:majorVersion'
REL_MINOR = 'release:minorVersion'
REL_REV = 'release:revisionVersion'
REL_NOTES = 'release:releaseNotes'
REL_CHLOG = 'release:changeLog'
REL_SYNCPROTO = 'release:synchProtocol'
REL_SYNCURL = 'release:synchURL'

UMD_META = 'UMDmeta:UMDmeta'
UMD_PLAT = 'UMDmeta:targetPlatform'
UMD_ARCH = 'UMDmeta:targetArch'
UMD_CAPAB = 'UMDmeta:capability'
UMD_PKGS = 'UMDmeta:packages'
UMD_PKG = 'UMDmeta:package'

REPO_REPOID = 'repofile:repoid'
REPO_ID = 'repofile:id'
REPO_NAME = 'repofile:name'
REPO_TYPE = 'repofile:type'
REPO_BASE = 'repofile:baseUrl'
REPO_ENABLED = 'repofile:enabled'
REPO_PRIO = 'repofile:priority'
REPO_GPGCHECK = 'repofile:gpgcheck'
REPO_GPGKEY = 'repofile:gpgkey'
REPO_PROTECT = 'repofile:protect'
REPO_ENTRY = 'repofile:entry'

REPO_ROOT = {
    'apt': 'repository:aptRepository',
    'yum': 'repository:yumRepository',
}


def get_repo_type(os):
    if os.find('deb') != -1:
        return 'apt'
    return 'yum'


def prettify(elem):
    """Return a pretty-printed XML string for the Element. """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="\t")


def parse_version(version):
    major, minor, rev = (0, 0, 0)
    sv = ('%s' % version).split('.', 2)
    try:
        major = sv.pop(0)
        minor = sv.pop(0)
        rev = sv.pop(0)
    except IndexError:
        pass
    return major, minor, rev


def get_rpm_attrs(url):
    attrs = {
        'pkgtype': 'metapackage',
        'url': url
    }
    filename = os.path.basename(urlparse.urlparse(url)[2])
    attrs['filename'] = filename
    dot_split = filename.split('.')
    attrs['arch'] = dot_split[-2]
    dash_split = ('.'.join(dot_split[0:-2])).split('-')
    attrs['release'] = dash_split[-1]
    attrs['version'] = dash_split[-2]
    attrs['pkgname'] = '-'.join(dash_split[0:-2])
    attrs['pkgtype'] = 'metapackage'
    return attrs


def create_umd_meta(release, pkg):
    root = ET.Element(UMD_META)
    ET.SubElement(root, UMD_PLAT).text = pkg.get('os', '')
    ET.SubElement(root, UMD_ARCH).text = pkg.get('arch', '')
    for capability in release['capabilities']:
        ET.SubElement(root, UMD_CAPAB).text = capability
    pkgs = ET.SubElement(root, UMD_PKGS)
    for url in pkg.get('rpms'):
        ET.SubElement(pkgs, UMD_PKG, get_rpm_attrs(url))
    return root


def create_repo_info(shortname, repo_type, pkg):
    if repo_type == 'yum':
        repo_file_ext = 'repo'
    else:
        repo_file_ext = 'list'
    attrs = {
        'filename': '%s.%s' % (shortname, repo_file_ext),
        'relativePath': 'repofiles'
    }
    repo_root = ET.Element('repofile:%sRepofile' % repo_type, attrs)
    repofile_root = ET.SubElement(repo_root,
                                  'repofile:%sRepository' % repo_type)
    ET.SubElement(repofile_root, REPO_REPOID).text = shortname
    if repo_type == 'yum':
        ET.SubElement(repofile_root, REPO_ID).text = shortname
        ET.SubElement(repofile_root, REPO_NAME).text = shortname
    else:
        ET.SubElement(repofile_root, REPO_TYPE).text = repo_type
    ET.SubElement(repofile_root, REPO_BASE, {'type': 'relative'}).text = '/'
    if repo_type == 'yum':
        ET.SubElement(repofile_root, REPO_ENABLED).text = '1'
        ET.SubElement(repofile_root, REPO_PRIO).text = '1'
        gpgkey = pkg.get('gpgkey')
        if gpgkey:
            ET.SubElement(repofile_root, REPO_GPGCHECK).text = '1'
            ET.SubElement(repofile_root, REPO_GPGKEY).text = gpgkey
        ET.SubElement(repofile_root, REPO_PROTECT).text = '1'
    else:
        ET.SubElement(repofile_root, REPO_ENTRY).text = './'
    return repo_root


def create_release_xml(release, pkgs):
    # Release part
    root_attr = {
        'xmlns:UMDmeta': 'http://repo.egi.eu/0.2/UMDmeta',
        'xmlns:release': 'http://repo.egi.eu/0.2/release',
        'xmlns:repofile': 'http://repo.egi.eu/0.2/repofile',
        'xmlns:repository': 'http://repo.egi.eu/0.2/repository',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsi:noNamespaceSchemaLocation': 'release.xsd',
    }
    root = ET.Element(REL_REL, root_attr)
    ET.SubElement(root, REL_PN).text = release.get('product', '')
    os = pkgs.get('os', '')
    repo_type = get_repo_type(os)
    shortname = ('%s.%s.%s.%s' % (release.get('tp_short').upper(),
                                  release.get('product').lower(),
                                  os, pkgs.get('arch', ''))).replace(' ', '_')
    ET.SubElement(root, REL_PSN).text = shortname
    ET.SubElement(root, REL_TP).text = release.get('tp_short', '')
    ET.SubElement(root, REL_TPSN).text = release.get('tp_short', '')
    ET.SubElement(root, REL_CONT).text = release.get('contact', '')
    ET.SubElement(root, REL_TECHCONT).text = release.get('contact', '')
    ET.SubElement(root, REL_DESC).text = release.get('desc', '')
    ET.SubElement(root, REL_DOCLINK).text = release.get('docs', '')
    isodate_now = datetime.datetime.now().strftime('%Y%m%d')
    ET.SubElement(root, REL_ISODATE).text = '%s' % release.get('isodate',
                                                               isodate_now)
    ET.SubElement(root, REL_INC).text = ('%s' % release.get('incremental',
                                                            False)).lower()
    ET.SubElement(root, REL_EMRGC).text = ('%s' % release.get('emergency',
                                                              False)).lower()
    major, minor, rev = parse_version(release.get('version', ''))
    ET.SubElement(root, REL_MAJOR).text = major
    ET.SubElement(root, REL_MINOR).text = minor
    ET.SubElement(root, REL_REV).text = rev
    ET.SubElement(root, REL_NOTES).text = release.get('releasenotes', '')
    ET.SubElement(root, REL_CHLOG).text = release.get('changelog', '')
    ET.SubElement(root, REL_SYNCPROTO).text = repo_type
    ET.SubElement(root, REL_SYNCURL).text = 'n/a'
    # packages
    root.append(create_umd_meta(release, pkg))
    # repository
    repo_attrs = {
        'external': 'false',
        'id': shortname,
        'path': '/',
    }
    ET.SubElement(root, REPO_ROOT.get(repo_type), repo_attrs)
    root.append(create_repo_info(shortname, repo_type, pkg))
    return root, '%s-%s.%s.%s' % (shortname, major, minor, rev)

parser = argparse.ArgumentParser(description='Produce release xml')
parser.add_argument('release', metavar='<RELEASE YAML>',
                    help='YAML file containing the release info')
args = parser.parse_args()

release = yaml.load(open(args.release))
for pkg in release.get('packages'):
    xml, ppa_name = create_release_xml(release, pkg)
    file_name = '%s.xml' % ppa_name
    with open(file_name, 'w+') as f:
        f.write(prettify(xml))
        print "Wrote %s" % file_name
