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
from ib.tool.base     import *

class IbToolValgrind( IbToolBase ) :
    _valgrind_prefix = ( "valgrind",
                         "--tool=${SubTool}",
                         "--log-file=${ToolOut}")

    def __init__( self, name, defs, args=None ) :
        IbToolBase.__init__( self, name, prefix=self._valgrind_prefix, tool_args=args, defs=defs )

    def Prefix( self ) :
        prefix = list(self._prefix) + [ "-v" for i in range(self._verbose) ]
        return prefix

Tools = \
{
    "valgrind" : IbToolValgrind("valgrind",
                                args=("--leak-check=full",
                                      "--track-origins=yes",
                                      "--track-fds=yes",
                                      "--freelist-vol=200000000",
                                      "--fair-sched=no"),
                                defs={"SubTool":"memcheck"}),
    "helgrind" : IbToolValgrind("helgrind",
                                defs={"SubTool":"helgrind"}),
    "drd" : IbToolValgrind("drd",
                           defs={"SubTool":"drd"}),
}

if __name__ == "__main__" :
    assert 0, "not stand-alone"
