#! /usr/bin/env python
# ****************************************************************************
# Licensed to Qualys, Inc. (QUALYS) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# QUALYS licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ****************************************************************************

from ib.build.archive import *
from ib.build.parser  import *

class IbBuildSpecParser( IbBuildParser ) :
    def __init__( self, description ) :
        IbBuildParser.__init__( self, description )

        group = self.Parser.add_argument_group( )
        group.add_argument( dest="labels", default=[], nargs='+',
                            help="Specify labels" )

        group.add_argument( '--ib-branch', dest="ib_branch", default=None,
                            help="Specify IronBee branch to use <None>" )
        group.add_argument( '--ib-version', dest="ib_version", default=None,
                            help="Specify IronBee version to use <None>" )
        group.add_argument( '--etc-branch', '--etc', '-b',
                            dest="etc_branch", default=None,
                            help="Specify alternate etc.in git branch name <None>" )

        group = self.Parser.add_argument_group( )
        group.add_argument( "--user",
                            action="store", dest="user", default=None,
                            help='Specify user to setup <default=from config>' )
        group.add_argument( "--group",
                            action="store", dest="group", default=None,
                            help='Specify group to setup <default=from config>' )

        group = self.Parser.add_argument_group( )
        group.add_argument( "--gcc-version",
                            action="store", dest="gcc_version", default=None,
                            help="Specify GCC version to use <Auto>" )
        group.add_argument( "--clang-version",
                            action="store", dest="clang_version", default=None,
                            help="Specify clang version to use <Auto>" )
        group.add_argument( "--clang-tsan",
                            action="store_true", dest="clang_tsan", default=False,
                            help="Require clang thread santized version to use <Auto>" )
        group.add_argument( "--compiler",
                            action="store", dest="compiler", default=None,
                            choices=('clang','gcc'),
                            help="Specify compiler to use <Auto>" )

        group = self.Parser.add_argument_group( )
        group.add_argument( "--ats-version",
                            action="store", dest="ats_version", default=None,
                            help="Specify ATS version to use <Auto>" )


class IbBuildSpecs( IbBuildArchive ) :
    def __init__( self, verbose ) :
        IbBuildArchive.__init__( self )
        self._verbose = verbose

    def MergeArgs( self, defaults, args ) :
        self.Labels = args.labels

        if args.ib_version is not None :
            self.IronBeeVersion = IbVersion(args.ib_version)
        elif defaults.get('IronBeeVersion', None) :
            self.IronBeeVersion = IbVersion(defaults.get('IronBeeVersion'))

        if args.ib_branch is not None :
            self.IronBeeGitBranch = args.ib_branch
        else :
            self.IronBeeGitBranch = defaults.get('IronBeeGitBranch', None)

        self.Architecture = args.arch
        self.Bits = args.bits

        if args.compiler is not None :
            self.Compiler = args.compiler
        elif 'COMPILER' in os.environ :
            self.Compiler = os.environ['COMPILER']

        if self.Compiler == 'gcc'  and  args.gcc_version is not None :
            self.GccVersion = args.gcc_version
        elif 'GCC_VERSION' in os.environ :
            self.GccVersion = os.environ['GCC_VERSION']

        if self.Compiler == 'clang'  and  args.clang_version is not None :
            self.ClangVersion = args.clang_version
        elif 'CLANG_VERSION' in os.environ :
            self.ClangVersion = os.environ['CLANG_VERSION']

        if self.Compiler == 'clang'  and  args.clang_tsan :
            self.ClangThreadSantizer = True

        if args.ats_version is not None :
            self.AtsVersion = args.ats_version
        elif 'ATS_VERSION' in os.environ :
            self.AtsVersion = os.environ['ATS_VERSION']


    def ArchiveFilter( self, archive ) :
        for label in self.Labels :
            if label not in archive.Labels :
                if self._verbose >= 2 :
                    print 'Skipping archive {}: Label "{}" not in target "{}"' .format(
                        archive.Name, label, archive.Labels )
                return False

        if self.IronBeeVersion is not None and \
           self.IronBeeVersion != archive.IronBeeVersion :
            if self._verbose >= 2 :
                print 'Skipping archive {}: IronBee versions do not match: "{}" != "{}"'.format(
                    archive.Name, self.IronBeeVersion, archive.IronBeeVersion )
            return False

        if self.IronBeeGitBranch is not None and \
           archive.IronBeeGitBranch != self.IronBeeGitBranch :
            if self._verbose >= 2 :
                print 'Skipping archive {}: IronBee branches do not match: "{}" != "{}"'.format(
                    archive.Name, archive.IronBeeGitBranch, self.IronBeeGitBranch )
            return False

        if self.Compiler != archive.Compiler :
            if self._verbose >= 2 :
                print 'Skipping archive {}: Compilers do not match: "{}" != "{}"'.format(
                    archive.Name, archive.Compiler, self.Compiler )
            return False

        if self.Compiler == 'gcc' and self.GccVersion != archive.GccVersion :
            if self._verbose >= 2 :
                print 'Skipping archive {}: GCC versions do not match: "{}" != "{}"'.format(
                    archive.Name, archive.GccVersion, self.GccVersion )
            return False

        if self.Compiler == 'clang' :
            if self.ClangVersion != archive.ClangVersion :
                if self._verbose >= 2 :
                    print 'Skipping archive {}: clang versions do not match: "{}" != "{}"'.format(
                        archive.Name, archive.ClangVersion, self.ClangVersion )
                return False
            if self.ClangThreadSanitizer != archive.ClangThreadSanitizer :
                if self._verbose >= 2 :
                    print 'Skipping archive {}: TSAN mis-match: "{}" != "{}"'.format(
                        archive.Name, archive.ClangVersion, self.ClangVersion )
                return False

        if self.Architecture != archive.Architecture :
            if self._verbose >= 2 :
                print 'Skipping archive {}:  Architectures do not match: "{}" != "{}"'.format(
                    archive.Name, archive.Architecture, self.Architecture )
            return False

        if self.Bits != archive.Bits :
            if self._verbose >= 2 :
                print 'Skipping archive {}:  Bits do not match: "{}" != "{}"'.format(
                    archive.Name, archive.Bits, self.Bits )
            return False
        return True



### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
