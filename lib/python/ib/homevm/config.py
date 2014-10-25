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
from configobj import ConfigObj
from validate  import Validator, ValidateError
from ib.util.version      import *
from ib.homevm.exceptions import *

class IbHomeVmConfig( object ) :
    _spec_data = \
                 """
                 [build]
                 
                 [install]
                 [[defaults]]
                 User             = string
                 Group            = string
                 IronBeeVersion   = string
                 IronBeeGitBranch = string
                
                 """.splitlines()

    def __init__( self, path ) :
        self._path = path

    @staticmethod
    def _CheckVersion( s ) :
        if IbVersion.CheckStr( s ) :
            return s
        else :
            raise ValidateError( 'Invalid version string "'+s+'"' )

    def Read( self, lines=None ) :
        try :
            spec = dict(ConfigObj(self._spec_data)).update({ '[DefaultVersion]':self._CheckVersion })
            validator = Validator( spec )
            if lines is not None :
                assert type(lines) in (tuple,list)
                config = ConfigObj( lines, configspec=ConfigObj(self._spec_data) )
            else :
                lines = open(self._path).readlines()
                config = ConfigObj( lines, configspec=ConfigObj(self._spec_data) )
            config.validate( validator )
            return config
        except ValidateError as e:
            raise IbApplianceConfigError(e)

if __name__ == "__main__" :
    _config = \
              """
              [build]
              
              [install]
              [[defaults]]
              User             = nick
              Group            = qualys
              IronBeeVersion   = 0.11.3
              IronBeeGitBranch = 0.11.x
              """.splitlines()
    _dict = {
        'build': {},
        'install': {
            'defaults':
            {
                'User': 'nick',
                'Group': 'qualys',
                'IronBeeVersion': '0.11.3',
                'IronBeeGitBranch': '0.11.x'
            }
        }
    }

    config = IbHomeVmConfig( '/ignored.conf' )
    cfg = config.Read( _config )
    assert cfg == _dict

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
