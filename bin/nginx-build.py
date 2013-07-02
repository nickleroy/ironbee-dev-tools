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
import sys
import subprocess

# Find the source, etc.
pkgname = os.path.basename(os.getcwd())
src_dir = os.path.join(os.environ['IB_ROOT'], 'servers/nginx')
install = os.path.join(os.environ['QYLS_BUILD'], 'gcc/install')
os.environ['NGINXIB_CONFIG_FILE'] = os.path.join(src_dir, 'config.nginx')
lib_dir = os.path.join(install, 'lib64')

ldpath = os.environ.get('LD_LIBRARY_PATH')
if ldpath is None  or  ldpath == '' :
    ldpath = lib_dir
else :
    ldpath = ldpath+':'+lib_dir
os.environ['LD_LIBRARY_PATH'] = ldpath

# Do we need to patch?
cmd = ('grep', '-q', 'ngx_regex_malloc_init', 'src/core/ngx_regex.h')
status = subprocess.call( cmd )
if status == 1 :
    cmd = ('patch', '-p', '0', '-i', os.path.join(src_dir,'nginx.patch') )
    print "Patching source..."
    subprocess.call( cmd )

cmd = ( './configure',
        '--add-module='+src_dir,
        '--with-cc-opt=-I'+os.path.join(install,'include'),
        '--with-ld-opt=-L'+lib_dir+' -lhtp -libutil -lironbee',
        '--prefix='+os.path.join(os.environ['EXT_INSTALL'], pkgname) )
print "Configuring via", cmd
subprocess.call( cmd )

