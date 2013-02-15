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
import copy

class IbDict( dict ):
    """
    Dictionary that allows for an associated getter function that's invoked
    automagically with any get.
    """
    class Value( object ) :
        def __init__( self, value, fn=None ) :
            self._value = value
            self._fn = fn

        def Get(self, data) :
            if self._fn is not None :
                self._fn(data, self._value)
            return self._value

    def Set( self, k, v, fn=None, over=True ) :
        if over == False and k in self :
            return
        dict.__setitem__(self, k, self.Value(v, fn) )

    def __setitem__(self, k, v):
        dict.__setitem__(self, k, self.Value(v) )

    def __getitem__(self, k):
        v = dict.__getitem__(self, k)
        return v.Get( self )

class IbExpander( object ) :
    def __init__( self, defs ) :
        assert isinstance(defs, dict)
        self._defs = defs

    def ExpandList( self, args ) :
        loops = 0
        if self._options.verbose >= 2 :
            print "Expanding:", args
            print "  using:", self._defs
        while True :
            initial = copy.copy(args)
            for n,arg in enumerate(args) :
                for key,value in self._defs.items() :
                    s = '${'+key+'}'
                    c = copy.copy(args)
                    if arg == s  and  type(value) == list :
                        expanded = self.Expand(value)
                        args = args[:n] + expanded + args[n+1:]
                        if self._options.verbose >= 3 :
                            print c, key+"="+str(expanded), "->", args
                        continue
                    if s in arg :
                        args[n] = arg.replace(s, str(value))
                        if self._options.verbose >= 3 :
                            print c, key+"="+str(value), "->", args
            if initial == args  or  loops > 10 :
                if self._options.verbose >= 2 :
                    print "Expanded:", args
                return args
            loops += 1

    def ExpandStr( self, s ) :
        if s is None :
            return None
        expanded = self.Expand( [s] )
        assert len(expanded) == 1
        return expanded[0]
        
    def Main( self ) :
        self.ParserSetup( )
        self.Parse( )
        self.RunATS( )

main = Main( )
main.Main( )

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
