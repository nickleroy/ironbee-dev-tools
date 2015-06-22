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
import shutil
import collections
from functools import partial
import imp
import resource
import platform

from ib.util.dict           import *
from ib.util.expander       import *
from ib.util.version        import *
from ib.util.version_reader import *
from ib.util.parser         import *
from ib.util.dag            import *

import ib.server.tool.base
import ib.server.tool.gdb
import ib.server.tool.strace
import ib.server.tool.valgrind

from ib.server.exceptions import *
from ib.server.generator  import *
from ib.server.node       import *
from ib.server.dags       import *
from ib.server.template   import *

from ib.server.tool.base     import *
from ib.server.tool.gdb      import *
from ib.server.tool.strace   import *
from ib.server.tool.valgrind import *

class _ServerParser( IbBaseParser ) :
    def __init__( self, main ) :
        IbBaseParser.__init__( self, "Run "+main.ServerNameFull+" with IronBee" )
        self.Parser.add_argument( "--confirm",
                                  action="store_true", dest="confirm", default=False,
                                  help='Confirm before starting {}'.format(main.ServerName) )

        group = self.Parser.add_argument_group( )
        group.add_argument( "sites", type=str, nargs='+', default=[],
                            help="Specify site(s) to enable" )
        group.add_argument( '--ib-options', '--ib',
                            dest="ib_options", type=str, nargs='+', default=[],
                            help="Specify IronBee option(s)" )
        group.add_argument( '--srv-options',
                            dest="srv_options", type=str, nargs='+', default=[],
                            help="Specify server-specific option(s)" )

        self.Parser.set_defaults( require_core=False )
        class CoreAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                namespace.tool = "gdb-core"
                namespace.precmds = False
                namespace.write_last = False
                namespace.require_core = True
                if values[0] != '-' :
                    namespace.defs['LastCoreFile'] = values[0]
        self.Parser.add_argument( "--core", action=CoreAction, nargs=1,
                                  help="Specify core file or \"-\" for last" )

        group = self.Parser.add_argument_group( )
        group.add_argument( '--tool', '-t', default='none', dest='tool', choices=main.Tools.keys(),
                            help="Run {:1} under specified tool".format(main.ServerName) )
        self.Parser.set_defaults( tool_args=[] )
        class ToolArgsAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                for v in values :
                    namespace.tool_args += v.split(',')
        group.add_argument( "--tool-args",
                            action=ToolArgsAction, dest="tool_args", nargs=1,
                            help="Specify list of tool-specific arguments (comma separated)")
        group.add_argument( "--tool-arg",
                            action="append", dest="tool_args",
                            help="Specify single tool-specific argument")

        group = self.Parser.add_argument_group( )
        class IbAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                generators = main.Generators()
                v = values[0]
                if '/' in v or os.path.isdir(v) :
                    namespace.defs['IbEtcIn'] = None
                    namespace.defs['IbGenerator'] = v
                elif v in generators :
                    namespace.defs['IbGenerator'] = generators[v]
                else :
                    parser.error( 'Unknown generator name "{}"'.format(v) )
        group.add_argument( "--ib-config", '-C', action=IbAction, nargs=1,
                            help="Specify ironbee configuration" )
        group.add_argument( "--ib-etc", action="store", dest="ironbee_etc", nargs=1,
                            help="Specify ironbee etc source directory" )
        
        def LogLevels( levels ) :
            count = len(levels)
            lower = [ l.lower() for l in levels ]
            nums  = [ str(n) for n in range(count) ]
            return tuple(lower + nums)

        group = self.Parser.add_argument_group( )
        group.add_argument( "--ib-log-level",
                            dest="log_level", type=str, default=None,
                            choices=LogLevels(main._log_levels),
                            help='Specify IronBee log level')
        group.add_argument( "--rule-log-level",
                            dest="rule_log_level", type=str, default=None,
                            choices=LogLevels(main._log_levels),
                            help='Specify IronBee rule log level')
        group.add_argument( "--rule-debug-level",
                            dest="rule_debug_level", type=str, default=None,
                            choices=LogLevels(set(main._rule_debug_level_map)),
                            help='Specify IronBee rule debug level')

        self.Parser.set_defaults( wipe=None )
        group = self.Parser.add_argument_group( )
        group.add_argument( "--wipe", '-w',
                            action="store_true", dest="wipe",
                            help="Force wipe of etc directories (default=auto)")
        group.add_argument( "--no-wipe",
                            action="store_true", dest="wipe",
                            help="Force wipe of etc directories (default=auto)")

        self.Parser.add_argument( "--clear-logs", "-c",
                                   action="store_true", dest="clear_logs", default=False,
                                   help="Clear log files before starting {}".format(main.ServerName) )

        group = self.Parser.add_argument_group( )
        group.add_argument( "--out", "-o",
                            dest="output", type=argparse.FileType('w'), default=None,
                            help='Specify output file')
        group.add_argument( "--default-out",
                            action="store_const", dest="output",
                            const="${DefaultOut}",
                            help="Use default stdout file" )

        group = self.Parser.add_argument_group( )
        group.add_argument( "--log", "-l",
                            action="store", dest="logfile", default=None, type=argparse.FileType('a'),
                            help='Log activity to file')
        group.add_argument( "--tmp",
                            action="store_true", dest="tmp", default=False,
                            help='Change to $QLYS_TMP directory before starting')

        group = self.Parser.add_argument_group( )
        group.add_argument( "--disable-pre", "--no-pre",
                            action="store_false", dest="precmds", default=True,
                            help="Disable running of pre-commands")
        group.add_argument( "--disable-main", "--no-main",
                            action="store_false", dest="main", default=True,
                            help="Disable running of "+main.ServerName )
        group.add_argument( "--disable-post", "--no-post",
                            action="store_false", dest="postcmds", default=True,
                            help="Disable running of post-commands")


        class EnableAction( argparse.Action ) :
            def __call__(self, parser, namespace, values, option_string=None):
                v = True if option_string in ('--enable', '-e') else False
                for name in values :
                    namespace.defs['Enable'+name] = v
        group = self.Parser.add_argument_group( )
        group.add_argument( "--disable", '-d',
                            action=EnableAction, nargs='+',
                            help='Disable setting' )
        group.add_argument( "--enable", '-e',
                            action=EnableAction, nargs='+',
                            help='Enable setting' )

        self.Parser.add_argument( "--interface", "--if",
                                  action="store", dest="interface", default="NET",
                                  choices=('net', 'pub', 'private', 'loop'),
                                  help="Specify IF_xxx interface to use" )

        group = self.Parser.add_argument_group( )
        self.Parser.set_defaults( ib_enable=True )
        class IbEnableAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                if 'enable' in option_string :
                    namespace.defs['IbEtc'] = '${Etc}/ironbee' # Restore default
                    namespace.defs['IbEnable'] = True
                    namespace.ib_enable = True
                else :
                    namespace.defs['IbEtc'] = None
                    namespace.defs['IbEnable'] = False
                    namespace.ib_enable = False
        group.add_argument( "--enable-ib", action=IbEnableAction, nargs=0,
                            help="Disable IronBee" )
        group.add_argument( "--disable-ib", action=IbEnableAction, nargs=0,
                            help="Disable IronBee" )

        group = self.Parser.add_argument_group( )
        self.Parser.set_defaults( read_last=True, write_last=None )
        group.add_argument( "--read-last",
                            action="store_true", dest="read_last",
                            help="Enable reading of the last file")
        group.add_argument( "--no-read-last",
                            action="store_false", dest="read_last",
                            help="Disable reading of the last file")
        group.add_argument( "--write-last",
                            action="store_true", dest="write_last",
                            help="Enable writing of last file")
        group.add_argument( "--no-write-last",
                            action="store_false", dest="write_last",
                            help="Disable writing of last file")

        self.Parser.set_defaults( defs = {} )
        class SetAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                for s in values :
                    try :
                        name, value = s.split( '=', 1 )
                        namespace.defs[name.strip()] = IbExpander.GetStringValue( value )
                    except ValueError :
                        parser.error( "Invalid definition '"+s+"'" )
        self.Parser.add_argument( "--set",
                                  action=SetAction, nargs='+',
                                  help="Specify name=value definitions" )

        group = self.Parser.add_argument_group( )
        group.add_argument( "--dump-defs",
                            action="store_const", const="dump",
                            dest="dump_mode", default=None,
                            help="Dump definition table and exit." )
        group.add_argument( "--dump-expanded",
                            action="store_const", dest="dump_mode", const="expand",
                            help="Dump expanded definition table and exit." )
        group.add_argument( "--create-dot-files",
                            action="store_true", dest="create_dot_files", default=False,
                            help="Create 'dot' files of the DAGs" )
        group.set_defaults( auto_add_modules=True )
        group.add_argument( "--auto-add-modules",
                            action="store_true", dest="auto_add_modules",
                            help="Automatically add all modules as depenencies for all DAG nodes" )
        group.add_argument( "--no-auto-add-modules", "--na",
                            action="store_false", dest="auto_add_modules",
                            help="Disable --auto-add-modules" )

        group = self.Parser.add_argument_group( )
        group.add_argument( "--dag-debug",
                            dest="dag_debug", type=int, default=0,
                            help="Specify DAG debug level" )
        group.add_argument( "--dag-debug-file",
                            dest="dag_debug_file", type=argparse.FileType('w'), default=sys.stdout,
                            help="Specify DAG debug file" )


