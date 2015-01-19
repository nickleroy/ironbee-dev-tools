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
        elif type(s) == IbVersion : 
            elements = s.Elements
        if elements is None :
            elements = self.StrToList( s )
            if elements is None :
                raise IbInvalidVersion( '"'+s+'"' )
        else :
            if type(elements) == int :
                elements = [elements]
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

    Major       = property( lambda self : self._GetVersionItem(0) )
    Minor       = property( lambda self : self._GetVersionItem(1) )
    Release     = property( lambda self : self._GetVersionItem(2) )
    Version     = property( lambda self : self._elements )
    NumElements = property( lambda self : len(self._elements) )
    Elements    = property( lambda self : tuple(self._elements) )
    String      = property( lambda self : str(self._elements) )
    RawString   = property( lambda self : self._elements )
    Path        = property( lambda self : self._path, _SetPath )

    DefaultFormat = property( lambda self : "%{1}.%{2}.%{3}" )

    def Compare( self, other, ignore=True ) :
        for n in range( min(self.NumElements, other.NumElements) ) :
            elem1 = self.GetElement(n)
            elem2 = other.GetElement(n)
            if elem1 != elem2 :
                return elem2 - elem1
        if ignore :
            return 0
        else :
            return other.NumElements - self.NumElements

    def __getitem__( self, k ) :
        return IbVersion(None, self._elements[k])

    def __cmp__( self, other ) :
        return self.Compare( other, False )

    def __eq__( self, other ) :
        return self.Compare( other, True ) == 0

    def __ne__( self, other ) :
        return self.Compare( other, True ) != 0

    def __gt__( self, other ) :
        return self.Compare( other, False ) < 0

    def __ge__( self, other ) :
        return self.Compare( other, True ) <= 0

    def __lt__( self, other ) :
        return self.Compare( other, False ) > 0

    def __le__( self, other ) :
        return self.Compare( other, True ) >= 0

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

    def __str__( self ) :
        return self.Format( )


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

IbVersion._InitClass( )
_IbVersionOpTable._InitClass( )


if __name__ == "__main__" :
    v0x  = IbVersion('0')
    v01x = IbVersion('0.1')
    v010 = IbVersion('0.1.0')
    v011 = IbVersion('0.1.1')
    v012 = IbVersion('0.1.2')
    v013 = IbVersion('0.1.3')
    v02x = IbVersion('0.2')
    v020 = IbVersion('0.2.0')
    v021 = IbVersion('0.2.1')
    v022 = IbVersion('0.2.2')
    v023 = IbVersion('0.2.3')
    v1x  = IbVersion('1')
    v10x = IbVersion('1.0')
    v100 = IbVersion('1.0.0')
    v101 = IbVersion('1.0.1')
    v102 = IbVersion('1.0.2')
    v103 = IbVersion('1.0.3')
    v11x = IbVersion('1.1')
    v110 = IbVersion('1.1.0')
    v111 = IbVersion('1.1.1')
    v112 = IbVersion('1.1.2')
    v113 = IbVersion('1.1.3')
    v12x = IbVersion('1.2')
    v120 = IbVersion('1.2.0')
    v121 = IbVersion('1.2.1')
    v122 = IbVersion('1.2.2')
    v123 = IbVersion('1.2.3')
    assert v01x[0] == IbVersion('0'), str(v01x[0])+' != '+str(IbVersion('0'))
    assert v10x[0] == IbVersion('1')
    assert v01x[0:1] == IbVersion('0')
    assert v01x[0:2] == IbVersion('0.1')
    assert v10x[0:2] == IbVersion('1.0')
    assert v100[0:2] == IbVersion('1.0')
    assert v100[0:3] == IbVersion('1.0.0')
    assert v010[0] == IbVersion('0')
    assert v1x  >  v0x
    assert v10x >  v01x
    assert v010 == v01x
    assert v010 >  v01x
    assert v011 == v01x
    assert v101 >  v100
    assert v102 >  v100
    assert v102 >  v10x
    assert v10x <  v102
    assert v102 >= v10x
    assert v11x >  v10x
    assert v11x >  v103
    assert v111 >  v100
    assert v111 >  v110
    assert v120 >= v12x
    assert IbVersion('0.11.3') == IbVersion('0.11.3')
    assert IbVersion('0.11.2') == IbVersion('0.11')
    assert IbVersion('0.11.3') == IbVersion('0.11')
    print "Passed"

class IbModule_util_version( object ) :
    modulePath = __file__

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
