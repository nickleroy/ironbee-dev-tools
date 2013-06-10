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
import os
import sys
import re
import subprocess
import argparse
import signal
import time
import random

_main = None

class _Main( object ) :
    class Command( object ) :
        def __init__( self, _name, _args, _help, _type=None, _nargs=0, _choices=None ) :
            assert type(_name) == str
            assert type(_args) == tuple
            assert type(_help) == str
            assert _type is None or type(_type) == type
            assert type(_nargs) in (int, str)

            self._name = _name
            self._args = _args
            self._help = _help
            self._type = _type
            self._nargs = _nargs
            self._choices = _choices
        Name = property( lambda self : self._name )
        Args = property( lambda self : self._args )
        Help = property( lambda self : self._help )
        Type = property( lambda self : self._type )
        NumArgs = property( lambda self : self._nargs )
        Choices = property( lambda self : self._choices )

        def Command( self, args ) :
            if args is None or self._nargs is 0:
                return self._name
            elif type(args) in (list,tuple) :
                return self._name+":"+":".join([str(a) for a in args])
            else :
                return self._name+":"+str(args)

        def __str__( self ) :
            return self._name

    # Commands to send to server
    _commands = (
        Command( "new-config",
                 ("--new-config",),
                 "Update the configuration file path" ),
        Command( "manager-create-engine",
                 ("--manager-create-engine", "--mce"),
                 "Create a new IronBee engine" ),
        Command( "manager-shutdown",
                 ("--manager-shutdown", "--ms"),
                 "Shut down the engine manager" ),
        Command( "manager-destroy",
                 ("--manager-destroy", "--md"),
                 "Destroy the engine manager",
                 _type=str, _nargs='?', _choices=("idle","non-current","all"), ),
        Command( "server-log-flush",
                 ("--server-log-flush", "--flush"),
                 "Cause server to flush the log messages" ),
        Command( "server-exit",
                 ("--server-exit", "--se"),
                 "Cause server to exit" ),
    )

    def __init__( self ) :
        self._children = { }
        self._shutdown = False

        self._parser = argparse.ArgumentParser( description="Send command to engine manager",
                                                prog="ib-engman.py" )

        # Command file
        self._parser.add_argument( "--command-file", "-c",
                                   action="store", dest="command_file",
                                   default="/tmp/ats-engine-manager.txt",
                                   help="Specify location of debug command file" )
        self._parser.set_defaults( command=None )
        class CommandAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                if namespace.command is not None :
                    parser.error( "Multiple commands \"\%s\"" % (option_string) )
                for command in _main._commands :
                    if option_string in command.Args :
                        namespace.command = command
                        namespace.command_args = values
                        break
                else :
                    parser.error( "Invalid command \"%s\"" % (option_string) )
        command_group = self._parser.add_mutually_exclusive_group(required=True)
        for command in self._commands :
            args = [a for a in command.Args]
            command_group.add_argument( *args,
                                         action=CommandAction,
                                         type=command.Type, nargs=command.NumArgs,
                                         choices=command.Choices,
                                         help=command.Help )

        self._parser.add_argument( "--server",
                                   action="store", dest="server", type=str, default="ATS",
                                   choices=("ATS", "Apache", "NGINX"),
                                   help="Specify server type" )
        self._parser.add_argument( "--server-port", "-p",
                                   action="store", dest="port", type=int, default=8181,
                                   help="Specify server port" )

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

    def ParseArgs( self ) :
        self._args = self._parser.parse_args()
        if self._args.server != "ATS" :
            self._parser.error( 'Currently only "ATS" server supported ("%s" specified)' %
                                (self_args.server) )

    def RunNc( self ) :
        cmd = ( "nc", "localhost", str(self._args.port) )
        null = open("/dev/null", "r")
        subprocess.call( cmd, stdin=null )

    def SendCommand( self, command ) :
        try :
            f = open( self._args.command_file, "w" )
            f.write(command)
            f.close()
            self.RunNc()
            if not self._args.quiet :
                print "Set command \"%s\" to \"%s\"" % (command, self._args.command_file)
        except IOError as e :
            print >>sys.stderr, "Unable to write to command file \"%s\": %s" % \
                (self._args.command_file, e)

    def SendCommands( self ) :
        command = self._args.command.Command(self._args.command_args)
        if self._args.execute :
            self.SendCommand( self._args.command.Command(self._args.command_args) )
        else :
            print "Not sending command \"%s\"" % ( command )

    def Main( self ) :
        self.ParseArgs()
        self.SendCommands()

_main = _Main( )
_main.Main( )
