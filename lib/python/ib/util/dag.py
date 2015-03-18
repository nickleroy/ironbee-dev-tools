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
import time

class IbDagBaseException( BaseException ) : pass
class IbDagNoFile( IbDagBaseException ) : pass
class IbDagNoRecipe( IbDagBaseException ) : pass
class IbDagRecipeFailed( IbDagBaseException ) : pass
class IbDagLoopDetected( IbDagBaseException ) : pass

class _BaseDagObject( object ) :
    def __init__( self, name, path=None, recipe=None, parents=None, children=None, enabled=True ) :
        assert isinstance(name, str)
        assert recipe is None or callable(recipe)
        self._name     = name
        self._setPath( path )
        self._setRecipe( recipe )
        self._parents  = set( )
        self._children = set( )
        if parents is not None :
            self.AddParents( parents )
        if children is not None :
            self.AddChildren( children )
        self._setEnabled( enabled )
        self._setEvaluated( False )

    def _setRecipe( self, recipe ) :
        assert recipe is None or callable(recipe)
        self._recipe = recipe
    def _setPath( self, path ) :
        assert path is None or type(path) == str
        self._path = path
    def _setEnabled( self, enabled ) :
        assert type(enabled) == bool
        self._enabled = enabled
    def _setEvaluated( self, evaluated ) :
        assert type(evaluated) == bool
        self._evaluated = evaluated
    def _setDirty( self, dirty ) :
        self._setEvaluated( not dirty )

    def AddParents( self, parents ) :
        assert isinstance(parents, (set,frozenset,tuple,list))
        self._CheckList( parents )
        if any ( [parent in self._children for parent in parents] ) :
            raise IbDagLoopDetected
        self._parents.update( set(parents) )
        for parent in parents :
            parent.AddChildren( [self] )

    def AddChildren( self, children ) :
        assert isinstance(children,  (set,frozenset,tuple,list))
        self._CheckList( children )
        if any ( [child in self._parents for child in children] ) :
            raise IbDagLoopDetected
        self._children.update( set(children) )

    Name      = property( lambda self : self._name )
    Path      = property( lambda self : self._path, _setPath )
    Recipe    = property( lambda self : self._recipe, _setRecipe )
    Enabled   = property( lambda self : self._enabled, _setEnabled )
    Parents   = property( lambda self : set(self._parents) )
    Children  = property( lambda self : set(self._children) )
    Dirty     = property( lambda self : not self._evaluated, _setDirty )
    Evaluated = property( lambda self : self._evaluated, _setEvaluated )


