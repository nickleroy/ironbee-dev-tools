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
import argparse

class IbBaseParser( object ) :
    class SizeAction(argparse.Action):
        __mults = { 'k':1024, 'K':1000,
                    'm':1024*1024, 'M':1000*1000,
                    'g':1024*1024*1024, 'G':1000*1000*1000, }
        __keys = tuple(__mults.keys())

        def SetSize( self, parser, namespace, option_string, value ) :
            assert False
        def __call__(self, parser, namespace, param, option_string=None):
            strval = param
            mult = 1
            if strval.endswith( self.__keys ) :
                mult = self.__mults[strval[-1]]
                strval = strval[:-1]
            try :
                value = int(strval) * mult
                self.SetSize( parser, namespace, option_string, value )
            except ValueError :
                parser.error( "Invalid value '"+strval+"'" )

    """
    Set up a basic parser for IronBee Python scripts.
    """
    def __init__( self, description ) :
        parser = argparse.ArgumentParser(
            description=description,
            prog=os.path.basename(sys.argv[0]) )
        self._parser = parser
        
        group = self.Parser.add_argument_group( )
        parser.add_argument( "--execute",
                             action="store_true", dest="execute", default=True,
                             help="Enable execution <default=yes>" )
        parser.add_argument( "-n", "--no-execute",
                             action="store_false", dest="execute",
                             help="Disable execution (for test/debug)" )
        parser.add_argument( "-v", "--verbose",
                             action="count", dest="verbose", default=0,
                             help="Increment verbosity level" )
        parser.add_argument( "-q", "--quiet",
                             action="store_true", dest="quiet", default=False,
                             help="be vewwy quiet (I'm hunting wabbits)" )
        self._parsers = [ parser ]

    def Parse( self ) :
        self._args = self._parser.parse_args()
        if not self._args.execute  and  self._args.verbose == 0  and  not self._args.quiet :
            self._verbose = 1
        return self._args

    Parser  = property( lambda self : self._parser )

if __name__ == "__main__" :
    parser = IbBaseParser("Test")
    args = parser.Parse( )
    print vars(args)

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***