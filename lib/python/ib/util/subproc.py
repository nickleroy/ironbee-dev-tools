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
import time

def SubProcFormatCmd( cmd, cwd=None, mult_lines=False, spaces=2 ) :
    fdir = '' if cwd is None else ' in "{}"'.format(cwd)
    if mult_lines :
        joiner = "'\n"+' '*spaces+"'"
        return "\n'"+joiner.join(cmd)+"'"+'\n'+' '*spaces+fdir
    else :
        return "'"+"' '".join(cmd)+"'"+' '+fdir


### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
