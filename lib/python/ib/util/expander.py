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
import pprint

class IbExpander( object ) :
    def __init__( self, defs=None ) :
        assert defs is None or isinstance(defs, dict)
        if defs is None :
            self._defs = { }
        else :
            self._defs = defs.copy()
        self._cache = { }
        self._verbose = 0

    def _getVerbose( self ) : return self._verbose
    def _setVerbose( self, v ) : self._verbose = v
    Verbose = property(_getVerbose, _setVerbose )

    def ExpandList( self, args ) :
        loops = 0
        if self._verbose >= 2 :
            print "Expanding:", args
            print "  using:", self._defs
        if type(args) == tuple :
            args = list(args)
        while True :
            initial = copy.copy(args)
            for n,arg in enumerate(args) :
                for key,value in self._defs.items() :
                    if key in self._cache :
                        s = self._cache[key]
                    else :
                        s = '${'+key+'}'
                        self._cache[key] = s
                    c = copy.copy(args)
                    if arg == s  and  type(value) == list :
                        expanded = self.ExpandList(value)
                        args = args[:n] + expanded + args[n+1:]
                        if self._verbose >= 3 :
                            print c, key+"="+str(expanded), "->", args
                        continue
                    if s in arg :
                        args[n] = arg.replace(s, str(value))
                        if self._verbose >= 3 :
                            print c, key+"="+str(value), "->", args
            if initial == args  or  loops > 10 :
                if self._verbose >= 2 :
                    print "Expanded:", args
                return args
            loops += 1

    def ExpandStr( self, s ) :
        if s is None :
            return None
        else :
            assert type(s) == str
        expanded = self.ExpandList( [s] )
        if len(expanded) == 1 :
            return expanded[0]
        else :
            return str(expanded)

    def ExpandItem( self, item ) :
        if item is None :
            return None
        elif type(item) == str :
            return self.ExpandStr( item )
        elif type(item) in (list, tuple) :
            return self.ExpandList( item )
        else :
            return item

    def Get( self, name, default=None ) :
        assert type(name) == str
        return self._defs.get(name, default)

    def Lookup( self, name ) :
        assert type(name) == str
        v = self._defs.get(name, None)
        return self.ExpandItem( v )

    def __setitem__( self, k, v ):
        assert type(k) == str
        self.Set(k, v)

    def __getitem__( self, k ):
        assert type(k) == str
        return self.Lookup( k )

    def __contains__( self, k ):
        return k in self._defs

    def Keys( self, filter=None ) :
        for k, v in self._defs.items( ) :
            if filter is None or filter(k, v) :
                yield k

    def KeyValues( self, expand=True, filter=None ) :
        for k, v in self._defs.items( ) :
            if filter is None or filter(k, v) :
                if expand :
                    yield k, self.ExpandItem( v )
                else :
                    yield k, v

    def Set( self, name, value, over=True ) :
        assert type(name) == str
        if name not in self._defs  or  over :
            self._defs[name] = value

    def SetDict( self, d, over=True ) :
        assert type(d) is dict
        for name,value in d.items() :
            self.Set( name, value, over )

    def Append( self, name, value ) :
        assert type(name) == str
        t = type(self._defs.get(name, None))
        if t is list :
            if type(value) in (list, tuple) :
                self._defs[name] += list(value)
            else :
                self._defs[name].append(value)
        elif t is dict :
            assert type(value) is dict
            for k,v in value :
                self._defs[name][k] = v
        elif t is str :
            self._defs[name] += str(value)
        else :
            assert False, "Don't know how to append to "+str(t)

    def Dump( self, expand, fp=sys.stdout ) :
        print self._defs
        for name in sorted(self._defs.keys()) :
            value = self._defs[name]
            if not expand :
                print name, "=", value
                continue

            expanded = value
            if type(value) == str :
                expanded = self.ExpandStr(value)
            elif type(value) in (int, bool, float) :
                pass
            elif type(value) in (list, tuple) :
                expanded = [ self.ExpandItem(v) for v in value ]
            elif type(value) == dict :
                expanded = { }
                for n,v in value.items( ) :
                    expanded[n] = self.ExpandItem(v)
            else :
                print >>sys.stderr, "I don't know how to expand", \
                    name, "with type", type(value)
            print name, "=", expanded, '('+str(type(value))+')'

    def Export( self, fpath ) :
        with open(fpath, 'w') as f :
            for k, v in self.KeyValues( ) :
                print >>f, '{:s}={:s}'.format( k, str(v) )
            f.close()

    @staticmethod
    def GetStringValue( s ) :
        if s == 'True' :
            return True
        elif s == 'False' :
            return False
        try :
            return int(s)
        except ValueError :
            pass
        try :
            return float(s)
        except ValueError :
            pass
        return s

    @classmethod
    def Import( cls, fpath ) :
        try :
            defs = IbExpander( )
            for n, line in enumerate(open(fpath)) :
                name, value = line.rstrip().split( '=', 1 )
                defs[name.strip()] = cls.GetStringValue(value)
            return defs
        except IOError as e :
            raise
        except ValueError :
            raise IbServerException("Failed to parse line %d" % (n) )


if __name__ == "__main__" :
    def Defs( env ) :
        return {
            "PID"       : os.getpid(),
            "Run"       : "${PID}",
            "Home"      : env["HOME"],
            "Devel"     : env.get("DEVEL", "${Home}/devel"),
            "PrjDevel"  : "${Devel}/project",
            "Build"     : env.get("BUILD", "${Devel}/build"),
            "PrjBuild"  : "${Build}/project",
            "Local"     : env.get("LOCAL", "${Devel}"),
            "ETC"       : env.get("ETC",   "${Devel}/etc"),
            "Var"       : env.get("VAR",   "${Local}/var"),
            "Log"       : env.get("LOG",   "${Var}/log"),
        }.copy()

    env = {"HOME":"/home/nick"}
    exp = IbExpander( Defs(env) )
    exp.Verbose = 2
    s = exp.ExpandStr("${Home}")
    assert s == "/home/nick", s
    s = exp.ExpandStr("${Log}")
    assert s == "/home/nick/devel/var/log", s
    s = exp.ExpandStr("${PrjDevel}")
    assert s == "/home/nick/devel/project", s
    s = exp.ExpandStr("${PrjBuild}")
    assert s == "/home/nick/devel/build/project", s

    env = {"HOME":"/home/nick", "DEVEL":"/local/devel/nick"}
    exp = IbExpander( Defs(env) )
    exp.Verbose = 2
    s = exp.ExpandStr("${Home}")
    assert s == "/home/nick", s
    s = exp.ExpandStr("${Log}")
    assert s == "/local/devel/nick/var/log", s
    s = exp.ExpandStr("${PrjDevel}")
    assert s == "/local/devel/nick/project", s
    s = exp.ExpandStr("${PrjBuild}")
    assert s == "/local/devel/nick/build/project", s

    env = {
        "HOME":"/home/nick",
        "LOCAL":"/local/nick",
        "BUILD":"/build/nick"}
    exp = IbExpander( Defs(env) )
    exp.Verbose = 2
    s = exp.ExpandStr("${Home}")
    assert s == "/home/nick", s
    s = exp.ExpandStr("${Build}")
    assert s == "/build/nick", s
    s = exp.ExpandStr("${Log}")
    assert s == "/local/nick/var/log", s
    s = exp.ExpandStr("${PrjDevel}")
    assert s == "/home/nick/devel/project", s
    s = exp.ExpandStr("${PrjBuild}")
    assert s == "/build/nick/project", s

class IbModule_util_expander( object ) :
    modulePath = __file__

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
