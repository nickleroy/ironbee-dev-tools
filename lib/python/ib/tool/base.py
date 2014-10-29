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
import math
import copy
import glob
import subprocess
import argparse

class IbToolException(BaseException) : pass

class IbToolBase( object ) :
    def __init__( self, name, prefix=None, tool_args=None, prog_args=None, defs=None ) :
        self._name = name
        self._prefix = self._List( prefix )
        self._tool_args = self._List( tool_args )
        self._prog_args = self._List( prog_args )
        self._defs = defs if defs is not None else { }
        self._verbose = 0
        if "ToolName" not in self._defs :
            self._defs["ToolName"] = name
        for p in self._prefix :
            if "${ToolOut}" in p :
                self._defs["ToolOut"] = "${NameLower}." + name + ".${Run}"
                break
        self._defs["DefaultOut"] = "${NameLower}." + name + ".out.${Run}"
    def SetVerbose( self, v ) :
        self._verbose = v

    @staticmethod
    def _List( o ) :
        if o is None :
            return ( )
        elif type(o) in (list, tuple) :
            return o
        else :
            return (o,)

    Defs     = property( lambda self : self._defs )
    ToolName = property( lambda self : self._defs["ToolName"] )
    ToolOut  = property( lambda self : self._defs.get("ToolOut", None) )
    Verbose  = property( lambda self : self._verbose )

    def Prefix( self ) :
        return self._prefix
    def ToolArgs( self, args ) :
        assert type(args) in (list,tuple)
        return list(args) + list(self._tool_args)
    def AppendToolArgs( self, args ) :
        assert type(args) in (list,tuple)
        self._tool_args += list(args)
    def ProgArgs( self, args ) :
        assert type(args) in (list,tuple)
        return list(args) + list(self._prog_args)
    def AppendProgArgs( self, args ) :
        assert type(args) in (list,tuple)
        self._prog_args += args

Tools = \
{
    "none" : IbToolBase( "none" ),
}


if __name__ == "__main__" :
    assert 0, "not stand-alone"
