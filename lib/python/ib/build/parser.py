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
import argparse

from ib.util.parser   import *
from ib.build.archive import *

class IbBuildParser( IbBaseParser ) :
    def __init__( self, description ) :
        IbBaseParser.__init__( self, description )

        class TimeAction( argparse.Action ) :
            def __call__( self, parser, namespace, values, option_string=None ) :
                namespace.timestamp = IbBuildArchive.FormatTime( values )
        self.Parser.set_defaults( timestamp=None )
        self.Parser.add_argument( "--timestamp",
                                  action=TimeAction,
                                  help="Specify timestamp <yymmdd-hhmmss>" )

        self.Parser.add_argument( "--arch",
                                  action="store", dest="arch", default=os.environ['SYS_ARCH'],
                                  help="Specify architector to use <"+os.environ['SYS_ARCH']+">" )

        self.Parser.add_argument( "--bits",
                                  action="store", dest="bits", type=int,
                                  default=int(os.environ['SYS_BITS']),
                                  help="Specify architector to use <"+os.environ['SYS_BITS']+">" )

        build_root = os.environ['QLYS_BUILD']
        self.Parser.add_argument( "--build-root",
                                          action="store", dest="build_root", default=build_root,
                                          help="Specify alternate directory <"+build_root+">" )

        archives = os.environ['IB_BLD_ARCHIVES']
        self.Parser.add_argument( "--archives",
                                  action="store", dest="archives", default=archives,
                                  help="Specify archives directory <"+archives+">" )

        config = os.path.join(os.environ['QLYS_DEV_ETC'], 'ib-build.conf')
        self.Parser.add_argument( "--config",
                                  action="store", dest="config", default=config,
                                  help="Specify configuration file to use <"+config+">" )

        self.Parser.add_argument( "--list",
                                  action="store_true", dest="list", default=False,
                                  help="List archives <default=no>" )

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
