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

from ib.server.exceptions import *

class IbServerSiteOptions( object ) :
    def __init__( self, defs ) :
        self._CheckOptions( )
        self._defs = defs
        self._site_options = { }
        self._local_options = { }

    def _CheckOptions( self ) :
        if self._sites is None or self._options is None :
            return
        assert all( [type(i) in (tuple,list) for i in self._options.values()] )
        assert all( [type(i) in (tuple,list) for i in self._sites.values()] )
        options = set(self._options.keys() )
        sites = set(self._sites.keys() )
        assert options.intersection(sites) == set()
        allnames = options.union(sites)
        for vlist in self._sites.values( ) :
            assert all( [key in allnames for key in vlist] )
        self._option_names = []
        for name,keys in self._options.items( ) :
            self._option_names.append( name )
            for key in keys :
                if key.startswith( ('-','+') ) :
                    self._option_names.append( name+'.'+key[1:] )
                else :
                    self._option_names.append( name+'.'+key )

    def SetOptions( self, options, is_site ) :
        optdict = self._site_options if is_site else self._local_options
        for opt in options :
            if opt in self._options :
                item = self._options[opt]
                if len(item) == 0 :
                    optdict[opt] = True
                else :
                    optdict[opt] = { }
                    for i in item :
                        if i.startswith( ('-', '+') ) :
                            name = i[1:]
                            enable = i[0] == '+'
                        else :
                            name = i[1:]
                            enable = i[0] == '+'
                        if not optdict[opt].get( name, False ) :
                            optdict[opt][name] = enable
            elif opt in self._option_names :
                optdict[opt] = True
            else :
                raise IbServerUnknownOption(opt)

    def SetSites( self, sites ) :
        if 'Sites' not in self._defs :
            self._defs['Sites'] = { }
        if self._sites is None :
            return
        for site,enabled in sites.items() :
            if site not in self._sites :
                raise IbServerUnknownSite(site)
            self._defs['Sites'][site] = enabled
            tmp = site+'Site'
            if tmp not in self._site_options :
                self._site_options[tmp] = {}
            for name in self._sites[site] :
                if name in self._sites :
                    self.SetSites([name])
                elif type(name) in (list,tuple) :
                    self.SetOptions( name, True )
                else :
                    self.SetOptions( [name], True )

    def Setup( self, ib_version, sites, options ) :
        self._engine.SetIbVersion( ib_version )
        self.SetSites( sites )
        self.SetOptions( options, False )

        # For any option groups that we're specified, fill in an empty group
        if self._options is not None :
            for name in self._options.keys() :
                if name not in self._site_options :
                    self._site_options[name] = { }
        if self.Verbose :
            print "local options enabled:", self._local_options
            print "Site options enabled:", self._site_options
            print "Sites enabled:", self._defs['Sites']

    def IsOptionEnabled( self, name, default=False ) :
        try :
            return self._defs['Opts'][name]
        except KeyError :
            return default

    def IsSiteEnabled( self, name, default=False ) :
        try :
            return self._defs['Sites'][name]
        except KeyError :
            return default

    LocalOptions   = property( lambda self : self._local_options )
    SiteOptions    = property( lambda self : self._site_options )
    Verbose        = property( lambda self : self._defs['Verbose'] )
    Execute        = property( lambda self : self._defs['Execute'] )
    Quiet          = property( lambda self : self._defs['Quiet'] )
    Wipe           = property( lambda self : self._defs['Wipe'] )
    SourceRoot     = property( lambda self : self._engine.SourceRoot )
    DestRoot       = property( lambda self : self._engine.DestRoot )

class IbModule_server_site_options( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    assert False, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
