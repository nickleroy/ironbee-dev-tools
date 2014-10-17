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
from configobj import ConfigObj
from validate  import Validator, ValidateError

class IbApplianceException( BaseException ) : pass
class IbApplianceConfigError( IbApplianceException )

class IbAppliance( object ) :
    _spec_data = \
"""
[build]

[install]
  DefaultVersion = string
  DefaultBranch = string(default=master)

""".splitlines()

    def __init__( self ) :
        pass

    @staticmethod
    def _CheckVersion( s ) :
        print "Checking version", s
        if IbVersion.CheckStr( s ) :
            return s
        else :
            raise ValidateError( 'Invalid version string "'+s+'"' )

    def ReadConfig( self, path ) :
        try :
            spec = dict(ConfigObj(self._spec_data)).update({ '[DefaultVersion]':self._CheckVersion })
            validator = Validator( spec )
            config = ConfigObj( path, configspec=ConfigObj(self._spec_data) )
            config.validate( validator )
            return config
        except ValidateError as e:
            raise IbApplianceConfigError(e)

if __name__ == "__main__" :
    _config = \
"""
[build]

[install]
  DefaultVersion =
  DefaultBranch  =
""".splitlines()
    appliance = IbAppliance( )
    appliance.ReadConfig( _config )

