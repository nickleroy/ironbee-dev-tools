#! /usr/bin/env python
"""
 * Licensed to Qualys, Inc. (QUALYS) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * QUALYS licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
"""

"""
This is a Python program to wrap the IronBee Python CLI for use in demos.
"""

import sys
import os
import re
import copy
import subprocess

sys.path.append( os.getcwd() )
from demo_defs import DemoDefs

class Var( object ) :
    def __init__( self, name, value ) :
        self._name  = name
        self._value = value
        self._lookup = '$('+name+')'
        assert self._lookup != self._value

    def Expand( self, s ) :
        if self._lookup in s :
            return s.replace( self._lookup, self._value ), True
        else :
            return s, False

    def Get( self ) :
        return self._value


class Vars( object ) :
    def __init__( self ) :
        self._vars = { }

    def Set( self, name, value ) :
        self._vars[name] = Var( name, value )
        return value

    def ExpandStr( self, s ) :
        while True :
            modified = False
            for var in self._vars.values() :
                s,mod = var.Expand( s )
                if mod : modified = True
            if modified == False :
                return s

    def ExpandList( self, _list ) :
        while True :
            modified = False
            for n,s in enumerate(_list) :
                for var in self._vars.values() :
                    s,mod = var.Expand( s )
                    if mod :
                        modified = True
                        _list = list(_list[:n]) + [s] + list(_list[n+1:])
            if modified == False :
                return _list

    def Get( self, name, expand=True ) :
        value = self._vars[name].Get( )
        if expand :
            if type(value) in ( list, tuple ) :
                return self.ExpandList( value )
            else :
                return self.ExpandStr( value )
        else :
            return value


class Main( object ) :
    """ Main class, does all of the real work """

    def __init__( self ) :
        """ Class initializer """
        if len(sys.argv) < 3 :
            print >>sys.stderr, "usage: demo <path-to-cli> number"
            sys.exit(1)
        v = Vars( )
        v.Set( "CliPath",  sys.argv[1] )
        v.Set( "DemoDir",  os.getcwd() )
        num  = v.Set( "DemoNum", sys.argv[2] )
        name = 'demo'+'-'+num
        v.Set( "DemoName", name )
        v.Set( "DemoBase", '$(DemoDir)/$(DemoName)' )
        v.Set( "DemoConf", '$(DemoBase).conf' )

        v.Set( "ReqFiles", '$(DemoBase)-request.htp' )
        v.Set( "RspFiles", '$(DemoBase)-response.htp' )

        for var,value in DemoDefs(num) :
            v.Set( var, value )
        self._vars = v
    

    def Run( self ) :
        cmd = self._vars.Get( 'Cli' )
        print cmd
        subprocess.call( cmd )


main = Main( )
main.Run( )


### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
