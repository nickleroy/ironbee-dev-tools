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
from ibutil import *
from ibversion import *

class IbToolException(BaseException) : pass

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
    _valgrind_prefix = ( "valgrind",
                         "--tool=${SubTool}",
                         "--log-file=${ToolOut}")
    def __init__( self, name, defs, args=None ) :
        _Tool.__init__( self, name, prefix=self._valgrind_prefix, tool_args=args, defs=defs )
    def Prefix( self ) :
        prefix = list(self._prefix) + [ "-v" for i in range(self._verbose) ]
        return prefix

class _IbParser( argparse.ArgumentParser ) :
    def SetMain( self, main ) :
        self._main = main

class _CommandItem( object ) :
    def __init__( self, name, priority, argv, enabled=True ) :
        assert type(priority) == int
        assert type(argv) in (list, tuple)
        self._name = name
        self._priority = priority
        self._argv = tuple(argv)
        self._enabled = enabled
        self._is_make = len(argv)  and  'make' in argv[0]
        self._is_clean = self.IsMake and 'clean' in argv

    def _SetEnabled( self, enabled ) :
        self._enabled = enabled
    Name     = property( lambda self : self._name )
    Priority = property( lambda self : self._priority )
    Argv     = property( lambda self : self._argv )
    Enabled  = property( lambda self : self._enabled, _SetEnabled )
    IsMake   = property( lambda self : self._is_make )
    IsClean  = property( lambda self : self._is_clean )

class _CommandList( object ) :
    def __init__( self ) :
        self._commands = dict()

    def AddCommand( self, command ) :
        assert isinstance(command, _CommandItem)
        self._commands[command.Name] = command

    def Create( self, name, priority, command, enabled=True ) :
        new = _CommandItem( name, priority, command, enabled )
        self._commands[new.Name] = new

    def Get( self, name ) :
        return self._commands.get( name, None )

    def SetEnabled( self, name, enabled ) :
        self._commands[name].Enabled = enabled

    def GetSortedItems( self, fn=None ) :
        for name in sorted( self._commands.keys(), key = lambda n : self._commands[n].Priority ) :
            item = self._commands[name]
            if fn is None  or  fn(item) :
                yield item
        return

    def GetSortedCommands( self, fn=None ) :
        for item in self.GetSortedItems( self, fn=fn ) :
            yield item.Command
        return


