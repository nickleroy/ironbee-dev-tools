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
import os
import sys
import subprocess
import argparse

class Main( object ) :
    def __init__( self ) :
        self._parser = argparse.ArgumentParser(
            description="Program to do some shit",
            prog="template" )

    def _ParserSetup( self ) :

        self._parser.add_argument( "--nginx-dir", "-d",
                                   dest="nginx_dir", default='.', action="store",
                                   help='Specify Nginx source directory')
        self._parser.add_argument( "--nginx-build",
                                   dest="nginx_build", default=None, action="store",
                                   help='Specify Nginx build directory')
        self._parser.add_argument( "--build-root",
                                   dest="build_root", action="store",
                                   default=os.environ.get('QLYS_BUILD'),
                                   help='Specify build root')

        self._parser.add_argument( "--ib-src",
                                   dest="ib_root", action="store",
                                   default=os.environ.get('IB_ROOT'),
                                   help='Specify IronBee source directory')
        self._parser.add_argument( "--ib-install",
                                   dest="ib_install", action="store",
                                   default=os.environ.get('IB_INSTALL'),
                                   help='Specify IronBee installation directory')

        self._parser.add_argument( "--execute",
                                   action="store_true", dest="execute", default=True,
                                   help="Enable execution <default>" )
        self._parser.add_argument( "-n", "--no-execute",
                                   action="store_false", dest="execute",
                                   help="Disable execution (for test/debug)" )
        self._parser.add_argument( "-v", "--verbose",
                                   action="count", dest="verbose", default=0,
                                   help="Increment verbosity level" )
        self._parser.add_argument( "-q", "--quiet",
                                   action="store_true", dest="quiet", default=False,
                                   help="be vewwy quiet (I'm hunting wabbits)" )


    def _ParseCmdline( self ) :
        self._args = self._parser.parse_args()

    Execute = property( lambda self : self._args.execute )
    Verbose = property( lambda self : self._args.verbose )
    Quiet   = property( lambda self : self._args.quiet )

    def _Run( self ) :
        nginx_dir = self._args.nginx_dir
        while nginx_dir.endswith('/') :
            nginx_dir = nginx_dir[:-1]
        if not os.path.isdir(nginx_dir) :
            self._parser.error("Nginx directory '%s' invalid" % (nginx_dir))
        pkgname = os.path.basename(nginx_dir)
        src_dir = os.path.join(self._args.ib_root, 'servers/nginx')

        if self._args.nginx_build is None :
            build_dir = os.path.join(self._args.build_root, pkgname)
        else :
            build_dir = self._args.nginx_build
        print nginx_dir, pkgname, build_dir
        if not os.path.isdir(build_dir) :
            os.makedirs(build_dir)
        if not self.Quiet :
            print "Building from", nginx_dir, "in", build_dir

        install = self._args.ib_install
        os.environ['NGINXIB_CONFIG_FILE'] = os.path.join(src_dir, 'config.nginx')
        lib_dir = os.path.join(install, 'lib64')

        ldpath = os.environ.get('LD_LIBRARY_PATH')
        if ldpath is None  or  ldpath == '' :
            ldpath = lib_dir
        else :
            ldpath = ldpath+':'+lib_dir
        os.environ['LD_LIBRARY_PATH'] = ldpath

        # Do we need to patch?
        os.chdir(nginx_dir)
        cmd = ('grep', '-q', 'ngx_regex_malloc_init',
               os.path.join(nginx_dir, 'src/core/ngx_regex.h'))
        status = subprocess.call( cmd )
        if status == 1 :
            cmd = ('patch', '-p', '0', '-i', os.path.join(src_dir,'nginx.patch') )
            print "Patching source... via", cmd
            if self.Execute :
                subprocess.call( cmd )

        os.chdir(build_dir)
        cmd = ( 'lndir', '-u', '-U', nginx_dir, '.' )
        if self.Execute :
            status = subprocess.call( cmd )
            if status :
                sys.exit( status )

        cmd = ( './configure' ,
                '--add-module='+src_dir,
                '--with-cc-opt=-I'+os.path.join(install,'include'),
                '--with-ld-opt=-L'+lib_dir+' -lhtp -libutil -lironbee',
                '--prefix='+os.path.join(os.environ['EXT_INSTALL'], pkgname) )
        print "Configuring via", cmd
        if self.Execute :
            status = subprocess.call( cmd )
            if status :
                sys.exit( status )

        cmd = ( 'make', '-j', '4' )
        print "Building via", cmd
        if self.Execute :
            status = subprocess.call( cmd )
            if status :
                sys.exit( status )


    def Main( self ) :
        self._ParserSetup( )
        self._ParseCmdline( )
        self._Run( )

main = Main( )
main.Main( )


### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***

