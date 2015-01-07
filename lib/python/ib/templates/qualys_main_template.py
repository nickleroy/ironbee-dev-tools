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
from ib.util.parser import *


class Parser( IbBaseParser ) :
    def __init__( self, main ) :
        IbBaseParser.__init__( self, "Perform {}".format(main.Description) )

        group = self.Parser.add_argument_group( )
        group.add_argument( "sites", type=str, nargs='+', default=[],
                            help="Specify site(s) to enable" )
        group.add_argument( '--ib-options', '--ib',
                            dest="ib_options", type=str, nargs='+', default=[],
                            help="Specify IronBee option(s)" )
        group.add_argument( '--srv-options',
                            dest="srv_options", type=str, nargs='+', default=[],
                            help="Specify server-specific option(s)" )

        self.Parser.set_defaults( files = [] )
        class FilesAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                print '%r %r %r' % (namespace, values, option_string)
                namespace.files += values
        self.Parser.add_argument( "-f", "--files",
                                  action=FilesAction, nargs='+',
                                  help="Specify list of files" )

class Main( object ) :
    def __init__( self ) :
        self._parser = Parser( self )

    def _Setup( self ) :
        pass

    def _Parse( self ) :
        self._args = self.Parser.Parse()
        
    def Main( self ) :
        self._Setup( )
        self._Parse( )

    Description = property( lambda self : 'Template' )


main = Main( )
main.Main( )

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
