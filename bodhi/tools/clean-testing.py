#!/usr/bin/python -tt

"""
A tool that untags testing builds that have a newer build tagged as stable.
"""

import os
import sys
import rpm
import turbomail
import turbogears

from sqlobject import SQLObjectNotFound
from turbogears.database import PackageHub

from bodhi.model import Release, PackageBuild
from bodhi.buildsys import get_session

def clean_testing_builds(untag=False):
    koji = get_session()
    for release in Release.select():
        stable_builds = koji.listTagged('%s-updates' % release.dist_tag,
                                        latest=True)
        print "Fetched %d builds tagged with %s-updates" % (
                len(stable_builds), '%s-updates' % release.dist_tag)
        testing_builds = koji.listTagged('%s-updates-testing' %
                                         release.dist_tag, latest=True)
        print "Fetched %d builds tagged with %s-updates-testing" % (
                len(testing_builds), release.dist_tag)
        for testing_build in testing_builds:
            for stable_build in stable_builds:
                if stable_build['package_name'] == testing_build['package_name']:
                    if rpm.labelCompare((str(testing_build['epoch']),
                                         testing_build['version'],
                                         testing_build['release']),
                                        (str(stable_build['epoch']),
                                         stable_build['version'],
                                         stable_build['release'])) < 0:
                        print "%s is older than %s" % (testing_build['nvr'],
                                                       stable_build['nvr'])
                        try:
                            build = PackageBuild.byNvr(testing_build['nvr'])
                            if build.update.status != 'testing':
                                print "%s not testing in bodhi!" % build.update
                                raise SQLObjectNotFound
                            else:
                                if untag:
                                    print "Obsoleting via bodhi"
                                    build.update.obsolete(newer=stable_build['nvr'])
                                else:
                                     print "Need to obsolete via bodhi"
                        except SQLObjectNotFound:
                            if untag:
                                print "Untagging via koji"
                                koji.untagBuild('%s-updates-testing' %
                                                release.dist_tag,
                                                testing_build['nvr'],
                                                force=True)
                            else:
                                print "Need to untag koji build %s" % testing_build['nvr']

        print

if __name__ == '__main__':
    load_config()
    turbomail.start_extension()
    clean_testing_builds('--untag' in sys.argv)