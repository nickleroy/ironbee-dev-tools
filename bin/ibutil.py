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

class IbDict( dict ):
    """
    Dictionary that allows for an associated getter function that's invoked
    automagically with any get.
    """
    class Value( object ) :
        def __init__( self, value, fn=None ) :
            self._value = value
            self._fn = fn

        def Get(self, data) :
            if self._fn is not None :
                self._fn(data, self._value)
            return self._value

        def __str__( self ) :
            return str(self._value)

        def __repr__( self ) :
            return str(self._value)

    def Set( self, k, v, fn=None, over=True ) :
        if over == False and k in self :
            return
        dict.__setitem__(self, k, self.Value(v, fn) )

    def __setitem__(self, k, v):
        dict.__setitem__(self, k, self.Value(v) )

    def __getitem__(self, k):
        v = dict.__getitem__(self, k)
        return v.Get( self )

    def Str( self ) :
        pp = pprint.PrettyPrinter(indent=2)
        return pp.pformat( self )


class IbExpander( object ) :
    def __init__( self, defs ) :
        assert isinstance(defs, dict)
        self._defs = defs.copy()
        self._verbose = 0

    def _getVerbose( self ) : return self._verbose
    def _setVerbose( self, v ) : self._verbose = v
    Verbose = property(_getVerbose, _setVerbose )

    def ExpandList( self, args ) :
        loops = 0
        if self._verbose >= 2 :
            print "Expanding:", args
            print "  using:", self._defs
        while True :
            initial = copy.copy(args)
            for n,arg in enumerate(args) :
                for key,value in self._defs.items() :
                    s = '${'+key+'}'
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
        else :
            return self.ExpandList( item )

    def Get( self, name ) :
        return self._defs.get(name, None)

    def Lookup( self, name ) :
        v = self._defs.get(name, None)
        return self.ExpandItem( v )

    def __setitem__(self, k, v):
        self.Set(k, v)

    def __getitem__(self, k):
        return self.Lookup( k )

    def Set( self, name, value, over=True ) :
        if name not in self._defs  or  over :
            self._defs[name] = value

    def SetDict( self, d, over=True ) :
        assert type(d) is dict
        for name,value in d.items() :
            self.Set( name, value, over )

    def Append( self, name, value ) :
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
            assert 0, "Don't know how to append to "+str(t)

    def Dump( self, expand ) :
        print self._defs
        for name in sorted(self._defs.keys()) :
            value = self._defs[name]
            if not expand :
                print name, "=", value
                continue

            expanded = value
            if type(value) == str :
                expanded = self.ExpandStr(value)
            elif type(value) == int :
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
            print name, "=", expanded


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


### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
