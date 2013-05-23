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

class _InvalidProcess(BaseException) : pass
class _Process( object ) :
    def __init__( self, user, pid, ppid, cmd ) :
        try :
            self._user = user 
            self._pid = int(pid)
            self._ppid = int(ppid)
            self._cmd = cmd
        except ValueError as e :
            raise _InvalidProcess(e)
    User   = property(lambda self : self._user)
    PID    = property(lambda self : self._pid)
    PPID   = property(lambda self : self._ppid)
    Cmd    = property(lambda self : self._cmd)
    IsAts  = property(lambda self : 'traffic_server' in self._cmd)
    IsGdb  = property(lambda self : 'gdb ' in self._cmd)
    IsUser = property(lambda self : self._user == os.environ['USER'])

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

        self._parser.add_argument( "--pid",
                                   action="store", type=int, dest="pid", default=None,
                                   help="Set PID of ATS process" )
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

        self._parser.add_argument( "--signal-usr1", "--usr1",
                                   action="store_true", dest="sigusr1", default=False,
                                   help="Enable SIGUSR1 to create new IronBee engine" )
        self._parser.add_argument( "--signal-usr2", "--usr2",
                                   action="store_true", dest="sigusr2", default=False,
                                   help="Enable SIGUSR2 to shut down server" )

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


    def FindAtsPid( self ) :
        procs = { }
        cmd = [ 'ps', '-eo', 'user,pid,ppid,cmd' ]
        for line in subprocess.check_output(cmd).split('\n') :
            try :
                (user, pid, ppid, cmd) = re.split('\s+', line, 3)
                proc = _Process(user, pid, ppid, cmd)
                procs[proc.PID] = proc
            except ( _InvalidProcess, ValueError ) :
                pass
        pids = [ ]
        for pid in sorted(procs.keys()) :
            proc = procs[pid]
            if proc.IsUser and proc.IsAts and not proc.IsGdb :
                pids.append(pid)
        if len(pids) == 0 :
            print >>sys.stderr, "No ATS processes found"
            sys.exit(1)
        elif len(pids) != 1 :
            print >>sys.stderr, "Too many ATS processes found:"
            for pid in pids :
                print procs[pid].User, pid, procs[pid].Cmd
            sys.exit(1)
        return pids[0]

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
        if len(pids) == 0 :
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
            self._children[p.pid] = p
            return True
        except OSError as e :
            print cmd, ":", e
            return False

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
                #print "Shutting down", e
                #self.Shutdown( self._killsig, None )

    def MainLoop( self ) :
        curl = [ "/usr/bin/curl" ]
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
                (s, self._args.url, self._args.num_procs, self._args.pid)

        dev_null = open("/dev/null", "w")
        for proc in range(self._args.num_procs) :
            if self._shutdown :
                return
            cmd = list(curl)
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

            started = False
            while started == False :
                if self._max_procs is None  or  len(self._children) < self._max_procs :
                    started = self.StartCmd( cmd, label="#%d"%proc, out=dev_null )
                self.Delay( started )

            if self._shutdown :
                return
            if self._args.execute:
                if self._args.sigusr1 :
                    os.kill( self._args.pid, signal.SIGUSR1 )
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
        if self._args.execute and self._args.sigusr2 :
            print "Sending first USR2"
            os.kill( self._args.pid, signal.SIGUSR2 )
            time.sleep(5.0)
            print "Sending second USR2"
            os.kill( self._args.pid, signal.SIGUSR2 )

    def Main( self ) :
        self.ParseArgs()
        if self._args.pid is None :
            self._args.pid = self.FindAtsPid( )

        self.MainLoop()
        self.Wait()

main = _Main( )
main.Main( )
