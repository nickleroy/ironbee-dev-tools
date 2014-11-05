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
import re
import shutil

from ib.server.exceptions import *
from ib.server.template   import *
from ib.server.node       import *

class IbServerBaseGenerator( object ) :
    def __init__( self, defs, src, dest ) :
        self._CheckOptions( )
        self._defs = defs
        self._engine = IbServerTemplateEngine( defs, src, dest )
        self._modes = []
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

    SourceRoot     = property( lambda self : self._engine.SourceRoot )
    DestRoot       = property( lambda self : self._engine.DestRoot )
    Verbose        = property( lambda self : self._defs['Verbose'] )
    Execute        = property( lambda self : self._defs['Execute'] )
    Quiet          = property( lambda self : self._defs['Quiet'] )
    Wipe           = property( lambda self : self._defs['Wipe'] )
    LocalOptions   = property( lambda self : self._local_options )
    SiteOptions    = property( lambda self : self._site_options )

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
        if self._sites is None :
            return
        if 'Sites' not in self._defs :
            self._defs['Sites'] = { }
        for site in sites :
            if site not in self._sites :
                raise IbServerUnknownSite(site)
            self._defs['Sites'][site] = True
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

    def PopulatePreDag( self, dag, root, main, srcdir, destdir ) :
        pass

    def PopulateMainDag( self, dag, root, main, srcdir, destdir ) :
        pass

    def PopulatePostDag( self, dag, root, main, srcdir, destdir ) :
        pass

    def RenderTemplate( self, template ) :
        template.Render( self )

    def AddTemplateNode( self, dag, dirname, infile, outfile, deps=None ) :
        if deps is None : deps = []
        inpath  = infile  if dirname is None else os.path.join(dirname, infile)
        outpath = outfile if dirname is None else os.path.join(dirname, outfile)
        templater = IbServerTemplate( self._engine, inpath, outpath )
        node = IbServerDagNodeTemplate( os.path.join(self.DestRoot, outpath), self, templater )
        dag.add( node, deps )
        return node

    def AddCopyNode( self, dag, dirname, infile, outfile, deps=None ) :
        if deps is None : deps = []
        inpath  = infile  if dirname is None else os.path.join(dirname, infile)
        outpath = outfile if dirname is None else os.path.join(dirname, outfile)
        node = IbServerDagNodeCopy( outfile, self,
                                    os.path.join(self.SourceRoot, inpath),
                                    os.path.join(self.DestRoot, outpath) )
        dag.add( node, deps )
        return node

    def AddCopyDirNode( self, dag, dirname, deps=None ) :
        if deps is None : deps = []
        node = IbServerDagNodeCopyDir( dirname, self,
                                       os.path.join(self.SourceRoot, dirname),
                                       os.path.join(self.DestRoot, dirname) )
        dag.add( node, deps )
        return node

    def AddDirNode( self, dag, dirname, deps=None ) :
        if deps is None : deps = []
        node = IbServerDagNodeDirectory( dirname,
                                         self,
                                         os.path.join(self.DestRoot, dirname) )
        dag.add( node, deps )
        return node

    def CreateDir( self, path ) :
        if not self.Execute  or  os.path.isdir( path ) :
            return
        elif os.path.exists( path ) :
            raise IbServerNodeError( '"{:s}" exists and is not a directory'.format(path) )
        try :
            os.makedirs( path )
        except OSError as e :
            raise IbServerNodeError(
                'Failed to create directory "{:s}": {:s}'.format(path, str(e))
            )

    def CopyFile( self, source, dest ) :
        if not self.Execute :
            return
        try :
            shutil.copy( source, dest )
        except OSError as e :
            raise IbServerNodeError(
                'Failed to copy "{:s}" to "{:s}: {:s}'.format(source, dest, str(e))
            )

    def CopyDir( self, source, dest ) :
        if not self.Execute  or  os.path.isdir( dest ):
            return
        try :
            shutil.copytree( source, dest )
        except OSError as e :
            raise IbServerNodeError(
                'Failed to copy "{:s}" to "{:s}: {:s}'.format(source, dest, str(e))
            )

    def _DefaultFileNodeFn( self, dag, dirname, fname, deps=None ) :
        if deps is None : deps = []
        if fname.endswith( '.in' ) :
            return self.AddTemplateNode( dag, dirname, fname, fname[:-3], deps )
        else :
            return self.AddCopyNode( dag, dirname, fname, fname, deps )

    def _DefaultFilter( self, name ) :
        if name.endswith( '~' ) or name in ( ('Makefile') ) :
            return False
        else :
            return True

    def AddDir( self, dag, dirname, deps=None, recurse=True,
                filt=None, file_node_fn=None ) :
        """
        Add a directory, creating a node for each file, including one for the directory
        itself.
        Returns list of nodes.
        """
        if file_node_fn is None :
            file_node_fn = self._DefaultFileNodeFn
        if filt is None :
            filt = self._DefaultFilter
        if deps is None :
            deps = []

        dirnode = self.AddDirNode(dag, dirname)
        phony = dag.add( dirname+'-phony', [dirnode], phony=True )

        srcdir = os.path.join( self.SourceRoot, dirname )
        for name in os.listdir( srcdir ) :
            fpath = os.path.join(srcdir, name)
            if filt is not None  and  not filt( name ) :
                continue
            if os.path.isdir( fpath ) :
                if not recurse :
                    continue
                nodes = self.AddDir( dag,
                                     os.path.join(dirname, name),
                                     deps,
                                     recurse=True,
                                     filt=filt,
                                     file_node_fn=file_node_fn )
                for node in nodes :
                    node.add( dirnode )
            else :
                node = file_node_fn( dag, dirname, name )
                if node is not None :
                    node.add( dirnode )
                    node.add( phony )

        return [phony]

    def __getitem__( self, attr ) :
        if attr == 'Pre' :
            return self.PopulatePreDag
        elif attr == 'Main' :
            return self.PopulateMainDag
        elif attr == 'Post' :
            return self.PopulatePostDag
        else :
            assert False, 'Unknown attribute "{:s}"'.format( attr )

def Instantiate( defs ) :
    return _IbGenerator( defs )

if __name__ == "__main__" :
    assert 0, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