class IbToolMain( object ) :
    _tools = {
        "none"     : _Tool( "none" ),
        "gdb"      : _ToolGdb( "gdb" ),
        "gdb-core" : _ToolGdbCore( "gdb" ),
        "strace"   : _ToolStrace( "strace" ),
        "valgrind" : _ToolValgrind("valgrind",
                                   args=("--leak-check=full",
                                         "--track-origins=yes",
                                         "--track-fds=yes",
                                         "--freelist-vol=200000000",
                                         "--fair-sched=no"),
                                   defs={"SubTool":"memcheck"}),
        "helgrind" : _ToolValgrind("helgrind",
                                   defs={"SubTool":"helgrind"}),
        "drd" : _ToolValgrind("drd",
                              defs={"SubTool":"drd"}),
    }

    _global_defs = {
        "PID"           : str(os.getpid()),
        "Run"           : "${PID}",
        "Devel"         : os.environ["QLYS_DEVEL"],
        "Var"           : os.environ.get("QLYS_VAR", "${Devel}/var"),
        "BaseLogDir"    : "${Var}/log",
        "LogDir"        : "${BaseLogDir}",
        "LogFiles"      : "${LogDir}/*",
        "Etc"           : os.environ.get("QLYS_ETC", "${Devel}/etc"),
        "EtcIn"         : os.environ.get("QLYS_ETC_IN", "${Devel}/etc.in"),
        "Tmp"           : os.environ["QLYS_TMP"],
        "MakeArgs"      : [ ],
        "Cmd"           : [ "${Executable}", "${Args}" ],
        "IbInstall"     : os.environ["IB_INSTALL"],
        "IbLibDir"      : os.environ["IB_LIBDIR"],
        "IbEtc"         : "${Etc}/ironbee",
        "IbEtcIn"       : "${EtcIn}/ironbee",
        "IbConfig"      : "${IbEtc}/${Short}.conf",
        "IbVersion"     : None,
        "IbRnsEtc"      : "${Etc}/rns-ironbee",
        "IbRnsEtcIn"    : "${EtcIn}/rns-ironbee",
        "LastFile"      : '.ib-${NameLower}.last',
        "LuaDir"        : os.path.join("${IbLibDir}", "lua"),
        "LuaPath"       : ";".join([s+"/?.lua" for s in
                                    ("${IbLibDir}", "${LuaDir}", "${Etc}/ironbee")]),
    }

    def __init__( self, defs ) :
        self._defs = IbExpander( self._global_defs )
        self._defs.SetDict( defs )
        name = self._defs.Lookup("Name")
        self._defs.Set( "NameLower", name.lower() )
        self._defs.Set( "NameUpper", name.upper() )

        cmds = _CommandList( )
        self._defs['PreCmds'] = cmds
        self.AddPrePair( 'Ib', '${IbEtcIn}' )
        cmds.Create('ClearLogs', 20, ('/bin/rm', '-fr', '${LogFiles}'))
        cmds = _CommandList( )
        self._defs['PostCmds'] = cmds

    FullName     = property(lambda self : self._defs.Lookup("FullName"))
    Name         = property(lambda self : self._defs.Lookup("Name"))
    NameLower    = property(lambda self : self._defs.Lookup("NameLower"))
    NameUpper    = property(lambda self : self._defs.Lookup("NameUpper"))
    PreCommands  = property(lambda self : self._defs.Get("PreCmds"))
    PostCommands = property(lambda self : self._defs.Get("PostCmds"))

    def ParserSetup( self ) :
        self._parser = _IbParser( description="Run "+self.FullName+" with IronBee",
                                  prog=os.path.basename(sys.argv[0]) )
        self._parser.SetMain( self )

        self._parser.set_defaults( require_core=False )
        class CoreAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                namespace.tool = "gdb-core"
                namespace.precmds = False
                namespace.write_last = False
                namespace.require_core = True
                if values[0] != '-' :
                    namespace.defs['CoreFile'] = values[0]
        self._parser.add_argument( "--core", action=CoreAction, nargs=1,
                                   help="Specify core file or \"-\" for last" )

        self._parser.add_argument( "--default",
                                   action="store_const", dest="tool", default="none",
                                   const="none",
                                   help="Run %s natively" % (self.Name) )
        self._parser.add_argument( "--gdb",
                                   action="store_const", dest="tool", const="gdb",
                                   help="Run %s under gdb" % (self.Name) )
        self._parser.add_argument( "--strace",
                                   action="store_const", dest="tool", const="strace",
                                   help="Run %s under strace" % (self.Name) )
        self._parser.add_argument( "--valgrind",
                                   action="store_const", dest="tool", const="valgrind",
                                   help="Run %s under valgrind (memcheck)" % (self.Name) )
        self._parser.add_argument( "--helgrind",
                                   action="store_const", dest="tool", const="helgrind",
                                   help="Run %s under helgrind" % (self.Name) )
        self._parser.add_argument( "--drd",
                                   action="store_const", dest="tool", const="drd",
                                   help="Run %s under valgrind/DRD" % (self.Name) )
        self._parser.add_argument( "--tsan",
                                   action="store_const", dest="tool", const="tsan",
                                   help="Run %s under TreadSanitizer" % (self.Name) )

        self._parser.add_argument( "--force-make", "-f",
                                   action="store_true", dest="force_make", default=False,
                                   help="Force execution of make in etc directories")

        class IbAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                if option_string == "--ib-config" :
                    namespace.defs['IbEtc'] = None
                    namespace.defs['IbConfig'] = values[0]
                elif len(values) == 0 :
                    namespace.defs['IbEtcIn'] = parser._main.Defs.Lookup("IbRnsEtcIn")
                else :
                    namespace.defs['IbEtcIn'] = values[0]
        self._parser.add_argument( "--rns", action=IbAction, nargs=0,
                                   help="Use the RNS IronBee etc")
        self._parser.add_argument( "--ib-etc", action="store", dest="ironbee_etc", nargs=1,
                                   help="Specify ironbee etc source directory" )
        self._parser.add_argument( "--ib-config", action=IbAction, nargs=1,
                                   help="Specify ironbee configuration" )
        
        def LogLevels( levels ) :
            count = len(levels)
            lower = [ l.lower() for l in log_levels ]
            nums  = [ str(n) for n in range(count) ]
            return tuple(lower + nums)

        log_levels = (
            "emergency",
            "alert",
            "critical",
            "error",
            "warning",
            "notice",
            "info",
            "debug",
            "debug2",
            "debug3",
            "trace"
            )
        rule_debug_levels = (
            "error",
            "warning",
            "notice",
            "info",
            "debug",
            "trace",
            )
        self._parser.add_argument( "--ib-log-level",
                                   dest="log_level", type=str, default=None,
                                   choices=LogLevels(log_levels),
                                   help='Specify IronBee log level')
        self._parser.add_argument( "--rule-log-level",
                                   dest="rule_log_level", type=str, default=None,
                                   choices=LogLevels(log_levels),
                                   help='Specify IronBee rule log level')
        self._parser.add_argument( "--rule-debug-level",
                                   dest="rule_debug_level", type=str, default=None,
                                   choices=LogLevels(rule_debug_levels),
                                   help='Specify IronBee rule debug level')

        self._parser.add_argument( "--clean",
                                   action="store_true", dest="clean", default=False,
                                   help="make clean in etc directories")

        self._parser.set_defaults( targets=("default",) )
        self._parser.add_argument( "--targets",
                                   action="store", dest="targets", nargs="+",
                                   help="Specify default make targets (in etc directories)")

        self._parser.set_defaults( tool_args=[] )
        class ToolArgsAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                for v in values :
                    namespace.tool_args += v.split(',')
        self._parser.add_argument( "--tool-args",
                                   action=ToolArgsAction, dest="tool_args", nargs=1,
                                   help="Specify tool arguments (with comma separator)")
        self._parser.add_argument( "--tool-arg",
                                   action="append", dest="tool_args",
                                   help="Specify single tool argument")

        self._parser.add_argument( "--out", "-o",
                                   dest="output", type=argparse.FileType('w'), default=None,
                                   help='Specify output file')
        self._parser.add_argument( "--default-out", "--do",
                                   action="store_const", dest="output",
                                   const="${DefaultOut}",
                                   help="Use default stdout file" )

        self._parser.add_argument( "--tmp",
                                   action="store_true", dest="tmp", default=False,
                                   help='Change to $QLYS_TMP directory before starting')

        self._parser.add_argument( "--clear-logs", "-c",
                                   action="store_true", dest="clear_logs", default=False,
                                   help="Clear log files before starting %s" % (self.Name) )

        self._parser.add_argument( "--disable-precmds", "--dp",
                                   action="store_false", dest="precmds", default=True,
                                   help="Disable running of pre-commands")

        self._parser.add_argument( "--disable-main", "--dm", "--no-main",
                                   action="store_false", dest="main", default=True,
                                   help="Disable running of "+self.Name )

        self._parser.add_argument( "--disable-make-n",
                                   action="store_false", dest="make_n", default=True,
                                   help='Disable running of "make -n" for --no-execute' )

        self._parser.add_argument( "--interface", "--if",
                                   action="store", dest="interface", default="NET",
                                   help="Specify IF_xxx interface to use" )
        self._parser.add_argument( "--net",
                                   action="store_const", dest="interface", const="NET",
                                   help="Use IF_NET (network) interface" )
        self._parser.add_argument( "--pub",
                                   action="store_const", dest="interface", const="PUB",
                                   help="Use IF_PUB (public) interface" )
        self._parser.add_argument( "--private",
                                   action="store_const", dest="interface", const="PRIV",
                                   help="Use IF_PRIV (private) interface" )
        self._parser.add_argument( "--loopback",
                                   action="store_const", dest="interface", const="LOOP",
                                   help="Use IF_LOOP (loopback) interface" )

        self._parser.set_defaults( ib_enable=True )
        class IbEnableAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                if 'enable' in option_string :
                    namespace.defs['IbEtc'] = '${EtcIn}/ironbee' # Restore default
                    namespace.ib_enable = True
                else :
                    namespace.defs['IbEtc'] = None
                    namespace.ib_enable = False
        self._parser.add_argument( "--enable-ib", action=IbEnableAction, nargs=0,
                                   help="Disable IronBee" )
        self._parser.add_argument( "--disable-ib", action=IbEnableAction, nargs=0,
                                   help="Disable IronBee" )

        self._parser.add_argument( "--read-last",
                                   action="store_true", dest="read_last", default=True,
                                   help="Enable reading of the last file")
        self._parser.add_argument( "--no-read-last",
                                   action="store_false", dest="read_last",
                                   help="Disable reading of the last file")
        self._parser.add_argument( "--write-last",
                                   action="store_true", dest="write_last", default=True,
                                   help="Enable writing of last file")
        self._parser.add_argument( "--no-write-last",
                                   action="store_false", dest="write_last",
                                   help="Disable writing of last file")

        self._parser.set_defaults( defs = {} )
        class StrAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                for s in values :
                    try :
                        name, value = s.split( '=', 1 )
                        namespace.defs[name.strip()] = value
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

        self._parser.add_argument( "--jobs", "-j",
                                   action="store", type=int, dest="max_jobs", default=0,
                                   help="Force number of # jobs to run" )
        self._parser.add_argument( "-1",
                                   action="store_const", dest="max_jobs", const=1,
                                   help="Force number of # jobs to run to 1 (-j 1)" )

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

    def CalcMaxJobs( self ) :
        cores = set()
        compiled = re.compile( r'core id\s+:\s+(\d+)' )
        for line in open( "/proc/cpuinfo" ) :
            m = compiled.match( line )
            if m is not None :
                cores.add( m.group(1) )
        aggression = 0.5
        return int(math.floor((len(cores) * aggression) + 0.5))

    def Parse( self ) :
        self._args = self._parser.parse_args()
        if self._args.max_jobs == 0 :
            self._args.max_jobs = self.CalcMaxJobs( )

    def GetIbVersion( self ) :
        if self._defs.Lookup( 'IbVersion' ) is not None :
            return
        libdir = self._defs.Lookup( 'IbLibDir' )
        tmp = IbVersionReader.FindFile( libdir )
        if tmp is None :
            self._parser.error( 'Unable to find library file in "'+libdir+'"' )
        self._args.path = tmp
        vreader = IbVersionReader( )
        version = vreader.GetAutoVersion( self._args.path )
        if version is None :
            sys.exit(1)
        self._version = version
        self._defs.Set( 'IbVersion', version.Format(r'%{1}.%{2}.%{3}') )

    def FindExecutable( self ) :
        for p in ("${Prog}", "${Prog}.bin") :
            path = self._defs.ExpandStr( p )
            if not os.path.islink( path ):
                self._defs.Set("Executable", p)
                break
        else :
            self._parser.error( "No %s binary found" % (self.NameUpper) )

    def SetupMakeArgs( self ) :
        if self._defs.Lookup('IbEtc') is None :
            self.PreCommands.SetEnabled('MakeIb', False)
        self._defs.Append("MakeArgs", "IB_ENABLE="+str(self._args.ib_enable))
        self._defs.Append("MakeArgs", "IB_VERSION="+self._defs.Lookup('IbVersion'))
        self._defs.Append("MakeArgs", "IB_CONFIG="+self._defs.Lookup('IbConfig'))
        self._defs.Append("MakeArgs", "LOG_DIR="+self._defs.Lookup('LogDir'))

        for post in ( "HOST", "DOMAIN", "FQDN", "IPADDR", "FULL" ) :
            envname = "IF_"+self._args.interface+"_"+post
            if envname in os.environ :
                self._defs.Append("MakeArgs", "QLYS_"+post+"="+os.environ[envname])

        if self._args.verbose :
            self._defs.Append("MakeArgs", "DUMP=dump")
            verbose = [ '-v' for n in range(self._args.verbose) ]
            self._defs.Append("MakeArgs", "VERBOSE="+' '.join(verbose))
        if self._args.max_jobs > 1 :
            self._defs.Append("MakeArgs", ("-j", str(self._args.max_jobs)) )
        if self._args.force_make :
            self._defs.Append("MakeArgs", "-B")
        if self._args.log_level is not None :
            self._defs.Append("MakeArgs", "LOG_LEVEL="+self._args.log_level)
        if self._args.rule_log_level is not None :
            self._defs.Append("MakeArgs", "RULE_LOG_LEVEL="+self._args.rule_log_level)
        if self._args.rule_debug_level is not None :
            self._defs.Append("MakeArgs", "RULE_DEBUG_LEVEL="+self._args.rule_debug_level)
        self._defs.Append("MakeArgs", self._args.targets)

    def AddPrePair( self, name, dirpath ) :
        base_cmd = ('make', '-C', dirpath, '${MakeArgs}')
        self.PreCommands.Create( 'Clean'+name, 10, base_cmd+('clean',) )
        self.PreCommands.Create( 'Make'+name,  11, base_cmd )

    def PostParse( self ) :
        for name,value in self._args.defs.items() :
            self._defs.Set( name, value )
        self.GetIbVersion( )
        self._tool = self._tools[self._args.tool]
        self._tool.SetVerbose( self._args.verbose )
        self._defs.SetDict( self._tool.Defs, over=False )
        if "IF_"+self._args.interface+"_HOST" not in os.environ :
            self._parser.error( 'Invalid interface "'+self._args.interface+'" specified' )
            
        self.FindExecutable( )
        self.SetupMakeArgs( )

        for pcmd in self.PreCommands.GetSortedItems( fn=lambda pc:pc.IsClean) :
            pcmd.Enabled = self._args.clean
        self.PreCommands.SetEnabled( 'ClearLogs', self._args.clear_logs )

        if self._args.read_last :
            self.ReadLastFile( )
        if self._args.require_core  and  'CoreFile' not in self._defs :
            self._parser.error( "No core file specified" )

    def GlobCmd( self, cmd ) :
        for n, arg in enumerate(cmd) :
            if n != 0  and  arg.endswith('*') :
                globbed = glob.glob(arg)
                l = len(globbed)
                if l == 0 :
                    return []
                cmd[n:n+1] = globbed
        return cmd

    def ReadDefsFile( self, fpath ) :
        try :
            n = 0
            f = open( fpath )
            for n, line in enumerate(f) :
                name, value = line.rstrip().split( '=', 1 )
                self._defs[name.strip()] = value
            f.close()
        except IOError as e :
            raise IbToolException(e)
        except ValueError :
            raise IbToolException("Failed to parse line %d" % (n) )

    def ReadLastFile( self ) :
        fpath = self._defs.Lookup( 'LastFile' )
        try :
            self.ReadDefsFile( fpath )
        except IbToolException as e :
            print >>sys.stderr, "Failed to read last file", fpath, ":", e

    def WriteLastFile( self, tool_out ) :
        fpath = self._defs.Lookup( 'LastFile' )
        if fpath is None :
            return
        print "Write last file", fpath
        try :
            f = open( fpath, 'w' )
            print >>f, "LastPid="+self._defs.Lookup( 'PID' )
            print >>f, "LastRun="+self._defs.Lookup( 'Run' )
            if tool_out is not None :
                cores = glob.glob(tool_out+".core*")
                for core in cores :
                    print >>f, "CoreFile="+core
            print >>f, "LastTool="+self._tool.ToolName
            if tool_out is not None :
                print >>f, "LastToolOut="+tool_out
            f.close()
        except IOError as e :
            print >>sys.stderr, "Failed to write to last file", fpath, ":", e

    def DumpTable( self ) :
        if self._args.dump_mode is None :
            return
        self._defs.Dump( self._args.dump_mode == "expand" )
        sys.exit(0)

    def RunPre( self ) :
        if not self._args.precmds :
            return
        for cmd in self.PreCommands.GetSortedItems( fn=lambda pc : pc.Enabled ) :
            argv = self.GlobCmd( self._defs.ExpandList(cmd.Argv) )
            if len(argv) == 0 :
                continue
            if not self._args.execute :
                if cmd.IsMake  and  self._args.verbose  and  self._args.make_n:
                    argv[1:1] = ( "-n", )
                else :
                    print "Not running:", argv
                    continue
            if self._args.verbose :
                print "%s: Executing \"%s\"" % (cmd.Name, str(argv))
            status = subprocess.call( argv )
            if status  and  not cmd.IsClean :
                print "Exit status is", status
                sys.exit(status)

    def RunProgram( self ) :
        tmp = [ ]
        tmp += self._tool.Prefix( )
        print self._args.tool_args
        print self._tool.ToolArgs(self._args.tool_args)
        tmp += self._tool.ToolArgs(self._args.tool_args)
        tmp += self._tool.ProgArgs(self._defs.Lookup("Cmd"))
        cmd = self._defs.ExpandItem( tmp )
        if len(cmd) == 0 :
            return

        outfile = self._defs.Lookup("Output")

        lpath = os.environ.get("LD_LIBRARY_PATH")
        libdir = self._defs.Lookup( "IbLibDir" )
        if lpath is None :
            lpath = libdir
        else :
            lpath += ":"+libdir
        os.environ['LD_LIBRARY_PATH'] = lpath
        if self._args.verbose :
            print "LD_LIBRARY_PATH set to", lpath

        luapath = os.environ.get('LUA_PATH')
        if luapath is None :
            luapath = self._defs.Lookup( "LuaPath" )
        else :
            luapath += ";"+self._defs.Lookup( "LuaPath" )
        os.environ['LUA_PATH'] = luapath
        if self._args.verbose :
            print "LUA_PATH set to", luapath

        if not self._args.execute  or  not self._args.main :
            print "Not running:", cmd
            return

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
        tool_out = None if self._tool.ToolOut is None else self._defs.ExpandStr(self._tool.ToolOut)
        if tool_out is not None :
            print self._tool.ToolName, "output is in", tool_out
        if self._args.write_last :
            self.WriteLastFile( tool_out )

    Defs = property( lambda self : self._defs )

    def GetTool( self, name ) :
        return self._tools[name]

    def Main( self ) :
        self.ParserSetup( )
        self.Parse( )
        self.PostParse( )
        self.DumpTable( )
        if self._args.tmp :
            os.chdir( self._defs.Lookup("Tmp") )
        self.RunPre( )
        self.RunProgram( )


if __name__ == "__main__" :
    assert 0, "not stand-alone"