class _ServerDags( IbServerDags ) :
    def __init__( self, main ):
        self._main = main
        IbServerDags.__init__( self )

    def PopulateWipeIronbee( self, dag ) :
        IbDagNode( dag, 'wipe-Ironbee',
                   recipe=partial(self._main.WipeConfigDir, 'IbEtc', 'IronBee') )

    def PopulateWipeServer( self, dag ) :
        IbDagNode( dag, 'wipe-Server',
                   recipe=partial(self._main.WipeConfigDir, 'ServerEtc', 'Server') )

    def PopulatePreIronbee( self, dag ) :
        if self._main._args.ib_enable :
            self._main.ImportDag( dag, 'IbGenerator', 'IbEtcIn', 'IbEtc' )

    def PopulatePreServer( self, dag ) :
        self._main.ImportDag( dag, 'ServerGenerator', 'ServerEtcIn', 'ServerEtc' )
        vardirs = IbDagNode( dag, 'create-var-dirs',
                             always=True, is_default_target=True,
                             recipe=self._main.CreateVarDirs )
        clear = IbDagNode( dag, 'clear-logs',
                           always=True, is_default_target=True, parents=[vardirs],
                           recipe=self._main.ClearLogs )

    def PopulateMainIronbee( self, dag ) :
        if self._main._args.ib_enable :
            self._main.ImportDag( dag, 'IbGenerator' )

    def PopulateMainServer( self, dag ) :
        self._main.ImportDag( dag, 'ServerGenerator' )
        main = IbDagNode( dag, 'main', always=True, is_default_target=True,
                          recipe=self._main.RunMain )

    def PopulatePostIronbee( self, dag ) :
        if self._main._args.ib_enable :
            self._main.ImportDag( dag, 'IbGenerator' )

    def PopulatePostServer( self, dag ) :
        self._main.ImportDag( dag, 'ServerGenerator' )
        IbDagNode( dag, 'write-last',
                   recipe=self._main.WriteLastFile )