class IbDagNode( _BaseDagObject ) :
    _path_mtime_cache = { }
    _ib_module_paths = None
    @classmethod
    def _InitClass( cls ) :
        if cls._ib_module_paths is not None :
            return
        cls._ib_module_paths = []
        regex = re.compile( r'IbModule_\w+?_\w+$' )
        for name,klass in globals().items() :
            if regex.match(name) :
                cls._ib_module_paths.append( klass.modulePath )

    def __init__( self, dag, name, path=None, sources=None, is_stale=False, recipe=None,
                  parents=None, children=None,
                  always=False, auto_add_modules=False, is_default_target=False ) :
        self._InitClass( )
        _BaseDagObject.__init__( self, name, path, recipe, parents, children )

        assert isinstance(dag, IbDag)
        assert isinstance(always, bool)
        self._dag      = dag
        self._sources  = set( )
        self._always   = always
        if sources is not None :
            self.AddSources( sources )
        self.Reset( )
        self.IsStale   = is_stale
        self._dag.AddNode( self, is_default_target=is_default_target )
        if auto_add_modules :
            self._AddModuleSources( )
            

    def _AddModuleSources( self ) :
        self.AddSources( self._ib_module_paths )

    def Reset( self ) :
        self._mtime    = None
        self._is_stale = None
        self.Evaluated = False
        self._executed = False

    def AddSources( self, sources ) :
        if isinstance( sources, str ) :
            sources = [sources]
        else :
            assert isinstance(sources, (set,frozenset,tuple,list))
            assert all( [isinstance(source, str) for source in sources] )
        self._sources.update( sources )

    def GetFullPath( self, path=None ) :
        if path is not None :
            return self._dag.GetFullPath( path ) 
        elif self._path is not None :
            return self._dag.GetFullPath( self._path ) 
        else :
            return None

    def _setIsStale( self, tf ) :
        assert type(tf) == bool
        self._isstale = tf
    def _setAlways( self, tf ) :
        assert type(tf) == bool
        self._always = tf

    def GetModTime( self, path ) :
        full = self.GetFullPath( path )
        mtime = self._path_mtime_cache.get( full )
        if mtime is not None :
            return mtime
        try :
            mtime = os.path.getmtime( full )
            self._path_mtime_cache[full] = mtime
            return mtime
        except OSError :
            raise IbDagNoFile( full )

    def GetModTimes( self, paths, ignore_missing ) :
        if type(paths) == str :
            paths = [paths]
        elif len(paths) == 0 :
            return [ 0.0 ]
        mtimes = []
        for path in paths :
            try :
                mtimes.append( self.GetModTime(path) )
            except IbDagNoFile :
                if ignore_missing : continue
                raise
        if len(mtimes) == 0 :
            return [0.0]
        else :
            return mtimes

    def NewestSources( self, sources=None ) :
        if sources is None :
            sources = self._sources
            
        mtimes = self.GetModTimes( [self.GetFullPath(src) for src in sources], False )
        maxtime = max( mtimes )
        return maxtime

    def EvaluateChildren( self ) :
        stales = []
        mtimes = [0.0]
        for node in self._children :
            stale,mtime = node.Evaluate( self )
            stales.append(stale)
            mtimes.append(mtime)
        maxtime = max(mtimes)
        return any(stales), maxtime

    def Evaluate( self, parent=None ) :
        if not self.Enabled :
            return False, 0.0
        if self.Evaluated  and  not self.Always :
            return self.IsStale, self.ModTime

        stale,maxtime = self.EvaluateChildren( )
        try :
            if self.Always :
                stale = True
            elif self.Path is None :
                self._mtime = 0.0
            else :
                self._mtime = None
        except IbDagNoFile :
            self._mtime = None
            stale = True

        try :
            maxsource = self.NewestSources( )
        except IbDagNoFile as e :
            msg = 'Souce file "{:s}" is missing for node "{}" of DAG "{}"' \
                .format(str(e), self.Name, self._dag.Name)
            raise IbDagNoFile( msg )

        if self.Path is None  or  stale  or  self._mtime is None :
            self._is_stale = True
        elif not self._is_stale :
            if maxtime > self._mtime  or  maxsource > self._mtime :
                self._is_stale = True
            elif self._is_stale is None :
                self._is_stale = False
        self.Dirty = False
        self._executed  = False
        return self.IsStale, self.ModTime

    def Execute( self, recipe=None, debug=0, debug_fp=sys.stdout, *args, **kwargs ) :
        if not self.Enabled or self._executed :
            if debug > 2 :
                if not self.Enabled :
                    print >>debug_fp, 'Not executing disabled node "{}" of DAG "{}"' \
                        .format(self.Name, self.Dag.Name)
                elif self._executed :
                    print >>debug_fp, 'Not executing executed node "{}" of DAG "{}"' \
                        .format(self.Name, self.Dag.Name)
            return

        for child in self._children :
            child.Execute( self, debug=debug, debug_fp=debug_fp, *args, **kwargs )

        _recipe = None
        if self.Recipe is not None :
            _recipe = self.Recipe
        elif recipe is not None :
            _recipe = recipe
        elif self.Dag.Recipe is not None :
            _recipe = self.Dag.Recipe
        else :
            raise IbDagNoRecipe( self.Name )

        assert callable(_recipe), (_recipe, type(_recipe))
        if debug > 1 :
            print >>debug_fp, 'Executing node "{}" of DAG "{}"'.format(self.Name, self.Dag.Name)
        status,text = _recipe( self, *args, **kwargs )
        if debug > 1 or status != 0 or text is not None :
            print >>debug_fp, 'Node "{}" status {} "{}"'.format(self.Name, status, text)
        self._executed = True
        if status :
            if text is None :
                text = 'Node "{:s}" recipe failed with status {:d}'.format(self.Name, status)
            raise IbDagRecipeFailed( text )

    def __str__( self ) :
        s = 'Node "{}": path="{}" full="{}" mtime={} stale={} evaluated={}' \
            .format( self.Name, self.Path, self.FullPath, self.ModTime, str(self.IsStale),
                     str(self.Evaluated) )
        return s

    def Print( self, debug_fp=sys.stdout ) :
        print self
        if len(self.Children) :
            print >>debug_fp, "  Children:"
            print >>debug_fp, "    ", sorted( [node.Name for node in self.Children] )
        if len(self.Parents) :
            print >>debug_fp, "  Parents:"
            print >>debug_fp, "    ", sorted( [node.Name for node in self.Parents] )
        if len(self.Sources) :
            print >>debug_fp, "  Sources:"
            for source in self.Sources :
                try :
                    print >>debug_fp, "    {:s} {:s} {:s}" \
                        .format( source, self.GetFullPath(source),
                                 time.asctime(time.localtime(self.GetModTime(source))) )
                except IbDagNoFile :
                    print >>debug_fp, "    {:s} {:s}".format(source, self.GetFullPath(source) )

    @staticmethod
    def _CheckList( objects ) :
        assert all( [isinstance(node, IbDagNode) for node in objects] )

    Dag      = property( lambda self : self._dag )
    IsStale  = property( lambda self : self._is_stale, _setIsStale )
    ModTime  = property( lambda self : self._mtime )
    Sources  = property( lambda self : tuple(self._sources) )
    FullPath = property( lambda self : self.GetFullPath() )
    Recipe   = property( lambda self : self._recipe )
    IsPhony  = property( lambda self : self._path is None )
    Always   = property( lambda self : self._always, _setAlways )


