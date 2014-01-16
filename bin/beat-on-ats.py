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

class _Main( object ) :
    def __init__( self ) :
        self._children = { }
        self._shutdown = False
        self._killsig = signal.SIGTERM

        self._parser = argparse.ArgumentParser( description="Beat on ATS",
                                                prog="beat-on-ats.py" )

        self._parser.add_argument( "--num-procs", "-P",
                                   action="store", type=int, dest="num_procs", default=5,
                                   help="Set number of curl processes" )
        self._parser.add_argument( "--max-procs",
                                   action="store", type=int, dest="max_procs", default=None,
                                   help="Specify max number of concurrent curl processes "
                                   "(default=None)" )
        self._parser.add_argument( "--max-proc-ratio",
                                   action="store", type=float, dest="max_proc_ratio", default=None,
                                   help="Set maximum concurrent process ratio" )

        self._parser.add_argument( "--num-urls", "-N",
                                   action="store", type=int, dest="urls", default=5,
                                   help="Set number of URLs / curl" )
        self._parser.add_argument( "--random-urls",
                                   action="store", dest="random_urls", default=[],
                                   type=int, nargs=2,
                                   help="Set random number of URLs from <min> to <max>" )

        self._parser.add_argument( "--port", "-p",
                                   action="store", type=int, dest="port", default=8180,
                                   help="Set port number (default = 8180)" )
        self._parser.add_argument( "--proxy", "-x",
                                   action="store", dest="proxy", default=None,
                                   help="Set curl proxy (default = None)" )

        self._parser.add_argument( "--alarm",
                                   action="store", type=int, dest="alarm", default=20,
                                   help="Set alarm timeout (default=20s)" )
        self._parser.add_argument( "--delay",
                                   action="store", type=float, dest="delay", default=0.5,
                                   help="Specify delay between curls (seconds) (default=0.5s)" )
        self._parser.add_argument( "--no-delay",
                                   action="store_const", dest="delay", const=0.0,
                                   help="Set curl delay to zero" )
        self._parser.add_argument( "--random-delay",
                                   action="store", dest="random_delay", default=[],
                                   type=float, nargs=2,
                                   help="Set curl delay randomly to from <min> to <max>" )
        self._parser.add_argument( "--rate-limit",
                                   action="store", dest="rate_limit", default=None,
                                   help="Set the curl rate limit (default=None)" )

        # Command file and related commands
        self._parser.add_argument( "--command-file", "-c",
                                   action="store", dest="command_file",
                                   default="/tmp/engine-manager-debug.txt",
                                   help="Specify location of debug command file" )
        self._parser.add_argument( "--new-config",
                                   action="store", dest="new_config", default=None,
                                   help="Update the configuration file path" )

        # Engine creation options 
        class CreateAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                try :
                    if values == 'yes' :
                        namespace.create = 1.0
                    elif values == "no" :
                        namespace.create = 0.0
                    else :
                        namespace.create = float(values)
                except ValueError :
                    parser.error( "Invalid create value '"+s+"'" )
        self._parser.add_argument( "--create",
                                   action="store", dest="create", default=0.0, nargs=1,
                                   help="Set probability to create new IronBee engine [yes, no, (0.0 - 1.0)]" )

        self._parser.add_argument( "--shutdown",
                                   action="store_true", dest="shutdown", default=False,
                                   help="When done: cause server to shut down engine manager" )
        self._parser.add_argument( "--exit",
                                   action="store_true", dest="exit", default=False,
                                   help="When done: cause server to shutdown" )

        self._parser.add_argument( "--trace-dir",
                                   action="store", dest="trace_dir", default=".",
                                   help="Specify directory to hold trace files" )
        self._parser.add_argument( "--trace", "-t",
                                   action="store_true", dest="trace", default=False,
                                   help="Enable --trace-ascii arg to curl" )
        self._parser.add_argument( "--no-trace",
                                   action="store_false", dest="trace",
                                   help="Disable --trace-ascii arg to curl" )

        self._parser.add_argument( "--out-dir",
                                   action="store", dest="out_dir", default=".",
                                   help="Specify directory to hold curl output files" )
        self._parser.add_argument( "--out-files",
                                   action="store_true", dest="out_files", default=False,
                                   help="Write curl output to files" )
        self._parser.add_argument( "--out-null",
                                   action="store_true", dest="out_null", default=False,
                                   help="Write curl output to /dev/null" )

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

        self._parser.add_argument( "url",
                                   action="store", type=str, default=None, nargs='?',
                                   help="Specify URL" )

    def CheckDir( self, label, path ) :
        if path == "." :
            return
        if not os.path.exists(path) :
            os.makedirs(path)
        elif not os.path.isdir(path) :
            parser.error( "%s directory \"%s\" is not a directory"%(label, path) )

    def ParseArgs( self ) :
        self._args = self._parser.parse_args()
        if self._args.url is None :
            self._args.url = "http://localhost:%d" % (self._args.port)

        if self._args.max_proc_ratio is not None :
            self._max_procs = self._args.num_procs * self._args.max_proc_ratio
        elif self._args.max_procs is not None :
            self._max_procs = self._args.max_procs
        else :
            self._max_procs = self._args.num_procs
        self.CheckDir("Output", self._args.out_dir)
        self.CheckDir("Trace", self._args.trace_dir)

    def Reaper( self, signum, frame ) :
        count = 0
        while True :
            try :
                (pid, status ) = os.waitpid( -1, os.WNOHANG )
                if pid == 0 :
                    break
                if status == 0 :
                    self._extra_delay = 0.0 if self._extra_delay < 0.1 else self._extra_delay - 0.1
                else :
                    self._extra_delay += 0.03
                count += 1
                if pid in self._children :
                    del self._children[pid]
                    print "Process %d [exit status %d] (%d children)" % \
                        ( pid, status, len(self._children) )
                else :
                    print "Process %d [exit status %d] unknown; children: %s" % \
                        ( pid, status, sorted(self._children.keys()) )
            except OSError :
                break
        # Reset the alarm
        if count :
            signal.alarm( self._args.alarm )
        if len(self._children) == 0 :
            self._extra_delay = 0.0
            
    def Shutdown( self, signum, frame ):
        self._shutdown = True
        signal.signal(signal.SIGALRM, self.Shutdown)
        signal.alarm( self._args.alarm )
        pids = sorted(self._children.keys())
        if len(pids) == 0  and  not self._nc_running :
            print "Idle: bye!"
            sys.exit(0)
        if not self._args.quiet :
            print "Signal %d: Sending signal %d to %d children" % (signum, self._killsig, len(pids))
        if self._args.verbose :
            print "PIDS:", pids
        for p in pids :
            try :
                os.kill( p, self._killsig )
            except OSError :
                pass
        self._killsig = signal.SIGKILL

    def StartCmd( self, cmd, label=None, out=None ) :
        if self._args.execute == False :
            if label is None :
                print "Not executing:", cmd
            else :
                print "Not executing %s: %s" % (label, cmd)
            return True
        if not self._args.quiet :
            if label is None :
                print "Executing:", cmd
            else :
                print "Executing %s: %s" % (label, cmd)
        try :
            p = subprocess.Popen( cmd, stdout=out )
            if not self._args.quiet :
                print "Created child", p.pid
            self._children[p.pid] = p
            return True
        except OSError as e :
            print cmd, ":", e
            return False

    def RunNc( self ) :
        cmd = ( "nc", "localhost", str(self._args.port) )
        null = open("/dev/null", "r")
        self._nc_running = True
        s = subprocess.call( cmd, stdin=null )
        self._nc_running = False
        if s != 0 :
            self.Shutdown( signal.SIGALRM, None )

    def Delay( self, started ) :
        delay = 0.0
        extra_delay = self._extra_delay;
        if started == False :
            extra_delay += 5.0
        elif self._max_procs is not None and len(self._children) > self._max_procs :
            print "Throttling due to too many children (%d)" % len(self._children)
            extra_delay += 1.0
        elif len(self._args.random_delay) == 2 :
            delay += self._args.random_delay[0] + \
                (random.random() * (self._args.random_delay[1] - self._args.random_delay[0]))
        else :
            delay += self._args.delay
        if len(self._children) == 0 :
            extra_delay = 0.0
        extra_delay = min(extra_delay, 10.0)
        delay += extra_delay
        self._extra_delay = extra_delay

        start = time.time()
        end = start + delay
        while True :
            secs = end - time.time()
            if secs <= 0.0 :
                break
            try :
                if self._args.verbose :
                    print "Sleeping for %0.5gs" % (secs)
                time.sleep(secs)
            except IOError as e :
                print >>sys.stderr, "Sleep failed:", e
                break

    def Setup( self ) :
        curl = [ "/usr/bin/curl" ]
        if self._args.rate_limit is not None :
            curl += ['--limit-rate', self._args.rate_limit ]
        if self._args.verbose < 2 :
            curl += ['-s']
        self._curl = curl

        self._start_time = time.time()
        self._nc_running = False
        self._extra_delay = 0.0
        self._killsig = signal.SIGTERM

        signal.signal(signal.SIGCHLD, self.Reaper)
        signal.signal(signal.SIGALRM, self.Shutdown)
        signal.signal(signal.SIGTERM, self.Shutdown)
        signal.signal(signal.SIGQUIT, self.Shutdown)
        signal.signal(signal.SIGINT, self.Shutdown)

        if not self._args.quiet :
            if len(self._args.random_urls) :
                s = "%d - %d" % (self._args.random_urls[0], self._args.random_urls[1])
            else :
                s = str(self._args.urls)
            print "Forking curl with %s urls '%s' %d times, PID=%d" % \
                (s, self._args.url, self._args.num_procs, os.getpid())

    def BuildCurlCmd( self ) :
        cmd = list(self._curl)
        if self._args.trace :
            cmd +=  [ '--trace-ascii',
                      os.path.join(self._args.trace_dir,'ats-trace.%05d'%proc) ]
        if self._args.out_null :
            cmd +=  [ '-o', '/dev/null' ]
        elif self._args.out_files :
            cmd +=  [ '-o', os.path.join(self._args.out_dir,'ats-out.%05d'%proc) ]
        if self._args.proxy is not None :
            cmd +=  [ '--proxy', self._args.proxy ]
        if len(self._args.random_urls) == 2 :
            urls = random.randint(self._args.random_urls[0], self._args.random_urls[1])
        else :
            urls = self._args.urls
        cmd += [ self._args.url for n in range(urls) ]
        return cmd


    def MainLoop( self ) :
        dev_null = open("/dev/null", "w")
        for proc in range(self._args.num_procs) :
            if self._shutdown :
                return
            cmd = self.BuildCurlCmd( )
            while True :
                if self._shutdown :
                    break
                if self._max_procs is None  or  len(self._children) < self._max_procs :
                    started = self.StartCmd( cmd, label="#%d"%proc, out=dev_null )
                    if started :
                        break
                self.Delay( started )

            if self._shutdown :
                return
            if self._args.execute:
                if random.random() < self._args.create :
                    subprocess.call( ['ib-engman.py', '--create'] )
                pass


    def Wait( self ) :
        last = None
        signal.alarm( self._args.alarm )
        while len(self._children) :
            pids = len(self._children)
            if self._args.verbose  and  pids != last :
                print "Waiting for %d children" % (pids)
            last = pids
            time.sleep(1.0)

    def Final( self ) :
        if self._args.execute and self._args.shutdown :
            subprocess.call( ['ib-engman.py', '--disable'] )
            time.sleep(5.0)
            subprocess.call( ['ib-engman.py', '--shutdown'] )

        if self._args.execute and self._args.exit :
            subprocess.call( ['ib-engman.py', '--exit'] )

    def Main( self ) :
        self.ParseArgs()
        if self._args.num_procs :
            self.Setup()
            self.MainLoop()
            self.Wait()
        self.Final()

main = _Main( )
main.Main( )
