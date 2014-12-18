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
import re
import os
import sys
import subprocess
import argparse

class Main( object ) :
    def __init__( self ) :
        self._parser = argparse.ArgumentParser( description="Template",
                                                prog="Template" )

    def Setup( self ) :
        self._parser.set_defaults( mode_xyzzy = True )
        self._parser.set_defaults( mode_string = "xyzzy" )
        class ModeAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                print '%r %r %r' % (namespace, values, option_string)
                if   values[0] in ( [ "x", "xyzzy" ] ) :
                    namespace.mode_xyzzy = True
                    namespace.mode_string = "xyzzy"
                elif values[0] in ( [ "l", "lwpi" ] ) :
                    namespace.mode_xyzzy = False
                    namespace.mode_string = "lwpi"
                else :
                    namespace.error( "Invalid mode '"+values[0]+"'" )
        self._parser.add_argument( "-m", "--mode",
                           action=ModeAction, nargs=1,
                           help="Specify mode of x)yzzy or l)wpi"+\
                           " <default=xyzzy>" )

        self._parser.set_defaults( files = [] )
        class FilesAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                print '%r %r %r' % (namespace, values, option_string)
                namespace.files += values
        self._parser.add_argument( "-f", "--files",
                                   action=FilesAction, nargs='+',
                                   help="Specify list of files" )

        self._parser.add_argument( "--execute",
                                   action="store_true", dest="execute", default=True,
                                   help="Enable execution <default>" )
        self._parser.add_argument( "-n", "--no-execute",
                                   action="store_false", dest="execute",
                                   help="Disable execution (for test/debug)" )
        self._parser.add_argument( "-V", "--verbose",
                                   action="count", dest="verbose", default=0,
                                   help="Increment verbosity level" )
        self._parser.add_argument( "-q", "--quiet",
                                   action="store_true", dest="quiet", default=False,
                                   help="be vewwy quiet (I'm hunting wabbits)" )

        self._parser.add_argument('strings', metavar='S', type=str, nargs='*',
                                  help='an string argument')

    def Parse( self ) :
        self._args = self._parser.parse_args()
        
    def Main( self ) :
        self.Setup( )
        self.Parse( )
        print "Execute:"+str(self._args.execute), \
            "Verbose:"+str(self._args.verbose), \
            "Quiet:"+str(self._args.quiet), \
            "xyzzy:"+str(self._args.mode_xyzzy), \
            "Mode:"+str(self._args.mode_string), \
            "Files:"+str(self._args.files)
        if len(self._args.strings) :
            print "Files (%d): %s\n" % ( len(self._args.strings), self._args.strings )

main = Main( )
main.Main( )

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
