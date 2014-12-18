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
from ib.util.dag            import *
from ib.server.template     import *
from ib.server.site_options import *

class IbServerDagNodeBase( IbDagNode ) :
    def __init__( self, dag, name, generator, *args, **kwargs ) :
        IbDagNode.__init__( self, dag, name, recipe=self.Run, *args, **kwargs )
        assert isinstance(generator, IbServerSiteOptions)
        self._generator = generator

class IbServerDagNodeExe( IbServerDagNodeBase ) :
    def __init__( self, dag, name, generator, cmd, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, dag, name, generator, *args, **kwargs )
        self._cmd = cmd

    def Run( self, node ) :
        return 0, None

class IbServerDagNodeTemplate( IbServerDagNodeBase ) :
    def __init__( self, dag, name, generator, template, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, dag, name, generator, *args, **kwargs )
        assert isinstance(template, IbServerTemplate)
        self._template = template

    def Run( self, node, *args, **kwargs ) :
        self._generator.RenderTemplate( self._template )
        return 0, None

class IbServerDagNodeDirectory( IbServerDagNodeBase ) :
    def __init__( self, dag, name, generator, dirpath, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, dag, name, generator, path=dirpath, *args, **kwargs )
        assert type(dirpath) == str
        self._dirpath = dirpath

    def Run( self, node ) :
        self._generator.CreateDir( self._dirpath )
        return 0, None

class IbServerDagNodeCopy( IbServerDagNodeBase ) :
    def __init__( self, dag, name, generator, source, dest, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, dag, name, generator, path=source, *args, **kwargs )
        assert type(source) == str, 'Type of source is {}, should be str'.format( type(source) )
        assert type(dest) == str, 'Type of dest is {}, should be str'.format( type(dest) )
        self._source = source
        self._dest   = dest

    def Run( self, node ) :
        self._generator.CopyFile( self._source, self._dest )
        return 0, None

class IbServerDagNodeCopyDir( IbServerDagNodeBase ) :
    def __init__( self, dag, name, generator, source, dest, *args, **kwargs ) : 
        IbServerDagNodeBase.__init__( self, dag, name, generator, *args, **kwargs )
        assert type(source) == str, 'Type of source is {}, should be str'.format( type(source) )
        assert type(dest) == str, 'Type of dest is {}, should be str'.format( type(dest) )
        self._source = source
        self._dest   = dest

    def Run( self, node ) :
        self._generator.CopyDir( self._source, self._dest )
        return 0, None

class IbModule_server_node( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    assert False, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
