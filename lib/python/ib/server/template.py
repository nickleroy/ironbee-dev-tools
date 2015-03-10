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
import sys
import os
import re
import pprint
import jinja2
import jinja2.ext

from ib.util.version           import *
from ib.server.exceptions      import *
from ib.server.template_engine import *

class IbServerTemplate( object ) :
    _num_regex = re.compile( r'(\d+)' )
    def __init__( self, engine, inpath, outpath ) :
        """
        Initialize the server template.
        engine: IbServerTempleEngine instance
        inpath: Input file path relative to the source root
        outpath: Output file path relative to the destination root
        """
        assert isinstance( engine, IbServerTemplateEngine )
        self._engine = engine
        self._in   = inpath
        self._in_full = os.path.join( engine.SourceRoot, inpath )
        self._out  = os.path.join( engine.DestRoot, outpath )

    def _MergeIn( self, tvars, key, value ) :
        keys = key.split('.',2)
        if min( [len(k) for k in keys] ) == 0 :
            raise IbServerDefError(key)
        key0 = keys[0]
        key1 = keys[1] if len(keys) > 1 else None
        key2 = keys[2] if len(keys) > 2 else None
        if len(keys) == 1 :
            tvars[key0] = value
        elif len(keys) == 2  and  key0 in tvars :
            tvars[key0][key1] = value
        elif len(keys) == 2 :
            tvars[key0] = { key1 : value }
        elif len(keys) == 3  and  key0 in tvars  and  key1 in tvars[key0] :
            tvars[key0][key1][key2] = value
        elif len(keys) == 3  and  key0 in tvars :
            tvars[key0][key1] = { key2 : value }
        elif len(keys) == 2 :
            tvars[key0] = { key1 : { key2 : value } }

    def Render( self, generator ) :
        if not self._engine.Execute :
            if self._engine.Verbose :
                print 'Not generating "{:s}"'.format( self._out )
            return
        tvars = dict()
        for key, value in self._engine.Defs.KeyValues( ) :
            if '.' not in key :
                self._MergeIn( tvars, key, value )
        for key, value in generator.SiteOptions.items( ) :
            self._MergeIn( tvars, 'Opts.'+key, value )
        for key, value in generator.LocalOptions.items( ) :
            print key, value
            self._MergeIn( tvars, 'Opts.'+key, value )
        for key, value in self._engine.Defs.KeyValues( ) :
            if '.' in key :
                self._MergeIn( tvars, 'Opts.'+key, value )
        m = self._num_regex.search( self._in )
        if m is not None :
            tvars['FileNum'] = int(m.group(1))
        if self._engine.Verbose :
            print 'Generating "{:s} from {:s}"'.format(self._out, self._in_full)
        if self._engine.Verbose > 2 :
            print "Using variables:"
            pprint.pprint( tvars )
        fp = open( self._out, 'w' )
        template = self._engine.Env.get_template( self._in )
        text = template.render( tvars )
        print >>fp, text
        fp.close( )

class IbModule_server_template( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    assert False, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
