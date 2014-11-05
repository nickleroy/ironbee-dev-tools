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
import dagger.dagger

class IbServerDag( dagger.dagger ) :
    def __init__( self, name ) :
        dagger.dagger.__init__( self )
        self._name = name
        self._stale = None
    Name = property( lambda self : self._name )

    def AllStale( self, stale ) :
        self._stale = stale

    def create( self, target, phony=False, stale=None, fn=None ):
        if stale is None :
            stale = False if self._stale is None else self._stale
        return dagger.node( target, phony=phony, stale=stale, fn=fn )

if __name__ == "__main__" :
    assert 0, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
