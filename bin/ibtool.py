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
from ibutil import *

class _Tool( object ) :
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


class _ToolGdb( _Tool ) :
    _gdb_prefix = ("${ToolName}",)
    def __init__( self, name ) :
        _Tool.__init__( self, name,
                        prefix=self._gdb_prefix,
                        tool_args="--args" )

class _ToolGdbCore( _Tool ) :
    _gdb_prefix = ("${ToolName}",)
    def __init__( self, name ) :
        _Tool.__init__( self, name,
                        prefix=self._gdb_prefix,
                        defs = {'Args':'${CoreFile'} )

class _ToolStrace( _Tool ) :
    _strace_prefix = ("${ToolName}",
                      "-o", "${ToolOut}")
    def __init__( self, name ) :
        _Tool.__init__( self, name, prefix=self._strace_prefix )

class _ToolValgrind( _Tool ) :
    _valgrind_prefix = ( "${ToolName}",
                         "--tool=${SubTool}",
                         "--log-file=${ToolOut}",
                         "--leak-check=full" )
    def __init__( self, name, defs ) :
        _Tool.__init__( self, name, prefix=self._valgrind_prefix, defs=defs )
    def Prefix( self ) :
        prefix = list(self._prefix) + [ "-v" for i in range(self._verbose) ]
        return prefix

class IbToolMain( object ) :
    _tools = {
        "none"     : _Tool( "none" ),
        "gdb"      : _ToolGdb( "gdb" ),
        "gdb-core" : _ToolGdbCore( "gdb" ),
        "strace"   : _ToolStrace( "strace" ),
        "valgrind" : _ToolValgrind("valgrind", defs={"SubTool":"memcheck"}),
        "helgrind" : _ToolValgrind("helgrind", defs={"SubTool":"helgrind"}),
    }

    _global_defs = {
        "PID"           : os.getpid(),
        "Run"           : "${PID}",
        "Devel"         : os.environ["QYLS_DEVEL"],
        "Var"           : os.environ.get("QYLS_VAR", "${Devel}/var"),
        "Log"           : "${Var}/log",
        "LogFiles"      : "${Log}/*",
        "Etc"           : os.environ.get("QYLS_ETC", "${Devel}/etc"),
        "EtcIn"         : os.environ.get("QYLS_ETC_IN", "${Devel}/etc.in"),
        "MakeArgs"      : [ ],
        "Cmd"           : [ "${Prog}", "${Args}" ],
        "IbEtc"         : "${EtcIn}/ironbee",
        "PreCmds"       : [ ["make", "-C", "${IbEtc}", "${MakeArgs}"] ],
    }

    def __init__( self, name, prefix, defs ) :
        self._name = name
        self._prefix = prefix
        self._defs = IbExpander( self._global_defs )
        self._defs.SetDict( defs )
        self._defs.Set( "Name", prefix)
        self._defs.Set( "NameLower", prefix.lower())
        self._defs.Set( "NameUpper", prefix.upper())

    Name = property(lambda self : self._defs.Get("Name"))
    NameLower = property(lambda self : self._defs.Get("NameLower"))
    NameUpper = property(lambda self : self._defs.Get("NameUpper"))

    def ParserSetup( self ) :
        self._parser = argparse.ArgumentParser( description="Run "+self._name+" with IronBee",
                                                prog=os.path.basename(sys.argv[0]) )
        self._parser.add_argument( "--default",
                                   action="store_const", dest="tool", default="none",
                                   const="none",
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

        self._parser.add_argument( "--dump-defs", "-d",
                                   action="store_const", const="dump",
                                   dest="dump_mode", default=None,
                                   help="Dump definition table and exit." )
        self._parser.add_argument( "--dump-expanded", "-de",
                                   action="store_const", dest="dump_mode", const="expand",
                                   help="Dump expanded definition table and exit." )

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

    def Parse( self ) :
        self._args, tool_args = self._parser.parse_known_args()
        self._args.tool_args = tool_args

    def Setup( self ) :
        for name,value in self._args.defs :
            self._defs.Set( name, value )
        self._tool = self._tools[self._args.tool]
        self._defs.SetDict( self._tool.Defs, over=False )

        if self._args.clean :
            files = [ ]
            varname = "${"+self._prefix+"LogFiles}"
            for expanded in self._defs.ExpandStr( varname ) :
                files += glob.glob(expanded)
            if len(files) :
                self._defs.Append("PreCmds", [ "rm" ] + files )
        if self._args.force_make :
            self._defs.Append("MakeArgs", "-B")
        self._tool.SetVerbose( self._args.verbose )

    def DumpTable( self ) :
        if self._args.dump_mode is None :
            return
        self._defs.Dump( self._args.dump_mode == "expand" )
        sys.exit(0)

    def RunPre( self ) :
        for cmd in self._defs.Lookup("PreCmds") :
            cmd = self._defs.ExpandItem(cmd)
            if not self._args.execute :
                print "Not running:", cmd
                continue
            if self._args.verbose :
                print "%s: Executing \"%s\"" % (self.Name, str(cmd))
            status = subprocess.call( cmd )
            if status :
                print "Exit status is", status

    def RunProgram( self ) :
        tmp = [ ]
        tmp += self._tool.Prefix( )
        tmp += self._tool.ToolArgs(self._args.tool_args)
        tmp += self._tool.ProgArgs(self._defs.Lookup("Cmd"))
        cmd = self._defs.ExpandItem( tmp )
        if len(cmd) == 0 :
            return

        if not self._args.execute :
            print "Not running:", cmd
            return

        outfile = self._defs.Lookup("Output")
        if outfile is not None :
            outfile = self.ExpandStr( outfile )

        if not self._args.quiet :
            print "Running:", cmd
            if outfile is not None :
                print "Output ->", outfile
        try :
            if self._args.output is None  and  outfile is None :
                status = subprocess.call( cmd )
            else :
                if self._args.output is not None :
                    out = self._args.output
                else :
                    out = open( outfile, "w" )
                p = subprocess.Popen( cmd,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT )
                for line in p.stdout :
                    print >>out, line.strip()
                    if self._args.verbose >= 2 :
                        print line.strip()
                p.wait()
                status = p.returncode
        except KeyboardInterrupt:
            status = 0
        if status :
            print "Exit status is", status
        if self._tool.ToolOut is not None :
            print self._tool.ToolName, "output is in", self._defs.ExpandStr(self._tool.ToolOut)

    Defs = property( lambda self : self._defs )

    def GetTool( self, name ) :
        return self._toos[name]

    def Main( self ) :
        self.ParserSetup( )
        self.Parse( )
        self.Setup( )
        self.DumpTable( )
        self.RunPre( )
        self.RunProgram( )


if __name__ == "__main__" :
    assert 0, "not stand-alone"
