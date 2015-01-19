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
import string
import magic

from ib.util.version import *

class IbVersionReader( object ) :
    def __init__( self ) :
        self._magic = magic.open(magic.NONE)
        self._magic.load( )

    def GetAutoVersion( self, path ) :
        ftype = self._magic.file( os.path.realpath(path) )
        self._last_path = path
        if 'ASCII' in ftype  or  'text' in ftype :
            return self.GetTextVersion( path )
        else :
            return self.GetBinVersion( path )

    _printable = frozenset(string.printable)
    def GetStrings( self, fp ) :
        found_str = ""
        while True:
            data = fp.read(1024*4)
            if not data:
                break
            for char in data:
                if char in self._printable:
                    found_str += char
                elif len(found_str) >= 4:
                    yield found_str
                    found_str = ""
                else:
                    found_str = ""

    _bin_re = re.compile( r"IronBee/([\d\.]+)" )
    def GetBinVersion( self, path ) :
        try :
            fp = open(path, "rb")
            for line in self.GetStrings( fp ) :
                m = self._bin_re.match( line )
                if m is None :
                    continue
                version = IbVersion.CreateFromStr( m.group(1) )
                if version is not None :
                    version.Path = path
                    return version
            return None
        except IOError as e :
            return None

    def GetTextVersion( self, path ) :
        regex = re.compile( 'VERSION=([\d\.]+)' )
        for line in open(path) :
            m = regex.search(line)
            if m is None :
                continue
            version = IbVersion.CreateFromStr( m.group(1) )
            if version is not None :
                version.Path = path
                return version
        return None

    @staticmethod
    def FindFile( path ) :
        if os.path.isfile( path ) :
            return path
        for name in ('libironbee.a', 'libironbee.so') :
            full = os.path.join(path, name)
            if os.path.isfile( full ) :
                return full
        return None

class IbModule_util_version_reader( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    assert False, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