_Generator = collections.namedtuple( 'Generator', ( 'Name', 'Module', 'Generator' ) )

class IbServerMain( object ) :
    _tools       = None
    _sys         = None
    _global_defs = None

    @classmethod
    def _InitClass( cls ) :
        if cls._tools is None :
            cls._InitTools( )
        if cls._sys is None :
            cls._InitSys( )
        if cls._global_defs is None :
            cls._InitGlobalDefs( )

    @classmethod
    def _InitTools( cls ) :
        cls._tools = { }
        regex = re.compile( r'IbServerTool\w+Tools' )
        for name in globals().keys() :
            if regex.match(name) :
                cls._tools.update( globals()[name] )

    @classmethod
    def _InitSys( cls ) :
        def _sys_get( env, _type, default ) :
            if env in os.environ :
                return _type(os.environ.get(env))
            else :
                return _type(default)

        arch = platform.architecture()
        bits = int(re.match(r'(\d+)bit', arch[0]).group(1))
        distro = platform.linux_distribution( )
        lib = 'lib'+str(bits) if bits > 32 else 'lib'
        cls._sys = {
            'bits'    : _sys_get('SYS_BITS', int, bits),
            'distro'  : _sys_get('SYS_DISTRO_FULL', str, '-'.join([s.strip() for s in distro]) ),
            'arch'    : _sys_get('SYS_ARCH', str, distro[2]),
            'lib'     : _sys_get('SYS_LIB', str, lib),
            'libexec' : _sys_get('SYS_LIBEXEC', str, 'libexec' if len(glob.glob('/usr/libexec/*')) else 'lib' )
        }

    @staticmethod
    def Generators( ) :
        ibconfigs = os.environ.get('IB_GENERATORS', 'ib:${IbMainGenerator}')
        return dict([c.split(':',1) for c in ibconfigs.split(',')])

    @classmethod
    def _InitGlobalDefs( cls ) :
        cls._global_defs = {
            "PID"              : str(os.getpid()),
            "Run"              : "${PID}",
            "SysLibName"       : cls._sys['lib'],
            "SysLibExec"       : cls._sys['libexec'],
            "Devel"            : os.environ["QLYS_DEVEL"],
            "Var"              : os.environ.get("QLYS_VAR", "${Devel}/var"),
            "BaseLogDir"       : "${Var}/log",
            "VarRun"           : "${Var}/run",
            "Etc"              : os.environ.get("QLYS_ETC", "${Devel}/etc"),
            "EtcIn"            : os.environ.get("QLYS_ETC_IN", "${Devel}/etc.in"),
            "Tmp"              : os.environ["QLYS_TMP"],
            "Cmd"              : [ "${Executable}", "${Args}" ],
            "IbInstall"        : os.environ["IB_INSTROOT"],
            "IbLibDir"         : os.environ["IB_LIBDIR"],
            "IbLibExec"        : os.environ["IB_LIBEXEC"],
            "IbLogDir"         : "${BaseLogDir}/ironbee",
            "IbEtc"            : "${Etc}/ironbee",
            "IbEtcIn"          : "${EtcIn}/ironbee",
            "IbEnable"         : True,
            "IbMainGenerator"  : os.environ.get('IB_GENERATOR', "${IbEtcIn}/ib_generator.py"),
            "IbConfigFile"     : "${ServerNameShort}.conf",
            "IbConfigFull"     : "${IbEtc}/${IbConfigFile}",
            "IbGenerators"     : IbServerMain.Generators(),
            "IbVersion"        : None,
            "TxLogDir"         : "${IbLogDir}/txlogs",
            "RnsEtc"           : "${Etc}/rns-ironbee",
            "RnsEtcIn"         : "${EtcIn}/rns-ironbee",
            "RnsGenerator"     : "${EtcIn}/rns-ironbee/rns_generator.py",
            "IbLogLevel"       : "debug",
            "IbRuleLogLevel"   : "debug",
            "IbRuleDebugLevel" : "debug",
            "LastFile"         : '.ib-${ServerNameLower}.last',
            "LuaDir"           : os.path.join("${IbLibDir}", "lua"),
            "LuaPath"          : ";".join([s+"/?.lua" for s in
                                           ("${IbLibDir}", "${LuaDir}", "${Etc}/ironbee")]),
        }

    _log_levels = (
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
        "trace",
    )
    _rule_debug_level_map = collections.OrderedDict(
        (
            ( "error",   ( "emergency", "alert", "critical", "error" ) ),
            ( "warning", ( "warning", ) ),
            ( "notice",  ( "notice", ) ),
            ( "info",    ( "info", ) ),
            ( "debug",   ( "debug", "debug2", "debug3" ) ),
            ( "trace",   ( "trace", ) ),
        )
    )

    def __init__( self, defs ) :
        self._InitClass( )
        self._defs = IbExpander( self._global_defs )
        self._defs.SetDict( defs )
        name = self._defs.Lookup("ServerName")
        self._defs.Set( "ServerNameLower", name.lower() )
        self._defs.Set( "ServerNameUpper", name.upper() )
        self._wipe = False
        self._generators = { }

    IronBeeVersion  = property(lambda self : self._ib_version)
    ServerNameFull  = property(lambda self : self._defs.Lookup("ServerNameFull"))
    ServerNameShort = property(lambda self : self._defs.Lookup("ServerNameShort"))
    ServerName      = property(lambda self : self._defs.Lookup("ServerName"))
    ServerNameLower = property(lambda self : self._defs.Lookup("ServerNameLower"))
    ServerNameUpper = property(lambda self : self._defs.Lookup("ServerNameUpper"))
    Tools           = property(lambda self : self._tools)
    Parser          = property(lambda self : self._parser)
    Defs            = property(lambda self : self._Defs)

    def Lookup( self, name ) :
        return self._defs.Lookup( name )

    def _MapLogLevelToRuleDebug( self, log_level ) :
        if log_level.isdigit() :
            name = self._log_levels[int(log_level)]
            for level,item in self._rule_debug_level_map.items() :
                if name in item[1] :
                    self._defs['IbRuleDebugLevel'] = str(level)
                    break
            else :
                assert False, 'No matching rule debug level for level {:s} "{:s}"'. \
                    format(log_level, name)
        else :
            for item in self._rule_debug_level_map.values :
                if log_level in items[1] :
                    self._defs['IbRuleDebugLevel'] = items[0]
                    break
            else :
                assert False, 'No matching rule debug level for level "{:s}"'. \
                    format(log_level)

    def _Parse( self ) :
        self._args = self.Parser.Parse()
        if self._args.write_last is None :
            self._args.write_last = self._args.execute

    def _GetIbVersion( self ) :
        if self._defs.Lookup( 'IbVersion' ) is not None :
            return
        libdir = self._defs.Lookup( 'IbLibDir' )
        tmp = IbVersionReader.FindFile( libdir )
        if tmp is None :
            self.Parser.Error( 'Unable to find library file in "'+libdir+'"' )
        self._args.path = tmp
        vreader = IbVersionReader( )
        version = vreader.GetAutoVersion( self._args.path )
        if version is None :
            sys.exit(1)
        self._ib_version = version
        self._defs.Set( 'IbVersion', version.Format(r'%{1}.%{2}.%{3}') )

    def _FindExecutable( self ) :
        for p in ("${Prog}", "${Prog}.bin") :
            path = self._defs.ExpandStr( p )
            if not os.path.islink( path ):
                self._defs.Set("Executable", p)
                break
        else :
            self.Parser.Error( "No {} binary found".format(self.ServerNameUpper) )
        
    def WipeConfigDir( self, name, pretty, node ) :
        path = self._defs.Lookup( name )
        if path is None :
            return 0, None
        if self._wipe is False :
            if self._args.verbose :
                print 'Not wiping {:s} configuration in "{:s}"'.format(pretty, path)
            return 0, None
        if not self._args.quiet :
            print 'Wiping {:s} configuration in "{:s}"'.format(pretty, path)
        if self._args.execute  and  os.path.isdir( path ) :
            shutil.rmtree( path )
        if self._args.execute :
            print 'Creating {:s} configuration in "{:s}"'.format(pretty, path)
            os.makedirs( path )
        return 0, None

    def ClearLogs( self, node ) :
        if not self._args.clear_logs :
            return 0, None
        dirs = set()
        for name in ( 'LogDir', 'IbLogDir', 'ServerLogDir' ) :
            logdir = self._defs.Lookup( name )
            if logdir is None  or  name in dirs :
                continue
            dirs.add( name )
            if not self._args.quiet :
                print 'Clearing logs in "{:s}"'.format( logdir )
            if self._args.execute  and  os.path.isdir( logdir ) :
                shutil.rmtree( logdir )
        return 0, None

    def CreateVarDirs( self, node ) :
        for name in ( 'LogDir', 'IbLogDir', 'TxLogDir', 'ServerLogDir', 'VarRun' ) :
            logdir = self._defs.Lookup( name )
            if logdir is not None  and  not os.path.isdir( logdir ) :
                os.makedirs( logdir )
        return 0, None

    def _Generator( self, name ) :
        if name in self._generators :
            return self._generators[name]
        genpath = self._defs.Lookup( name )
        if genpath is None :
            self._generators[name] = None
            return None
        try :
            path, filename = os.path.split( genpath )
            filename = filename.replace('.py', '')
            if path == '' :
                pypath = None
            else :
                pypath = [path]+os.environ['PYTHONPATH'].split(':')
            print pypath
            fp, modpath, descr = imp.find_module( filename, pypath )
            mod = imp.load_module( filename, fp, modpath, descr )
            try :
                obj = mod.Instantiate(self._defs)
                assert isinstance( obj, IbServerBaseGenerator )
                generator = _Generator( name, mod, obj )
                self._generators[name] = generator
                return generator
            except AttributeError as e :
                raise IbServerInvalidGenerator( '"'+genpath+'" '+str(e) )
        except ImportError as e :
            raise IbServerNoGenerator( e )
            
    def ImportDag( self, dag, name, srcname=None, destname=None ) :
        try :
            generator = self._Generator( name )
        except IbServerInvalidGenerator as e :
            print >>sys.stderr, 'Invalid generator "{:s}": {:s}'.format( name, str(e) )
            sys.exit(1)
        if generator is None :
            return
        for d in [dag]+list(dag.Parents) :
            try :
                fn = generator.Generator[d.Name]
                if fn is not None :
                    srcdir  = None if srcname  is None else self._defs.Lookup( srcname )
                    destdir = None if destname is None else self._defs.Lookup( destname )
                    if srcdir is not None :
                        dag.Path = srcdir
                    fn( dag, self, srcdir, destdir )
                break
            except KeyError :
                continue
        else :
            raise IbServerInvalidGenerator( name )

    def _LoadGenerator( self, name, sites, flags ) :
        try :
            generator = self._Generator( name )
            allsites = { }
            for name in generator.Generator.SiteNames() :
                allsites[name] = name in sites
            generator.Generator.Setup( self.IronBeeVersion, allsites, flags )
        except IbServerNoGenerator as e :
            print >>sys.stderr, ( 'No generator "{:s}"'.format(name) )
        except IbServerInvalidGenerator as e :
            print >>sys.stderr, 'Invalid generator: {:s}'.format( str(e) )
            sys.exit(1)
        except IbServerUnknownSite as e :
            self.Parser.Error( 'Unknown site "{:s}"'.format( str(e) ) )
        except IbServerUnknownOption as e :
            self.Parser.Error( 'Unknown option "{:s}"'.format( str(e) ) )

    def _WipeNames( self ) :
        regex = re.compile( r'(EtcIn|Enable|Generator|Level|Version|Install|LibDir|Mode)' )
        names = [ key for key in self._defs.Keys(lambda k,v : regex.search(k)) ]
        return names

    def _PostParse( self ) :
        # Setup DAGs, hostname, etc
        self._dags = _ServerDags( self )

        if "IF_"+self._args.interface+"_IPADDR" not in os.environ :
            self.Parser.Error( 'Invalid interface "'+self._args.interface+'" specified' )

        hmap = {
            "HOST":"Hostname",
            "DOMAIN":"Domain",
            "FQDN":"FQDN",
            "IPADDR":"IPAddress",
            "FULL":"FullHostname",
        }
        for post,remap in hmap.items() :
            envname = "IF_"+self._args.interface+"_"+post
            if envname in os.environ :
                self._defs[remap] = os.environ[envname]

        # Import basic settings
        self._defs['Execute'] = self._args.execute
        self._defs['Verbose'] = self._args.verbose
        self._defs['Quiet']   = self._args.quiet

        # Import IronBee log-level settings
        if self._args.log_level is not None :
            self._defs['IbLogLevel'] = self._args.log_level
            self._defs['IbRuleLogLevel'] = self._args.log_level
            self._defs['IbRuleDebugLevel'] = self.MapLogLevelToRuleDebug( self._args.log_level )
        if self._args.rule_log_level is not None :
            self._defs['IbRuleLogLevel'] = self._args.rule_log_level
        if self._args.rule_debug_level is not None :
            self._defs['IbRuleDebugLevel'] = self._args.rule_debug_level

        # Import all of the settings from the command line
        for name,value in self._args.defs.items() :
            self._defs.Set( name, value )

        self._defs["UserName"] = os.environ['USER']
        self._GetIbVersion( )

        # Create the IronBee and server generators, set their mode
        self._LoadGenerator( 'IbGenerator', self._args.sites, self._args.ib_options )
        self._LoadGenerator( 'ServerGenerator', self._args.sites, self._args.srv_options )

        # Re-import all values from the command line that may have been over-ridden
        # by the mode setting
        for name,value in self._args.defs.items() :
            self._defs.Set( name, value )

        self._tool = self._tools[self._args.tool]
        self._tool.SetVerbose( self._args.verbose )
        self._defs.SetDict( self._tool.Defs, over=False )
        self._FindExecutable( )
        self._dags.SetupDags( )

    def _ReadLastFile( self ) :
        fpath = self._defs.Lookup( 'LastFile' )
        try :
            if self._args.verbose :
                print "Reading last file", fpath, "from", os.path.abspath('.')
            defs = IbExpander.Import( fpath )
            if 'CoreFiles' in defs :
                self._defs['LastCoreFile'] = defs['CoreFiles'][0]
            return defs
        except IOError :
            return IbExpander( )

    def WriteLastFile( self, node ) :
        fpath = self._defs.Lookup( 'LastFile' )
        if fpath is None  or  not self._args.write_last :
            return
        if self._args.verbose :
            print "Writing last file", fpath
        try :
            self._defs.Export( fpath )
            return 0, None
        except IOError as e :
            print >>sys.stderr, "Failed to write to last file", fpath, ":", e
            return 1, 'WriteLastFile() Failed'

    def _DumpTable( self ) :
        if self._args.dump_mode is None :
            return
        self._defs.Dump( self._args.dump_mode == "expand" )
        sys.exit(0)

    def _PreMain( self ) :
        if self._args.read_last :
            self._last_defs = self._ReadLastFile( )
        else :
            self._last_defs = IbExpander( )
        if self._args.require_core  and  'CoreFile' not in self._defs :
            self.Parser.Error( "No core file specified" )
        if self._args.wipe is None :
            for name in self._WipeNames( ) :
                if self._defs.Lookup(name) != self._last_defs.Get(name) :
                    if not self._args.quiet :
                        print 'Triggering wipe: name={:s} "{:s}" != "{:s}"'.format(
                            name, str(self._defs.Lookup(name)), str(self._last_defs.Get(name))
                        )
                    self._wipe = True
                    break
            else :
                self._wipe = False
        else :
            self._wipe = self._args.wipe

    def RunMain( self, node ) :
        tmp = [ ]
        tmp += self._tool.Prefix( )
        tmp += self._tool.ToolArgs(self._args.tool_args)
        tmp += self._tool.ProgArgs(self._defs.Lookup("Cmd"))
        cmd = self._defs.ExpandItem( tmp )
        assert len(cmd) != 0

        lpath = os.environ.get("LD_LIBRARY_PATH")
        libdir = self._defs.Lookup( "IbLibDir" )
        if lpath is None :
            lpath = libdir
        else :
            lpath += ":"+libdir
        os.environ['LD_LIBRARY_PATH'] = lpath
        if self._args.verbose > 1 :
            print "LD_LIBRARY_PATH set to", lpath

        luapath = os.environ.get('LUA_PATH')
        if luapath is None :
            luapath = self._defs.Lookup( "LuaPath" )
        else :
            luapath += ";"+self._defs.Lookup( "LuaPath" )
        os.environ['LUA_PATH'] = luapath
        if self._args.verbose > 1 :
            print "LUA_PATH set to", luapath

        if not self._args.execute  or  not self._args.main :
            print "Not running:", cmd
            return 0, None

        outfile = self._defs.Lookup("Output")
        if not self._args.quiet :
            print "Running:", cmd
            if outfile is not None :
                print "Output ->", outfile

        if self._args.confirm :
            answer = raw_input( 'Start "{}" (Y/n)? ' )
            if answer.lower in ('no','n') :
                return 0
        try :
            resource.setrlimit(resource.RLIMIT_CORE,
                               (resource.RLIM_INFINITY,resource.RLIM_INFINITY))
            if self._args.output is None  and  outfile is None :
                status = subprocess.call( cmd )
                if self._args.logfile is not None :
                    print >>self._args.logfile, '  PID {} "{}" status {}'.format('?', cmd, status)
            else :
                outfile = self._defs.ExpandStr( '.ib-${ServerNameLower}.${PID}.out' )
                errfile = self._defs.ExpandStr( '.ib-${ServerNameLower}.${PID}.err' )
                if self._args.output is not None :
                    out = self._args.output
                else :
                    out = open( outfile, "w+", 0 )
                err = open( errfile, 'w', 0 )
                p = subprocess.Popen( cmd, stdout=out, stderr=err )
                pid = p.pid
                if self._args.verbose :
                    print "Process is", p.pid
                for line in out :
                    if out != sys.stdout  and  self._args.verbose >= 2 :
                        print line.strip()
                status = p.wait()
                if self._args.logfile is not None :
                    print >>self._args.logfile, '  PID {} "{}" status {}'.format(pid, cmd, status)
        except KeyboardInterrupt:
            status = 0
        if status :
            print "Exit status is", status
        tool_out = None if self._tool.ToolOut is None else self._defs.ExpandStr(self._tool.ToolOut)
        if tool_out is not None :
            self._defs['ToolOutput'] = tool_out
            print self._tool.ToolName, "output is in", tool_out
            cores = glob.glob(tool_out+'.core*')
            if len(cores) :
                print "Core dumps found:", cores
            self._defs['CoreFiles'] = cores

        return status, 'Exit status is {}'.format(status)

    Defs = property( lambda self : self._defs )

    def GetTool( self, name ) :
        return self._tools[name]

    def Main( self ) :
        self._parser = _ServerParser( self )
        self._Parse( )
        self._PostParse( )
        self._PreMain( )
        self._DumpTable( )
        if self._args.tmp :
            os.chdir( self._defs.Lookup("Tmp") )
        if self._args.logfile is not None :
            print >>self._args.logfile, '-- Starting {} @ {} --'.format(os.getpid(), time.asctime())
            print >>self._args.logfile, '  {}'.format(sys.argv)
        self._dags.Evaluate( )
        if self._args.dag_debug :
            print >>self._args.dag_debug_file, '---- DAG debug Start -----'
            self._dags.Dump( debug=self._args.dag_debug-1, debug_fp=self._args.dag_debug_file )
        self._dags.Execute( debug=self._args.dag_debug, debug_fp=self._args.dag_debug_file )
        if self._args.dag_debug :
            #s = raw_input( 'OK / Failed? ' )
            s = ''
            print >>self._args.dag_debug_file, '---- DAG debug {} End -----'.format(s)


class IbModule_server_main( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    assert False, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
