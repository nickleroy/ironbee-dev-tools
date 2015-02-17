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

class IbTimeUnits( object ) :
    @staticmethod
    def _GetUnit( seconds, base ) :
        if seconds < base :
            return 0, seconds
        value = int(seconds) / base
        return value, seconds - (value * base)

    def __init__( self, seconds, years=True, days=True, hours=True ) :
        self._years, seconds   = self._GetUnits( seconds, 365*24*60*60 ) if years else 0, seconds
        self._days, seconds    = self._GetUnits( seconds, 24*60*60 ) if days else 0, seconds
        self._hours, seconds   = self._GetUnits( seconds, 60*60 ) if hours else 0, hours
        self._minutes, seconds = self._GetUnits( seconds, 60 )
        self._seconds = seconds

    def Format( self, fmt='%y:%d:%h:%m:%s' ) :
        if self._years :
            return fmt.format( self.Years, self.Days, self.Hours, self.Minutes, self.Seconds )
        elif self._days :
            fmt

    Years   = property( lambda self : self._years )
    Days    = property( lambda self : self._days )
    Hours   = property( lambda self : self._hours )
    Minutes = property( lambda self : self._minutes )
    Seconds = property( lambda self : self._seconds )


class IbTimeFormatter( object ) :
    def __init__( self ) :
        pass

    def ElapsedTime( seconds ) :
        return TimeUnits( seconds, minutes, hours, days, years )

    def FormatElapsedTime( self, seconds ) :
        units = self.ElapsedTime( seconds )


class IbModule_util_timeformat( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    assert False, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
