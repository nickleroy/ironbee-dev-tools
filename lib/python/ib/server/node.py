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
import dagger.dagger
from ib.server.template  import *

class IbServerDagNodeBase( dagger.node ) :
    def __init__( self, name, generator, *args, **kwargs ) :
        dagger.node.__init__( self, name, *args, **kwargs )
        self._generator = generator

class IbServerDagNodeExe( IbServerDagNodeBase ) :
    def __init__( self, name, generator, cmd, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, name, generator, *args, **kwargs )
        self._cmd = cmd

    def run( self ) :
        pass

class IbServerDagNodeTemplate( IbServerDagNodeBase ) :
    def __init__( self, name, generator, template, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, name, generator, *args, **kwargs )
        assert isinstance(template, IbServerTemplate)
        self._template = template

    def run( self, *args, **kwargs ) :
        self._generator.RenderTemplate( self._template )

class IbServerDagNodeDirectory( IbServerDagNodeBase ) :
    def __init__( self, name, generator, dirpath, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, name, generator, *args, **kwargs )
        self._dirpath = dirpath

    def run( self ) :
        self._generator.CreateDir( self._dirpath )

class IbServerDagNodeCopy( IbServerDagNodeBase ) :
    def __init__( self, name, generator, source, dest, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, name, generator, *args, **kwargs )
        self._source = source
        self._dest   = dest

    def run( self ) :
        self._generator.CopyFile( self._source, self._dest )

class IbServerDagNodeCopyDir( IbServerDagNodeBase ) :
    def __init__( self, name, generator, source, dest, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, name, generator, *args, **kwargs )
        self._source = source
        self._dest   = dest

    def run( self ) :
        self._generator.CopyDir( self._source, self._dest )

if __name__ == "__main__" :
    assert 0, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