class IbDag( _BaseDagObject ) :
    def __init__( self, name, rootdir=None, recipe=None,
                  targets=None, parents=None, children=None,
                  enabled=True, auto_add_modules=False ) :
        _BaseDagObject.__init__( self, name, rootdir, recipe, parents, children, enabled )
        assert targets is None or type(targets) in (list,tuple)
        self._nodes = [ ]
        self._names = { }
        self._paths = { }
        self._targets = set( )
        if targets is not None :
            self.AddTargets( targets )
        self._path_full_cache = { }
        self._auto_add_modules = auto_add_modules

    Targets = property( lambda self : self._targets )
    Nodes   = property( lambda self : self._nodes )

    def AddNode( self, node, is_default_target=False ) :
        assert isinstance(node, IbDagNode)
        try :
            assert node not in self._nodes, 'Duplicate node found "{}"'.format(node.name)
            assert node.Name not in self._names, 'Duplicate node name "{}"'.format(node.Name)
        except AssertionError :
            print "Nodes:", [node.Name for node in self._nodes]
            print "Names:", self._names.keys()
            raise
        self._nodes.append( node )
        self._names[node.Name] = node

        if node.Path not in self._paths :
            self._paths[node.Path] = []
        self._paths[node.Path].append( node )
        if self._auto_add_modules :
            node._AddModuleSources( )
        if is_default_target :
            self._targets.add( node )
        self._setDirty( True )

    def AddSingleTarget( self, target ) :
        self.AddTargetList( [target] )
        self._setDirty( True )

    def AddTargetList( self, targets ) :
        tset = self._getTargetSet( targets )
        self._targets.update( tset )
        self._setDirty( True )

    def _CheckList( self, objects ) :
        assert all( [isinstance(node, IbDag) for node in objects] )

    def GetFullPath( self, path ) :
        if path is None :
            return None
        full = self._path_full_cache.get( path )
        if full is not None :
            return full
        elif os.path.isabs( path ) :
            full = path
        elif self.Path is not None :
            full = os.path.join( self.Path, path )
        else :
            full = path
        self._path_full_cache[path] = full
        return full

    def GetPathNodes( self, path ) :
        return list(self._paths.get(path, []))

    def FindNode( self, name ) :
        if type(name) == str :
            return self._names.get( name )
        elif isinstance(name, IbDagNode) :
            return name
        else :
            assert False, "Invalid object passed to FindNode({:s})".format(str(type(name)))

    def _getTargetSet( self, targets, self_targets=False ) :
        if targets is not None :
            assert all( [isinstance(node, (str,IbDagNode)) for node in targets] )
            tmp = [ self.FindNode(target) for target in targets ]
            assert all( [node in self._nodes for node in targets] )
            return set(targets)
        elif self_targets and len(self._targets) :
            return set(self._targets)
        else :
            return set(self._nodes)

    def Evaluate( self, targets=None ) :
        if not self.Enabled  or  self.Evaluated :
            return
        targets = self._getTargetSet( targets, True )
        for dag in self.Children :
            dag.Evaluate( )
        for target in targets :
            target.Evaluate( )
        self.Evaluated = True

    def Execute( self, targets=None, recipe=None, debug=0, debug_fp=sys.stdout, *args, **kwargs ) :
        if not self.Enabled :
            return
        assert recipe is None or callable(recipe)

        if debug :
            print >>debug_fp, 'Executing DAG "{:s}"'.format(self.Name)
        if not self.Evaluated :
            self.Evaluate( targets )

        if len(self._children) :
            if debug and len(self._children):
                print >>debug_fp, 'Executing child DAGs of DAG "{:s}"'.format(self.Name)
            for dag in tuple(self._children) :
                dag.Execute( targets, recipe, debug, debug_fp, *args, **kwargs )

        targets = self._getTargetSet( targets, True )
        if len(targets) :
            if debug > 1:
                print >>debug_fp, 'Executing targets of DAG "{:s}"'.format(self.Name)
            for target in tuple(targets) :
                target.Execute( recipe, debug, debug_fp, *args, **kwargs )
        if debug :
            print >>debug_fp, 'DAG "{:s}" excution done'.format(self.Name)


class IbModule_util_dag( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    import shutil
    dag = IbDag('test')
    root = '/tmp/dagtest'
    shutil.rmtree( root )
    os.makedirs( root )
    for name in ( 'file1', 'file2', 'node3' ) :
        with open( os.path.join(root, name), 'w') as fp :
            print >>fp, name
    def touch( node ) :
        with open( node.Path, 'w') as fp :
            print >>fp, node.Name
            for source in node.Sources :
                print >>fp, "Source:", source
        return 0, None
    node1 = IbDagNode(dag, 'node1', os.path.join(root,'node1') )
    node2 = IbDagNode(dag, 'node2', os.path.join(root, 'node2'),
                      sources=[os.path.join(root,'file1'),
                               os.path.join(root,'file2'),
                               '/etc/passwd'],
                      parents=[node1])
    node3 = IbDagNode(dag, 'node3', os.path.join(root,'node3'),
                      sources=['/etc/passwd'],
                      parents=[node1])
    node4 = IbDagNode(dag, 'node4', os.path.join(root,'node4'),
                      sources=['/etc/passwd'],
                      parents=[node2])
    dag.Evaluate( )
    dag.Execute( recipe=touch )

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
