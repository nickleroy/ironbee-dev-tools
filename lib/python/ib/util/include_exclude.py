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
from ib.parser.base import *

class IbArchiverException( BaseException ) : pass
class IbArchiverRuleError( IbArchiverException ) : pass

class _ArchiverRule( object ) :
    """
    Base class for managing include / exclude rules for rsync
    and tar.  Note that tar doesn't support --include.
    """
    def __init__( self, _type, pattern ) :
        assert type(_type) == str
        assert type(pattern) == str
        assert _type in ( 'include', 'exclude' )
        self._type = _type
        self._pattern = pattern
    def __str__( self ) :
        return '--'+self._type+'='+self._pattern
    Pattern = property(lambda self : self._pattern)
    Type    = property(lambda self : self._type)

class IbArchiverIncludeRule( _ArchiverRule ) :
    def __init__( self, pattern ) :
        _ArchiverRule.__init__( self, 'include', pattern )

class IbArchiverExcludeRule( _ArchiverRule ) :
    def __init__( self, pattern ) :
        _ArchiverRule.__init__( self, 'exclude', pattern )

class IbArchiverRuleSet( object ) :
    def __init__( self, name=None, rules=None ) :
        assert name is None or type(name) == str
        assert rules is None or type(rules) in (list, tuple)
        self._name = name
        self._rules = []
        if rules is not None :
            self.AddRules( rules )

    def AddRules( self, rules ):
        assert type(rules) in (list, tuple)
        for rule in rules :
            self.AddRule( rule )

    def AddRule( self, rule ) :
        assert isinstance(rule, _ArchiverRule)
        if 'tar' in self._name and isinstance(rule, IbArchiverIncludeRule) :
            raise IbArchiverRuleError('IncludeRule "{:s}" not supported by tar'.format(rule.Pattern))
        self._rules.append(rule)

    def GetRules( self ) :
        return tuple( [ str(rule) for rule in self._rules ] )
    Rules = property( GetRules )


class _Executor( object ) :
    def __init__( self, parser ) :
        assert isinstance(parser, IbBaseParser)
        self._p = parser

    def Execute( self, cmd, cwd=None ) :
        if not self._p.Quiet :
            if cwd is None :
                print 'Executing', cmd
            else :
                print 'Executing', cmd, 'from', cwd
        if self._p.Execute :
            subprocess.call( cmd, cwd=cwd )


class IbArchiverRsync( _Executor ) :
    """
    Simple class building temp directories via rsync.
    """
    def __init__( self, parser, path ) :
        _Executor.__init__( self, parser )
        if os.path.isabs( path ) :
            self._path = path
        else :
            self._path = os.path.join(os.environ['QLYS_TMP'], path)

    Path  = property( lambda self : self._path )
    Rules = property( lambda self : self._rules )

    def AddIncludeRule( self, pattern ) :
        rule = IbArchiverIncludeRule( pattern )
        self._rules.AddRule( rule )

    def AddExcludeRule( self, pattern ) :
        rule = IbArchiverExcludeRule( pattern )
        self._rules.AddRule( rule )

    def Run( self, basedir, targets, wipe=True, ruleset=None ) :
        if wipe  and  self._p.Execute  and  os.path.exists(self._path) :
            shutil.rmtree( self._path )
        if ruleset is None :
            ruleset = IbArchiverRuleSet( )
        if not self._p.Quiet :
            print 'Populating', self._path, 'from', str(targets), "in", basedir
        if not self._p.Execute :
            rsync_flags = '-avn' if self._p.Verbose > 1 else '-an'
        elif self._p.Verbose :
            rsync_flags = '-av'
        else :
            rsync_flags = '-a'
        cmd = [ '/usr/bin/rsync', rsync_flags ] + \
              list(ruleset.Rules) + \
              targets + \
              [ self._path, ]
        self.Execute( cmd, basedir )


class IbArchiver( _Executor ) :
    """
    Simple class for creating tar archives, populating from archives.
    """
    def __init__( self, parser, tarball ) :
        _Executor.__init__( self, parser )
        assert isinstance(parser, IbBaseParser)
        self._tarball = tarball

    def Run( self, cwd=None, targets=None, ruleset=None ) :
        if ruleset is None :
            ruleset = IbArchiverRuleSet( )
        if targets is None :
            targets = [ '.' ]
        if not self._p.Quiet :
            name = os.path.splitext(os.path.basename(self._tarball))[0]
            print 'Creating', name, 'tarball', self._tarball
        tar_cmd = 'cvfj' if self._p.Verbose else 'cfj'
        cmd = [ "/bin/tar", tar_cmd, self._tarball ] + list(targets) + list(ruleset.Rules)
        self.Execute( cmd, cwd=cwd )
