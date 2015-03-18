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
from ib.util.dag import *
import collections

class IbServerDags( object ) :
    def __init__( self ) :
        self._dags = collections.OrderedDict()

    def _AddDag( self, name, *args, **kwargs ) :
        dag = IbDag( name, *args, **kwargs )
        self._dags[name] = dag
        return dag

    def _CreateDag( self, name, parent, *args, **kwargs ) :
        dag = IbDag( name, parents=[parent], *args, **kwargs )
        return dag

    def _SetupWipe( self, dag ) :
        self.PopulateWipeIronbee( self._CreateDag('WipeIronBee', dag) )
        self.PopulateWipeServer( self._CreateDag('WipeServer', dag) )
        return dag

    def _SetupPre( self, dag ) :
        self.PopulatePreIronbee( self._CreateDag('PreIronBee', dag) )
        self.PopulatePreServer( self._CreateDag('PreServer', dag) )
        return dag

    def _SetupMain( self, dag ) :
        self.PopulateMainIronbee( self._CreateDag('MainIronBee', dag) )
        self.PopulateMainServer( self._CreateDag('MainServer', dag) )
        return dag

    def _SetupPost( self, dag ) :
        self.PopulatePostIronbee( self._CreateDag('PostIronBee', dag) )
        self.PopulatePostServer( self._CreateDag('PostServer', dag) )
        return dag

    def SetupDags( self ) :
        self._SetupWipe( self._AddDag('Wipe', enabled=True) )
        self._SetupPre( self._AddDag('Pre', enabled=True) )
        self._SetupMain( self._AddDag('Main', enabled=True) )
        self._SetupPost( self._AddDag('Post', enabled=True) )

    def GetDag( self, name ) :
        return self._dags.get(name)

    def Evaluate( self, *args, **kwargs ) :
        for dag in self._dags.values() :
            dag.Evaluate( *args, **kwargs )

    def Execute( self, *args, **kwargs ) :
        for dag in self._dags.values() :
            dag.Execute( *args, **kwargs )

    def Dump( self, debug=0, debug_fp=sys.stdout ) :
        for name,dag in self._dags.items() :
            print >>debug_fp, 'DAG', name
            print >>debug_fp, '  Parents:', sorted( [p.Name for p in dag._parents] )
            print >>debug_fp, '  Children:', sorted( [c.Name for c in dag._children] )
            if len(dag.Nodes) :
                print >>debug_fp, '  Nodes:', sorted( [node.Name for node in dag.Nodes] )
            for node in dag.Nodes :
                print >>debug_fp, '    Node {}: parents={} children={}'.format(
                    node.Name,
                    sorted( [p.Name for p in node.Parents] ),
                    sorted( [c.Name for c in node.Children] )
                )
            if len(dag.Targets) :
                print >>debug_fp, '  Targets:', sorted( [target.Name for target in dag.Targets] )



class IbModule_server_dag( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    assert False, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
