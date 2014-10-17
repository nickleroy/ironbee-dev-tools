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
import string
import magic
import subprocess

class IbVersionException( BaseException ) : pass
class IbInvalidVersion( IbVersionException ) : pass
class IbInvalidVerOp( IbVersionException ) : pass

class IbVersion( object ) :
    _match_regexs = [ ]
    _search_regexs = [ ]
    _initialized = False

    @classmethod
    def _InitClass( cls ) :
        if cls._initialized :
            return
        regexs = ( r'(\d+)\.x\.x',
                   r'(\d+)\.(\d+)\.x',
                   r'(\d+)\.(\d+)\.(\d+)',
                   r'(\d+)\.(\d+)',
                   r'(\d+)' )
        for n,regex in enumerate(regexs) :
            cls._search_regexs.append( re.compile(regex) )
            cls._match_regexs.append( re.compile('^'+regex+'$') )

    def __init__( self, s, elements=None ) :
        self._InitClass( )
        if s is None  and  elements is None :
            raise IbInvalidVersion( )
        if elements is None :
            elements = self.StrToList( s )
            if elements is None :
                raise IbInvalidVersion( '"'+s+'"' )
        else :
            if type(elements) not in (list, tuple)  or  len(elements) not in (1,2,3) :
                raise IbInvalidVersion( str(elements) )
            for v in elements :
                if type(v) == str :
                    raise IbInvalidVersion( '"'+elements+'"' )
                elif type(v) != int :
                    raise IbInvalidVersion( str(elements) )
        self._s = s
        self._elements = tuple(elements)
        self._file = None

    def _GetVersionItem( self, n ) :
        try :
            return self._elements[n]
        except IndexError :
            return None

    def GetElement( self, n ) :
        return self._GetVersionItem( n )

    def _SetPath( self, path ) :
        self._path = path

    Major     = property( lambda self : self._GetVersionItem(0) )
    Minor     = property( lambda self : self._GetVersionItem(1) )
    Release   = property( lambda self : self._GetVersionItem(2) )
    Version   = property( lambda self : self._elements )
    Elements  = property( lambda self : len(self._elements) )
    String    = property( lambda self : str(self._elements) )
    RawString = property( lambda self : self._elements )
    Path      = property( lambda self : self._path, _SetPath )

    DefaultFormat = property( lambda self : "%{1}.%{2}.%{3}" )

    def Compare( self, other ) :
        for n in range( min(self.Elements, other.Elements) ) :
            elem1 = self.GetElement(n)
            elem2 = other.GetElement(n)
            if elem1 == elem2 :
                pass
            else :
                return elem2 - elem1
        return 0

    @classmethod
    def CheckStr( cls, s, match=True ) :
        cls._InitClass( )
        regexs = cls._match_regexs if match else cls._search_regexs
        for regex in regexs :
            m = regex.search( vstr )
            if m is not None :
                return True
        else :
            return False

    @classmethod
    def StrToList( cls, vstr, match=True ) :
        cls._InitClass( )
        regexs = cls._match_regexs if match else cls._search_regexs
        for regex in regexs :
            m = regex.search( vstr )
            if m is not None :
                break
        else :
            return None
        return tuple([ int(s) for s in m.groups()])

    @classmethod
    def CreateFromStr( cls, s, match=True ) :
        cls._InitClass( )
        l = cls.StrToList( s, match )
        if l is None :
            return None
        return cls( s, l )

    _term_formats = ('%{1}', '%{2}', '%{3}')
    _norm_formats = ('%[1]', '%[2]', '%[3]')
    _std_formats  = { r'\n':'\n', r'\t':'\t', r'\r':'\r', r'\b':'\b', r'\f':'\f', r'\\':'\\' }
    def Format( self, format=None ) :
        if format is None :
            format = self.DefaultFormat
        versions = [ str(n) for n in self._elements ]
        while len(versions) < 3 :
            versions.append( 'x' )
        for n, s in enumerate( self._term_formats ) :
            index = format.find( s )
            if index >= 0  and  len(self._elements) < n :
                format = format[:index]
                break
            format = format.replace( s, versions[n] )
        for n, s in enumerate( self._norm_formats ) :
            format = format.replace( s, versions[n] )
        for pat, repl in self._std_formats.items() :
            format = format.replace( pat, repl )
        return format


class _IbVersionCmpOp( object ) :
    def __init__( self, opstr, opfn ) :
        self._opstr = opstr
        self._opfn = opfn
    def CompareVersions( self, v1, v2 ) :
        return self.OpFn( v1, v2 )
    OpStr = property( lambda self : self._opstr )
    OpFn = property( lambda self : self._opfn )

