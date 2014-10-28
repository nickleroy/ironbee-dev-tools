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
# Nick's confgen RC file for IronBee, etc.

from confgen.rc.build import *
from confgen.rc.gcc import *
from confgen.rc.clang import *
from confgen.rc.doxygen import *
from confgen.rc.path import *

class IbBuildInfo( object ) :
    __valid_builds = {
        "IronBee" : ("devel", "generic", "doxygen"),
        "LibHTP" : ("generic"),
        "other" : ("generic"),
    }
    def __init__( self, _class, _type ) :
        """
        Valid classes: "IronBee", "generic", "doxygen"
        Valid types: "devel" (IronBee only), "generic", "doxygen"(IronBee only)
        """
        assert _class in self.__valid_builds, _class
        assert _type in self.__valid_builds[_class], _type
        self._class = _class
        self._type = _type

    def GetClass( self ) :
        return self._class
    def GetType( self ) :
        return self._type
    def GetIsIronBee( self ) :
        return self._class == "IronBee"
    def __str__( self ) :
        return 'IbBuildTarget( class='+self._class+' , type='+self._type+' )'

class IbConfGenGcc( ConfGenGcc ) :
    def __init__( self ) :
        ConfGenGcc.__init__( self, "IronBee/GCC" )
    def Setup( self ) :
        cxx  = self.GetVar('cxx')
        size = self.GetVar('size')
        ConfGenGcc.Setup( self, cxx=cxx, size=size )

class IbConfGenClang( ConfGenClang ) :
    def __init__( self ) :
        ConfGenClang.__init__( self, "IronBee/Clang" )
    def Setup( self ) :
        cxx      = self.GetVar('cxx')
        analyzer = self.GetVar('analyzer')
        ConfGenClang.Setup( self, cxx=cxx, analyzer=analyzer )

class IbConfGenDoxygen( ConfGenDoxygen ) :
    def __init__( self ) :
        ConfGenDoxygen.__init__( self, "IronBee/Doxygen" )
    def Setup( self ) :
        ConfGenDoxygen.Setup( self )

class IbBuild( object ) :
    def __init__( self, config, build ) :
        assert isinstance(config, ConfGenBaseRc)
        assert isinstance(build, IbBuildInfo)
        self._config = config
        self._build = build
    Build       = property( lambda self : self._build )
    BuildClass  = property( lambda self : self._build.GetClass() )
    BuildType   = property( lambda self : self._build.GetType() )
    Platform    = property( lambda self : self._config.Platform )

    def Setup( self ) :
        self._SetupDirs()
        self._SetupExternals()
        self._config.Setup( )
        self._config.AddQuery( 'isIronBee', self._build.GetIsIronBee )
        self._config.AddQuery( 'Target',    self._build.GetClass )
        self._config.AddQuery( 'BuildType', self._build.GetType )

    def Finish( self ) :
        self._config.FinishConfig( )

    def _SetupDirs( self ) :
        parent = os.path.realpath( '..' )
        home  = os.environ['HOME']
        devel = os.environ.get( 'QLYS_DEVEL', os.path.join(home, 'devel') )
        self._dirs = { }
        self._dirs['devel']   = devel
        self._dirs['build']   = os.environ.get( 'QLYS_BUILD', os.path.join(devel, 'build') )
        self._dirs['ibsrc']   = os.environ.get( 'IB_ROOT',  os.path.join(devel, 'ib') )
        self._dirs['install'] = os.path.join(parent, 'install')
        self._dirs['ext']     = os.environ.get('EXT_INSTALL', os.path.join(devel, 'install'))

    def _SetupExternals( self ) :
        ext = self._dirs['ext']
        if self.Platform.isOpenSUSE  and  self.Platform.DistroFloat >= 12.3 :
            externals = {
                'ats'      : None,
                'httpd'    : None,
                'tengine'  : None,
            }
        else :
            externals = {
                'ats'      : CheckPath.CheckEnvPath( 'ATS_ROOT' ),
                'httpd'    : CheckPath.CheckEnvPath( 'HTTPD_ROOT' ),
                'tengine'  : CheckPath.CheckEnvPath( 'TENGINE_ROOT' ),
            }
        externals['modp'] = CheckPath.CheckDirPath( 'stringencoders-v3.10.3', self._dirs['ext'] )

        self._externals = { }
        for k,v in externals.items() :
            if v is not None :
                self._externals[k] = v
        print self._externals

    def _SetupQlysBuild( self, suffix ) :
        if suffix is not None :
            prefix = self._dirs['install']+suffix
            self._config.SetNameValueOption( "prefix", prefix )
            self._config.SetNameValueOption( "libexecdir", os.path.join(prefix, "libexec") )
        else :
            prefix = self._dirs['install']
            self._config.SetNameValueOption( "prefix", prefix)
            self._config.SetNameValueOption( "libexecdir", os.path.join(prefix, "libexec") )

    def SetupIronBee( self, ib_version=None ) :
        print "Setting up IronBee", "CXX:", self._config.IsCxx()
        assert self.BuildClass == "IronBee"
        prefix = self._dirs['install']
        self._config.SourceDir = self._dirs['ibsrc']

        self._SetupQlysBuild( ib_version )
        self._SetupQlysBuild( ib_version )
        self._SetupExternals( )

        self._config.SetEnableOption( 'cpp', self._config.IsCxx() )
        if self.BuildType == "devel" :
            self._config.SetEnableOption( "experimental", True )
            self._config.SetEnableOption( "mpool-valgrind", True )
            self._config.SetWithOption( "valgrind", True )
        else :
            self._config.SetEnableOption( "mpool-valgrind", False )
            self._config.SetWithOption( "valgrind", False )
            protobuf = self._externals.get('protobuf')
            if protobuf is not None :
                self._config.SetWithOption( "protobuf", True, protobuf );

        # C / CXX flags
        self._config.SetOptimize(self._config.Arg('optimization'))

        if self.BuildType == 'devel' :
            ext = self._externals
            self._config.AddCcFlag('-DATS_DEBUG_ENGINE_MANAGER=1', True)
            if 'httpd' in ext :
                httpd = ext['httpd']
                self._config.SetWithOption( "httpd", True, httpd )
                self._config.SetWithOption( "apxs", True, os.path.join(httpd, "bin", "apxs") )
            self._config.SetWithOption( "trafficserver", True, ext.get('ats') )
            if 'modp' in ext :
                self._config.SetWithOption( "modp", True, ext['modp'] )
            if 'tengine' in ext :
                self._config.SetWithOption( "ngx_dso_tool", True,
                                    os.path.join(ext['tengine'], 'sbin', 'dso_tool') )
            if 'pcre' in ext :
                self._config.SetWithOption( "pcre", True, ext['pcre'] )
            if 'yajl' in ext :
                self._config.SetWithOption( "yajl", True, ext['yajl'] )

        if not self._config.Quiet :
            print "SELF._BUILD:", self._build

    def SetupLibHTP( self ) :
        self._SetupQlysBuild( )
        self.config.SourceDir = os.path.join(self._dirs['devel'], 'libhtp')

    def SetupOther( self ) :
        self.config.SourceDir = self.BuildDir
        self._config.SetNameValueOption( "prefix", os.path.join(self._dirs['ext'], self._build['name']) )
        if self._build_name.startswith('trafficserver-') :
            self._config.SetWithOption('user', True, os.environ['USER'])
            self._config.SetWithOption('group', True, 'users')
            self._config.SetEnableOption( "diags", True )
            self._config.SetEnableOption( "tests", True )


### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
