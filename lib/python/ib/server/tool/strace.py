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
from ib.server.tool.base import *

class IbToolStrace( IbToolBase ) :
    _strace_prefix = ("${ToolName}",
                      "-o", "${ToolOut}")
    def __init__( self, name ) :
        IbToolBase.__init__( self, name, prefix=self._strace_prefix )

Tools = \
{
    "strace" : IbToolStrace( "strace" ),
}

if __name__ == "__main__" :
    assert 0, "not stand-alone"
