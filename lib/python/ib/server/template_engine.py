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
import sys
import os
import re
import jinja2
import jinja2.ext

from ib.util.version import *
from ib.server.exceptions import *

class FileLineExtension( jinja2.ext.Extension ) :
    r""" Adds a filename, basename and lineno tags to Jinja. """

    tags = set(['filename', 'basename', 'lineno'])

    def parse(self, parser):
        token = next(parser.stream)
        if token.value == 'filename' :
            node = jinja2.nodes.Const(parser.filename)
        elif token.value == 'basename' :
            node = jinja2.nodes.Const(os.path.basename(parser.filename))
        elif token.value == 'lineno' :
            node = jinja2.nodes.Const(str(token.lineno))
        else :
            assert False, 'Unknown token "{:s}"'.format(token.value)
        return node

class RuleIdExtension( jinja2.ext.Extension ) :
    r""" Adds a {% baseid %}, {% ruleid %}, and {% pruleid %} tags to Jinja. """

    tags = set(['baseid', 'ruleid', 'pruleid'])

    _ruleid = ''
    _regex = re.compile( r'\..+' )
    def parse(self, parser):
        token = next(parser.stream)
        if token.value == 'pruleid' :
            return jinja2.nodes.Const(self._ruleid)
        baseid = self._regex.sub('', os.path.basename(parser.filename))
        if token.value == 'ruleid' :
            ruleid = '{:s}/{:03d}'.format(baseid, token.lineno)
            parser.environment.globals['RuleId'] = ruleid
            self._ruleid = ruleid
            node = jinja2.nodes.Const(ruleid)
        elif token.value == 'baseid' :
            parser.environment.globals['BaseId'] = baseid
            node = jinja2.nodes.Const(baseid)
        else :
            assert False, 'Unknown token "{:s}"'.format(token.value)
        return node

class IbVersionExtension( jinja2.ext.Extension ) :
    r""" Adds a {% ibvercmp(op,value) %} tag to Jinja. """

    tags = set(['ibversion'])

    def parse(self, parser):
        token = next(parser.stream)
        args = parser.parse_expression()
        print 'Token is "{:s}"'.format(token)
        print 'Args:', type(args), args
        print 'args.expr:', type(args.expr), args.expr
        print 'args.ops:', type(args.ops), args.ops
        for n,op in enumerate(args.ops) :
            print n, type(op), op
        node = jinja2.nodes.Const(True)
        return node

class _RelativeEnvironment(jinja2.Environment):
    """Override join_path() to enable relative template paths."""
    def join_path(self, template, parent):
        searchpath = self.loader.searchpath + [os.path.dirname(parent)]
        for root in searchpath :
            full = os.path.join(root, template)
            if os.path.exists(full) :
                prefix = os.path.commonprefix([full, root])
                path = full.replace(prefix+'/', '')
                return path
        return

class IbServerTemplateEngine( object ) :
    def __init__( self, defs, src_root, dst_root ) :
        assert src_root != dst_root, 'src_root="{}" == dst_root="{}"'.format(src_root, dst_root)
        paths = [ src_root ]
        self._defs = defs
        self._src_root = src_root
        self._dst_root = dst_root
        self._loader = jinja2.FileSystemLoader( searchpath=paths )
        self._env = _RelativeEnvironment(loader=self._loader,
                                         lstrip_blocks=True,
                                         extensions=[FileLineExtension,
                                                     RuleIdExtension])
        self._env.filters['ibversion'] = self._IbVersionFilter
        self._env.filters['Map'] = self._IbMapFilter
        self._env.filters['Size'] = self._SizeFilter
        self._env.tests['rule_enable'] = self._IsRuleEnable

    def _IsRuleEnable( self, name ) :
        return self._defs.Get( name, False )

    @jinja2.environmentfilter
    def _IbMapFilter(self, env, name, _map, value) :
        if value in _map :
            return _map[value]
        elif value in _map.values():
            return value
        else :
            assert False, 'Invalid {:s} identifier "{:s}"'.format(name, str(value))

    @jinja2.contextfilter
    def _IbVersionFilter(self, context, value) :
        if value == "" :
            return self._ib_version
        else :
            return IbVersion( value )

    def SetIbVersion( self, ib_version ) :
        self._ib_version = ib_version

    __mults = { 'k':1024, 'K':1000,
                'm':1024*1024, 'M':1000*1000,
                'g':1024*1024*1024, 'G':1000*1000*1000, }
    __keys = tuple(__mults.keys())
    @jinja2.contextfilter
    def _SizeFilter(self, context, value) :
        mult = 1
        if value.endswith( self.__keys ) :
            mult = self.__mults[value[-1]]
            value = value[:-1]
        try :
            return int(value) * mult
        except ValueError :
            assert False, 'Invalid size "{:s}"'.format(str(value))

    IronBeeVersion = property( lambda self : self._ib_version )
    Defs       = property( lambda self : self._defs )
    Env        = property( lambda self : self._env )
    SourceRoot = property( lambda self : self._src_root )
    DestRoot   = property( lambda self : self._dst_root )
    Verbose    = property( lambda self : self._defs['Verbose'] )
    Execute    = property( lambda self : self._defs['Execute'] )
    Quiet      = property( lambda self : self._defs['Quiet'] )

class IbModule_server_template_engine( object ) :
    modulePath = __file__

if __name__ == "__main__" :
    assert False, "not stand-alone"

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
