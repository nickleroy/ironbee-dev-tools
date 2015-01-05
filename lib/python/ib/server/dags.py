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

class IbServerDags( object ) :
    def __init__( self, main ) :
        self._dags = { main.Name : main }
        self._maindag = main

    def _CreateDag( self, name, parent, *args, **kwargs ) :
        dag = IbDag( name, parents=[parent], *args, **kwargs )
        self._dags[name] = dag
        return dag

    def _WipeDone( self, node ) :
        for dag in self._dags.values( ) :
            if self._maindag in dag.Parents :
                dag.Enabled = (dag != node.Dag)
        return 0, None

    def _SetupWipe( self, after ) :
        dag = self._CreateDag( 'Wipe', self._maindag, enabled=True, execute_after_dags=after )
        self.PopulateWipeIronbee( self._CreateDag('WipeIronBee', dag) )
        self.PopulateWipeServer( self._CreateDag('WipeServer', dag) )
        wipe_node = IbDagNode( dag, 'WipeDone', recipe=self._WipeDone, always=True )
        return dag

    def _SetupPre( self, after ) :
        dag = self._CreateDag( 'Pre', self._maindag, enabled=False, execute_after_dags=after )
        self.PopulatePreIronbee( self._CreateDag('PreIronBee', dag) )
        self.PopulatePreServer( self._CreateDag('PreServer', dag) )
        return dag

    def _SetupMain( self, after ) :
        dag = self._CreateDag( 'Main', self._maindag, enabled=False, execute_after_dags=after )
        self.PopulateMainIronbee( self._CreateDag('MainIronBee', dag) )
        self.PopulateMainServer( self._CreateDag('MainServer', dag) )
        return dag

    def _SetupPost( self, after ) :
        dag = self._CreateDag( 'Post', self._maindag, enabled=False, execute_after_dags=after )
        self.PopulatePostIronbee( self._CreateDag('PostIronBee', dag) )
        self.PopulatePostServer( self._CreateDag('PostServer', dag) )
        return dag

    def SetupDags( self ) :
        dag = self._SetupWipe( None )
        dag = self._SetupPre( [dag] )
        dag = self._SetupMain( [dag] )
        dag = self._SetupPost( [dag] )

    def GetDag( self, name ) :
        return self._dags.get(name)

    def Evaluate( self, *args, **kwargs ) :
        self._maindag.Evaluate( *args, **kwargs )

    def Execute( self, *args, **kwargs ) :
        self._maindag.Execute( *args, **kwargs )

    def Dump( self, verbose=0 ) :
        for name,dag in self._dags.items() :
            print "DAG", name
            if len(dag.Nodes) : print "Nodes:", [node.Name for node in dag.Nodes]
            if len(dag.Targets) : print "Targets:", [target.Name for target in dag.Targets]



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