class _IbVersionOpTable( object ) :
    _op_list = None
    _initialized = False

    @classmethod
    def _InitClass( cls ) :
        if cls._initialized :
            return
        cls._op_list = {
            '==' : _IbVersionCmpOp('==', cls._CmpEq),
            'eq' : _IbVersionCmpOp('eq', cls._CmpEq),
            '!=' : _IbVersionCmpOp('!=', cls._CmpNe),
            'ne' : _IbVersionCmpOp('ne', cls._CmpEq),
            '<'  : _IbVersionCmpOp('<' , cls._CmpLt),
            'lt' : _IbVersionCmpOp('lt', cls._CmpLt),
            '<=' : _IbVersionCmpOp('<=', cls._CmpLtEq),
            'le' : _IbVersionCmpOp('le', cls._CmpLtEq),
            '>'  : _IbVersionCmpOp('>' , cls._CmpGt),
            'gt' : _IbVersionCmpOp('gt', cls._CmpGt),
            '>=' : _IbVersionCmpOp('>=', cls._CmpGtEq),
            'ge' : _IbVersionCmpOp('ge', cls._CmpGtEq)
        }
        cls._initialized = True

    @classmethod
    def IsValidOpStr( cls, opstr ) :
        cls._InitClass( )
        return opstr in self._op_list

    @classmethod
    def GetOpFromStr( cls, opstr ) :
        cls._InitClass( )
        return cls._op_list.get( opstr )

    @staticmethod
    def _CmpEq( v1, v2 ) :
        return v1.Compare( v2 ) == 0

    @staticmethod
    def _CmpNe( v1, v2 ) :
        return v1.Compare( v2 ) != 0

    @staticmethod
    def _CmpLt( v1, v2 ) :
        return v1.Compare( v2 ) < 0

    @staticmethod
    def _CmpLtEq( v1, v2 ) :
        return v1.Compare( v2 ) <= 0

    @staticmethod
    def _CmpGt( v1, v2 ) :
        return v1.Compare( v2 ) > 0

    @staticmethod
    def _CmpGtEq( v1, v2 ) :
        return v1.Compare( v2 ) >= 0


class IbVersionComparer( object ) :
    def __init__( self ) :
        pass

    @classmethod
    def _CheckVersion( cls, ver ) :
        if ver is None  or  type(ver) is not IbVersion :
            raise IbInvalidVersion( '"'+str(ver)+'"' )

    @classmethod
    def _CheckOp( cls, op ) :
        if op is None  or  type(op) is not _IbVersionCmpOp :
            raise IbInvalidVerOp( '"'+str(op)+'"' )

    @classmethod
    def _MakeVersion( cls, vstr ) :
        if vstr is None :
            ver = None
        elif type(vstr) == IbVersion :
            ver = vstr
        elif type(vstr) == str :
            ver = IbVersion.CreateFromStr( vstr )
        else :
            ver = None
        if ver is None :
            raise IbInvalidVersion( '"'+str(vstr)+'"' )
        else :
            return ver

    @classmethod
    def _MakeOp( cls, opstr ) :
        if type(opstr) == _IbVersionCmpOp :
            op = opstr
        elif type(opstr) == str :
            op = _IbVersionOpTable.GetOpFromStr( opstr )
        else :
            op = None
        if op is None :
            raise IbInvalidVerOp( '"'+str(opstr)+'"' )
        else :
            return op

    @classmethod
    def CompareVersions( cls, v1, op, v2 ) :
        cls._CheckVersion(v1)
        cls._CheckVersion(v2)
        cls._CheckOp(op)
        return op.CompareVersions( v1, v2 )

    @classmethod
    def CompareVersionsStr( cls, v1str, opstr, v2str ) :
        v1 = cls._MakeVersion( v2str )
        op = cls._MakeOp( opstr )
        v2 = cls._MakeVersion( v1str )
        return op.CompareVersions( v1, v2 )


class IbVersionCmp( IbVersionComparer ) :
    def __init__( self, op, version ) :
        IbVersionComparer.__init__( self )
        self._CheckOp( op )
        self._CheckVersion( version )
        self._op      = op
        self._version = version

    Op      = property( lambda self : self._op )
    Version = property( lambda self : self._version )
    OpStr   = property( lambda self : self._op.OpStr )
    VerStr  = property( lambda self : self._op.String )

    @classmethod
    def CreateFromStrs( cls, opstr, verstr ) :
        op = _IbVersionOpTable.GetOpFromStr( opstr )
        version = IbVersion.CreateFromStr( verstr )
        if op is None  or  version is None :
            return None
        return cls( opstr, version )

    def Compare( self, verinfo ) :
        assert type(verinfo) in (IbVersion, IbVersionCmp)
        if type(verinfo) is IbVersion :
            return self.CompareVersions( self.Version, verinfo )
        elif type(verinfo) is IbVersionCmp :
            return self.CompareVersions( self.Version, verinfo.Version )


class IbVersionReader( object ) :
    def __init__( self ) :
        self._magic = magic.open(magic.NONE)
        self._magic.load( )

    def GetAutoVersion( self, path ) :
        ftype = self._magic.file( os.path.realpath(path) )
        self._last_path = path
        if 'ASCII' in ftype  or  'text' in ftype :
            return self.GetTextVersion( path )
        else :
            return self.GetBinVersion( path )

    _printable = frozenset(string.printable)
    def GetStrings( self, fp ) :
        found_str = ""
        while True:
            data = fp.read(1024*4)
            if not data:
                break
            for char in data:
                if char in self._printable:
                    found_str += char
                elif len(found_str) >= 4:
                    yield found_str
                    found_str = ""
                else:
                    found_str = ""

    _bin_re = re.compile( r"IronBee/([\d\.]+)" )
    def GetBinVersion( self, path ) :
        try :
            fp = open(path, "rb")
            for line in self.GetStrings( fp ) :
                m = self._bin_re.match( line )
                if m is None :
                    continue
                version = IbVersion.CreateFromStr( m.group(1) )
                if version is not None :
                    version.Path = path
                    return version
            return None
        except IOError as e :
            return None

    def GetTextVersion( self, path ) :
        regex = re.compile( 'VERSION=([\d\.]+)' )
        for line in open(path) :
            m = regex.search(line)
            if m is None :
                continue
            version = IbVersion.CreateFromStr( m.group(1) )
            if version is not None :
                version.Path = path
                return version
        return None

    @staticmethod
    def FindFile( path ) :
        if os.path.isfile( path ) :
            return path
        for name in ('libironbee.a', 'libironbee.so') :
            full = os.path.join(path, name)
            if os.path.isfile( full ) :
                return full
        return None

IbVersion._InitClass( )
_IbVersionOpTable._InitClass( )
