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
import subprocess

class IbAchiverException( BaseException ) : pass
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

class IbArchiverIncludeRule( _BaseRule ) :
    def __init__( self, pattern ) :
        _BaseRule.__init__( self, 'include', pattern )

class IbArchiverExcludeRule( _BaseRule ) :
    def __init__( self, pattern ) :
        _BaseRule.__init__( self, 'exclude', pattern )

class IbArchiverRuleSet( object ) :
    def __init__( self, name=None, rules=None ) :
        assert name is None or type(name) == str
        assert rules is None or type(rules) in (list, tuple)
        self._rules = []
        if rules is not None :
            self.AddRules( rules )

    def AddRules( self, rules ):
        assert type(rules) in (list, tuple)
        for rule in rules :
            self.AddRule( rule )

    def AddRule( self, rule ) :
        assert isinstance(rule, _BaseRule)
        if 'tar' in self._name and isinstance(rule, _IncludeRule) :
            raise IbArchiverRuleError('IncludeRule "{:s}" not supported by tar'.format(rule.Pattern))
        self._rules.append(rule)

    def GetRules( self ) :
        return tuple( [ str(rule) for rule in self._rules ] )
    Rules = property( GetRules )


class IbArchiverRsync( object ) :
    """
    Simple class building temp directories via rsync.
    """
    def __init__( self, name, tmproot=None, ruleset=None ) :
        if tmproot is None :
            tmproot = os.environ['QLYS_TMP']
        self._path = os.path.join(tmproot, name)
        self._rules = IbArchiverRuleSet( ) if ruleset is None else ruleset

    def AddIncludeRule( self, pattern ) :
        rule = IbArchiverIncludeRule( pattern )
        self._rules.AddRule( rule )

    def AddExcludeRule( self, pattern ) :
        rule = IbArchiverExcludeRule( pattern )
        self._rules.AddRule( rule )

    def RsyncDir( self, path ) :


class IbArchiver( object ) :
    """
    Simple class for creating tar archives, populating from archives.
    and building temp directories via rsync.
    """
    def __init__( self, path ) :
        self._path = path

    def RsyncDir( self, path ) :
