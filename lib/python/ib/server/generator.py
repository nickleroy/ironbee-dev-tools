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

from ib.server.exceptions      import *
from ib.server.template        import *
from ib.server.template_engine import *
from ib.server.node            import *
from ib.server.site_options    import *

class IbServerBaseGenerator( IbServerSiteOptions ) :
    def __init__( self, defs, src, dest ) :
        IbServerSiteOptions.__init__( self, defs )
        self._engine = IbServerTemplateEngine( defs, src, dest )

    SourceRoot     = property( lambda self : self._engine.SourceRoot )
    DestRoot       = property( lambda self : self._engine.DestRoot )

    def PopulatePreDag( self, dag, root, main, srcdir, destdir ) :
        pass

    def PopulateMainDag( self, dag, root, main, srcdir, destdir ) :
        pass

    def PopulatePostDag( self, dag, root, main, srcdir, destdir ) :
        pass

    def RenderTemplate( self, template ) :
        template.Render( self )

    def _getSources( self, sources, inpath ) :
        if sources is None :
            return [inpath]
        else :
            return list(sources) + [inpath]
        return sources

    def AddTemplateNode( self, dag, infile, outfile,
                         name=None, dirname=None, sources=None, *args, **kwargs ) :
        inpath  = infile  if dirname is None else os.path.join(dirname, infile)
        outpath = outfile if dirname is None else os.path.join(dirname, outfile)
        templater = IbServerTemplate( self._engine, inpath, outpath )
        node = IbServerDagNodeTemplate( dag, infile,
                                        path=os.path.join(self.DestRoot, outpath),
                                        generator=self,
                                        template=templater,
                                        sources=self._getSources(sources, inpath),
                                        *args, **kwargs )
        return node

    def AddCopyNode( self, dag, infile, outfile,
                     name=None, dirname=None, sources=None, *args, **kwargs ) :
        inpath  = infile  if dirname is None else os.path.join(dirname, infile)
        infull  = os.path.join(self.SourceRoot, inpath)
        outpath = outfile if dirname is None else os.path.join(dirname, outfile)
        outfull = os.path.join(self.DestRoot, outpath)
        node = IbServerDagNodeCopy( dag, infile,
                                    generator=self,
                                    source=infull,
                                    dest=outfull,
                                    sources=self._getSources(sources, inpath),
                                    *args, **kwargs )
        return node

    def AddCopyDirNode( self, dag, dirname, *args, **kwargs ) :
        fullsrc = os.path.join(self.SourceRoot, dirname)
        node = IbServerDagNodeCopyDir( dag, dirname,
                                       generator=self,
                                       source=fullsrc,
                                       dest=os.path.join(self.DestRoot, dirname),
                                       *args, **kwargs )
        return node

    def AddDirNode( self, dag, dirname, *args, **kwargs ) :
        node = IbServerDagNodeDirectory( dag, dirname,
                                         generator=self,
                                         dirpath=os.path.join(self.DestRoot, dirname),
                                         *args, **kwargs )
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

    def _DefaultFileNodeFn( self, dag, dirname, fname, *args, **kwargs ) :
        if fname.endswith( '.in' ) :
            return self.AddTemplateNode( dag, fname, fname[:-3], dirname=dirname, *args, **kwargs )
        else :
            return self.AddCopyNode( dag, fname, fname, dirname=dirname, *args, **kwargs )

    def _DefaultFilter( self, name ) :
        if name.endswith( '~' ) or name in ( ('Makefile') ) :
            return False
        else :
            return True

    def AddDir( self, dag, dirname, parents=None, recurse=True,
                filt=None, file_node_fn=None, *args, **kwargs ) :
        """
        Add a directory, creating a node for each file, including one for the directory
        itself.
        Returns list of nodes.
        """
        if file_node_fn is None :
            file_node_fn = self._DefaultFileNodeFn
        if filt is None :
            filt = self._DefaultFilter

        dirnode = self.AddDirNode(dag, dirname, *args, **kwargs)
        if 'parents' in kwargs :
            kwargs['parents'].append(dirnode)

        srcdir = os.path.join( self.SourceRoot, dirname )
        for name in os.listdir( srcdir ) :
            fpath = os.path.join(srcdir, name)
            if filt is not None  and  not filt( name ) :
                continue
            if os.path.isdir( fpath ) :
                if not recurse :
                    continue
                children = [dirnode]
                if 'children' in kwargs :
                    kwargs = kwargs.copy()
                    children += kwargs['children']
                    del kwargs['children']
                node = self.AddDir( dag,
                                    os.path.join(dirname, name),
                                    recurse=True,
                                    children=children,
                                    filt=filt,
                                    file_node_fn=file_node_fn,
                                    *args, **kwargs)
            else :
                children = [dirnode]
                if 'children' in kwargs :
                    children += kwargs['children']
                    del kwargs['children']
                node = file_node_fn( dag, dirname, name, children=children, *args, **kwargs )

    def __getitem__( self, attr ) :
        if attr == 'Pre' :
            return self.PopulatePreDag
        elif attr == 'Main' :
            return self.PopulateMainDag
        elif attr == 'Post' :
            return self.PopulatePostDag
        else :
            raise KeyError('Unknown attribute "{:s}"'.format(attr))

def Instantiate( defs ) :
    return _IbGenerator( defs )

class IbModule_server_generator( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    assert False, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
