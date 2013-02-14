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
import glob
import subprocess
import argparse

class Tool( object ) :
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
                self._defs["ToolOut"] = "httpd." + name + ".${Run}"
                break
        self._defs["DefaultOut"] = "httpd." + name + ".out.${Run}"
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
        return list(args) + list(self._tool_args)
    def ProgArgs( self, args ) :
        return list(args) + list(self._prog_args)


class ToolGdb( Tool ) :
    _gdb_prefix = ("${ToolName}",)
    def __init__( self, name ) :
        Tool.__init__( self, name, prefix=self._gdb_prefix, tool_args="--args", prog_args="-X" )

class ToolStrace( Tool ) :
    _strace_prefix = ("${ToolName}",
                      "-o", "${ToolOut}")
    def __init__( self, name ) :
        Tool.__init__( self, name, prefix=self._strace_prefix )

class ToolValgrind( Tool ) :
    _valgrind_prefix = ( "${ToolName}",
                         "--tool=${SubTool}",
                         "--log-file=${ToolOut}",
                         "--leak-check=full" )
    def __init__( self, name, defs ) :
        Tool.__init__( self, name, prefix=self._valgrind_prefix, defs=defs )
    def Prefix( self ) :
        prefix = list(self._prefix) + [ "-v" for i in range(self._verbose) ]
        return prefix

class ToolMain( object ) :
    _CmdPrefixes = {
        "none"     : Tool( "none" ),
        "gdb"      : ToolGdb( "gdb" ),
        "strace"   : ToolStrace( "strace" ),
        "valgrind" : ToolValgrind("valgrind", defs={"SubTool":"memcheck"}),
        "helgrind" : ToolValgrind("helgrind", defs={"SubTool":"helgrind"}),
        }

    self._defs = {
        "PID"           : os.getpid(),
        "Run"           : "${PID}",
        "Devel"         : os.environ["QYLS_DEVEL"],
        "Var"           : os.environ.get("QYLS_VAR", "${Devel}/var"),
        "Log"           : "${Var}/log",
        "Etc"           : os.environ.get("QYLS_ETC", "${Devel}/etc"),
        "EtcIn"         : os.environ.get("QYLS_ETC_IN", "${Devel}/etc.in"),
        "MakeArgs"      : [ ],
        "Cmd"           : [ "${Prog}", "${Args}" ],
        "IbEtc"         : "${EtcIn}/ironbee",
        }

    def __init__( self, name, defs ) :
        self._name = name
        for k,v in defs.items() :
            self._defs[k] = v

    def ParserSetup( self ) :
        self._parser = argparse.ArgumentParser( description="Run " + self._name " with IronBee",
                                                prog=os.path.basename(sys.argv[0]) )
        self._parser.add_argument( "--default",
                                   action="store_const", dest="tool", default="none",
                                   const="None",
                                   help="Run %s natively" % (self._name) )
        self._parser.add_argument( "--gdb",
                                   action="store_const", dest="tool", const="gdb",
                                   help="Run %s under gdb" % (self._name) )
        self._parser.add_argument( "--strace",
                                   action="store_const", dest="tool",
                                   const="strace",
                                   help="Run %s under strace" % (self._name) )
        self._parser.add_argument( "--valgrind",
                                   action="store_const", dest="tool",
                                   const="valgrind",
                                   help="Run %s under valgrind (memcheck)" % (self._name) )
        self._parser.add_argument( "--helgrind",
                                   action="store_const", dest="tool",
                                   const="helgrind",
                                   help="Run %s under helgrind" % (self._name) )

        self._parser.add_argument( "--force-make", "-f",
                                   action="store_true", dest="force_make", default=False,
                                   help="Force execution of make in etc directories")

        self._parser.add_argument( "--out", "-o",
                                   dest="output", type=argparse.FileType('w'), default=None,
                                   help='Specify output file')
        self._parser.add_argument( "--default-out", "--do",
                                   action="store_const", dest="output",
                                   const="${DefaultOut}",
                                   help="Use default stdout file" )

        self._parser.add_argument( "--clean", "-c",
                                   action="store_true", dest="clean", default=False,
                                   help="Clean log files before starting %s" % (self._name) )

        self._parser.set_defaults( defs = [] )
        class StrAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                for s in values :
                    try :
                        name, value = s.split( '=', 1 )
                        namespace.defs.append( (name.strip(), value) )
                    except ValueError :
                        parser.error( "Invalid definition '"+s+"'" )
        self._parser.add_argument( "strings", metavar='n=v', type=str,
                                   action=StrAction, nargs='*',
                                   help="Specify name=value definitions" )

        self._parser.add_argument( "--print-defs", "-p",
                                   action="store_const", const="print",
                                   dest="print_mode", default=None,
                                   help="Print definition table and exit." )
        self._parser.add_argument( "--print-expanded", "-pe",
                                   action="store_const", dest="print_mode", const="expand",
                                   help="Print expanded definition table and exit." )

        self._parser.add_argument( "--execute",
                                   action="store_true", dest="execute", default=True,
                                   help="Enable execution <default>" )
        self._parser.add_argument( "-n", "--no-execute",
                                   action="store_false", dest="execute",
                                   help="Disable execution (for test/debug)" )
        self._parser.add_argument( "-v", "--verbose",
                                   action="count", dest="verbose", default=0,
                                   help="Increment verbosity level" )
        self._parser.add_argument( "-q", "--quiet",
                                   action="store_true", dest="quiet", default=False,
                                   help="be vewwy quiet (I'm hunting wabbits)" )


if __name__ == "__main__" :
    assert(0, "not stand-alone")
