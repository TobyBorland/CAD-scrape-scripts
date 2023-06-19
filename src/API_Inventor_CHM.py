# -------------------------------------------------------------------------------
# Name:        API_Inventor_CHM.py
# Purpose:     Parse the Autodesk Inventor collection of html help files into an
# 				XML file that identify the COM variant type
#
# Author:      Toby Borland 2019, tobyborland@hotmail.com
#
# Created:     06/02/2016
# Revised:     Derived from API_SWKS_CHM_07.py 17Sept16
# Copyright:   (c) Toby Borland  2016
# Licence:     This program is free software: you can redistribute it and/or modify
#              it under the terms of the GNU General Public License as published by
#              the Free Software Foundation, either version 3 of the License, or
#              (at your option) any later version.
#
#               This program is distributed in the hope that it will be useful,
#               but WITHOUT ANY WARRANTY; without even the implied warranty of
#               MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#               GNU General Public License for more details.
#
#               You should have received a copy of the GNU General Public License
#               along with this program.  If not, see <https://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

# beautifulsoup4 installed via "pip3.4 install beautifulsoup4" in cmd terminal
from bs4 import BeautifulSoup, NavigableString, Comment
#from bs4 import SoupStrainer
import os # issues with shadowing open()

# note weird Unicode translation fail with \U in C:\Users.. use \\ or r"string"
#WORKDir =  r"C:\Users\Foobert\Desktop\PY_DELL2\SWKS_help_XML\API_doc_parse\API_data"
cadDir = r"C:\Users\Foobert\Desktop\PY_DELL2\Inventor_help_XML\Inventor12_help\admapi_16"
WORKDir =  r"C:\Users\Foobert\Desktop\PY_DELL2\Inventor_help_XML\Inventor12_help"

import xml.etree.ElementTree as ET
CAD_XMLtable = ET.Element('CAD_XMLtable_03')
CAD_API = ET.SubElement(CAD_XMLtable, 'apiSet', name = 'Inventor2012')

import re, string
LPDISPATCHre = re.compile(r'\bLP[A-Z2-9]+\b', re.IGNORECASE)
dispatchRe = re.compile( r'\bface\d?s?\b|\bedges?\b', re.IGNORECASE)
arrayRe = re.compile( r'\barray\b|\bsafearray\b', re.IGNORECASE)
isValidHTML = re.compile( r'\b([a-z0-9_]+)\.(html?)\b', re.IGNORECASE)
isHTMLcomment = re.compile( r'<!--.*-->')
isHTMLdoctype = re.compile( r'HTML PUBLIC "-//W3C//DTD HTML 4.0 Frameset//EN"')
arrDispatchRe = re.compile( r'array of dispatch\b', re.IGNORECASE) #________________________???
ObjectRe = re.compile(r'/bpbject?s/b', re.IGNORECASE)
paramRe = re.compile( r'\(\b(\&?\**\w+\**)\s?\)\s*(\&?\**\w+)\b', re.IGNORECASE)
StringRe = re.compile( r'\bstrings?\b|\bBSTR\*?\b', re.IGNORECASE)
ShortRe = re.compile( r'\bshorts?\b', re.IGNORECASE)
IntRe = re.compile( r'\bints?\b', re.IGNORECASE)
LongRe = re.compile( r'\blongs?\b', re.IGNORECASE)
FloatRe = re.compile( r'\bfloats?\b', re.IGNORECASE)
DoubleRe = re.compile( r'\bdoubles?\b', re.IGNORECASE)
pointerToRe = re.compile( r'\bpointer?s?\s+to\b', re.IGNORECASE)
OLEre = re.compile(r'^Syntax\s*\(OLE\s+Auto', re.IGNORECASE)
COMre = re.compile(r'^Syntax\s*\(COM', re.IGNORECASE)

InventorInputRe = re.compile(r'(?<=\WInput\W)(\b\w+\b)', re.IGNORECASE)
InventorObjectRe = re.compile(r'(\b\w+\b)(?=\Wobject\W)', re.IGNORECASE)

unknownObject = []
unknownDispatch = []

# create a local corpus of method names, parameter names, unique helpstring words
methodNames = []
paramNames = []
helpStringCorpus = '' # dump it all in, convert to a set later
dump = []
CSVoutput = []
Verbose = False #True #
modelSentence = ''
SS_methodNames = ''

# invParam object captures parameter data
class invParam(object):
	name = ''
	basetype = ''
	subtype = ''
	modifier = ''
	reference = ''
	subreference = ''
	direction = '' # Input Output ByRef

	# invParam constructor/initialiser
	def __init__(self, name, basetype, reference, subtype, subreference, modifier, direction):
		self.name = name
		self.basetype = basetype
		self.reference = reference
		self.subtype = subtype
		self.subreference = subreference
		self.modifier = modifier
		self.direction = direction

def catalogParam(name, basetype, baseref, subtype, subref, modifier, direction):
	param = invParam(name, basetype, baseref, subtype, subref, modifier, direction)
	return param

def deCamel(camelCase):
	# strip camelcase format
	#import re
	camelCase = re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', camelCase)
	return camelCase

def refPrefix(typestring, refcount):
	typestring = typestring.replace(' ','-')
	for rc in range(0, refcount):
		typestring = 'ptr_to_' + typestring
	return typestring

def testVTtype(s):
	String = StringRe.search(s) # C types
	Short = ShortRe.search(s)
	Int = IntRe.search(s)
	Long = LongRe.search(s)
	Float = FloatRe.search(s)
	Double = DoubleRe.search(s)
	LPDISPATCH = LPDISPATCHre.search(s)

	VARIANT = re.search(r'\bVARIANT\b', s)
	VARIANT_BOOL = re.search(r'\bVARIAN?T?_BOOLE?A?N?\b', s)
	BOOL = re.search(r'\bBOOLE?A?N?\b', s)
	HRESULT = re.search(r'\bHRESULT\b', s)
	LPobject = re.search(r'\bLP\w+\b', s)
	#dispatch = re.search(r'\bd?D?ispatch\b', s)

	#http://www.quickmacros.com/help/Tables/IDP_VARIANT.html
	#PointerTo = re.search(r'\b\&\w+',s)
	#PointerTo = re.search(r'\w+\*',s)
	#PtrPtrTo = re.search(r'\b\*\*\w+',s)

	VT = None
	if VARIANT:
		VT = 0xC # VARIANT is replaced by other type in subsequent search, relevant to comment parsing
		pType = ''
	if Short:
		VT = 0x2
		pType = 'short'
	if Int or Long:
		VT = 0x3
		pType = 'integer'
	if Float:
		VT = 0x4
		pType = 'float'
	if Double:
		VT = 0x5
		pType = 'double'
	if String:
		VT = 0x8 # VT_BSTR
		pType = 'string'
	if LPDISPATCH: # or dispatch: # access to underlying IDispatch pointer
		VT = 0x9
		pType = 'dispatch-pointer'
	if VARIANT_BOOL or BOOL:
		VT = 0xB
		pType = 'VARIANT_BOOL' #'boolean'
		print("VARIANT_BOOL or BOOL?: "+s)
	if HRESULT:
		VT = 0x19
		pType = 'HRESULT'
	if LPobject:
		VT = 0x9 #___________________________________check
		pType = 'object'
		unknownObject.append(s)
	#if Array: # is it possible to identify between safearray (0x27) and C style array (0x28)
	# array always specified as safearray as VB6 variant type is safearray for COM boundary traversal
	#	VT = 0x27
	#if PointerTo:
	#	VT = VT + 0x4000
	##if PtrPtrTo: # cannot distinguish between "pointer to" and "pointer to pointer to"?
	#	#VT = VT + 0x4000
	#	pType = 'pointer-to-' + pType
	#	#print("Please check pointer to pointer.. always array of Dispatch/COM objects?: "+s)
	if not VT:
		print('Unknown type (testVTtype): '+s)
		pType = 'unknown'
		unknownDispatch.append(s) #probably
	return [VT, pType]

# Inventor does not divide parameter categories with handy tags on the same line.
# Instead, they are guessed from a table structure that flattens into a single word parameter name followed by
# a descriptive sentence using the convention of "Input <type>..."

# test for multiple instances of Input/Output/Properties
# Property is a referenced COM accessible parameter that is changed, (i.e. input AND output)
CommaCatchRe = re.compile(r'(?<!\s\[in|\[out)(\,)')

ParamRe = re.compile(r'''
	(\bProperty\b\s|\bByRef\b\s|\(|\,\s)    # determine is object method parameter passed by reference, or is a get/set object property
	(\b\w+\b)								# parameter name
    (?:\(\))?                               # property brackets.. untested ByRef parameter possibility________________________________
	(?:\sAs\s)								# VB declaration syntax non-capture group
	(\[\w+[\,\s\w\(\)]*\]\s)?				# optional square bracket encapsulated modifier, e.g. [optional], [out, retval]
	([\w\s]+\**)							# parameter base type
	(\([\w\s]+\**\))?                       # parameter subtype, e.g. SAFEARRAY(unsigned char)
	''', re.VERBOSE)

EnumTypeRe = re.compile(r'\b\w+Enum\b') # Enumeration type in Description instead of input / output
FlagTypeRe = re.compile(r'\bflag\b', re.IGNORECASE) # Flag type in Description instead of input / output
FilenameTypeRe = re.compile(r'(\[in)|(\[out)|(\[defaultvalue)|(\[optional)|(\[unique)')
EmptyBracketsRe = re.compile(r'\(\)')
OLEsubNameRe = re.compile(r'(\b\w+)(?:\([\w\s\(\,\[\]\*\)]*$)', re.IGNORECASE)

def getParams(syntax):
	# return list of invParam objects with assessed parameter qualities
	invP = []
	pName = 'none'
	pType = 'none'
	pRef = 0
	pSubType = 'none'
	pSubRef = 0
	pModifier = 'none'
	pDirection = 'none'
	ParamGroup = ParamRe.findall(syntax)
	for pg in ParamGroup:
		if pg[1] != '': # somehow None gets modifies to ''
			pName = pg[1]
		if pg[2] != '': # somehow None gets modifies to ''
			pModifier = pg[2]
			pModifier = pModifier[1:-2] # strip square brackets
			if 'input' in pModifier:
				pDirection = 'input'
			elif 'output' in pModifier:
				pDirection = 'output'
		if pg[0] == 'ByRef' or pg[0] == 'Property':
			pDirection = pg[0]
		if pg[3] != '':
			pType = pg[3]
			pRef = pType.count('*')
			pType = pType.replace('*', '')
		if pg[4]:
			if pType != 'SAFEARRAY':
				print('unexpected subtype: ' + pg[3])
			pSubType = pg[4]
			pSubType = pSubType[1:-2] # strip brackets
			pSubRef = pSubType.count('*')
			pSubType = pSubType.replace('*', '')

		invP.append(catalogParam(pName, pType, pRef, pSubType, pSubRef, pModifier, pDirection))
	return invP


for (root, dirs, files) in os.walk(cadDir, topdown=False):
	for APIname in files:
		if Verbose:
			print('Opening ' + APIname)
		cadFullFilePath = os.path.join(u'\\\\?\\' + root, APIname) # string added to bypass 256 character path limit in windows 7 OS

		#isValidHTML = re.compile( r'\b([a-z0-9_]+)\.(html?)\b', re.IGNORECASE)
		#isUnderscoreFreeHTML = re.compile( r'\b[A-Za-z0-9]+\b.htm?')
		if isValidHTML.search(APIname): # avoid gifs, etc
			with open(cadFullFilePath) as FileHandle:
				CAD_BS = BeautifulSoup(FileHandle, "html.parser")

			dirName = root[len(cadDir)+1:]
			if not dirName:
				dirName = '' # 'root directory'
			if Verbose:
				print(dirName)
			#print('Extracting types from ' + APIname + ' in ' + dirName)

			FileNameParse = FilenameTypeRe.findall(APIname)

			comments = CAD_BS.findAll(text=lambda text:isinstance(text, Comment))
			[comment.extract() for comment in comments] # remove comment tag from bs tree

            # strip out human-readable text

			#helpStrings = [a for a in re.sub('[\n\xa0]+','\n', CAD_BS.getText()).split('\n') if a != ''] # strip newlines, tabs, empty strings
			helpStrings = [a for a in re.sub(r'\s?\xa0\n+','\n', CAD_BS.getText()).split('\n') if a != ''] # strip newlines, tabs, empty strings

##			helpStrings = list(filter(('').__ne__, helpStrings))
##			if Verbose:
##				print('\n'.join(helpStrings))
##				print('__________________________________________________________________________\n')

			dump = []
			[dump.append(re.findall('[\w\-\_]+', line)) for line in helpStrings] # split into seperate words
			dump = [s for ss in dump for s in ss] # remove sub-lists
			dump = ' '.join(dump)
			helpStringCorpus = helpStringCorpus + ' ' + dump
			#input(' return to continue')

			# 'object::method'
			#ObjectMethod = re.search( r'(\b\w+)::(\w+\b)', CAD_BS.title.string)

			# 'Object.Interface MethodOrProp' Interface may be Property or Method Quality.. does this matter?
			ObjectInterfaceQuality = re.search( r'(\b\w+)\.(\w+\b) (\w+)', CAD_BS.title.string)
			if ObjectInterfaceQuality: # if regexp fails (as in an interface description page), skip the process
				Object = ObjectInterfaceQuality.group(1)
				InventorMethod = ObjectInterfaceQuality.group(2)
				MethodOrProp = ObjectInterfaceQuality.group(3) # some properties have referenced variables
				methodNames.append(deCamel(InventorMethod))
				SS_methodNames = SS_methodNames + deCamel(InventorMethod) + '\n'

				XMLtableObject = ET.SubElement(CAD_API, 'object', name = Object, category = dirName) #______________________________________________
				#XMLtableObject = ET.SubElement(CAD_API, 'object', name = Object)
				XMLtableMethod = ET.SubElement(XMLtableObject, 'method', name = InventorMethod) # may require update to reflect property, etc

				if 'Summary' in helpStrings: # equivalent to "Description" heading
					if helpStrings.index('Summary') + 1 < len(helpStrings):
						MethodDescription = helpStrings[helpStrings.index('Summary') + 1]
						XMLtableMethodDescription = ET.SubElement(XMLtableMethod, 'description')
						XMLtableMethodDescription.text = MethodDescription
						#descriptionText.append(MethodDescription)
						modelSentence = modelSentence + deCamel(InventorMethod) + ' ' + MethodDescription + '\n' #


				if 'Visual Basic' in helpStrings:
					if helpStrings.index('Visual Basic') + 1 < len(helpStrings):
						OLEsyntax = helpStrings[helpStrings.index('Visual Basic') + 1]
						OLEsyntax = re.sub('Sub ', '', OLEsyntax)
						#OLEsubName = OLEsubNameRe.search(OLEsyntax)
						XMLtableOLEsyntax = ET.SubElement(XMLtableMethod, 'ole_syntax')
						XMLtableOLEsyntax.text = OLEsyntax + '\n'

					# test syntax for variables, then test description for input, output, inout/output
					# determine return values, no input variables used but referenced variables possible (ByRef)
					invParams = getParams(OLEsyntax) # list of identified parameters/property

					# determine number of parameters via commas in syntax description
					ParamCount = CommaCatchRe.findall(OLEsyntax)
					ParamCount = len(ParamCount) + 1
					if ParamCount != len(invParams) and invParams != []:
						print('comma/regexp parameter detection mismatch: ' + OLEsyntax)
						print('	..in ' + APIname)
					if len(FileNameParse) != ParamCount and FileNameParse != []:
						print('filename/regexp parameter detection mismatch: ' + APIname)
						print('	..in ' + APIname)

					# test description for input, output, input/output
					if not 'Parameters' in helpStrings:
						if MethodOrProp == 'Method':
							if EmptyBracketsRe.search(OLEsyntax):
								print('method without parameters: ' + OLEsyntax)
								print('	..in ' + APIname + '\n')
								# e'g' Sub Delete()
						elif MethodOrProp == 'Property':
							if not EmptyBracketsRe.search(OLEsyntax):
								print('property with parameters: ' + OLEsyntax)
								print('	..in ' + APIname + '\n')
								# e'g' IAnimationFavorites.Count
						else:
							if InventorMethod.find('Enum') < 0:
								print('detection fail: ' + InventorMethod + ' : ' + MethodOrProp)
								print('	..in ' + APIname + '\n')

					else: #_______________________________________________________NOT IN PROPERTIES
						if helpStrings.index('Parameters') + 3 < len(helpStrings): # next two strings are 'Parameters', 'Description',
							helpRange = helpStrings[helpStrings.index('Parameters') + 3:len(helpStrings)]
							#for ip in invParams: #
							for ipIndex, ip in enumerate(invParams):
								if ip.name in helpRange:
									if ipIndex <= len(FileNameParse) and FileNameParse != []:
										if any(['in' in fnp for fnp in FileNameParse[ipIndex]]):
											FNP = 'in' # also use the information in API filename
										elif any(['out' in fnp for fnp in FileNameParse[ipIndex]]):
											FNP = 'out'
									else:
										print('filename/parameter mismatch: '  + ip.name + ' ..of.. ' +  ParamDescription)
										print('	..in ' + APIname + '\n')

									ParamDescription = helpRange[helpRange.index(ip.name) + 1]
									if ParamDescription.find('Input', 0, 5) == 0: # ConvertToTransitionalConstraint, second word
										PD = 'in'
									elif ParamDescription.find('Optional input', 0, 14) == 0:
										PD = 'in'
									elif ParamDescription.find('Specifies', 0, 9) == 0:
										PD = 'in'
									elif ParamDescription.find('Optional output', 0, 15) == 0: #
										PD = 'out'
									elif ParamDescription.find('Input/output', 0, 12) == 0:
										PD = 'out'
									elif ParamDescription.find('Output', 0, 6) == 0:
										PD = 'out'
									elif EnumTypeRe.search(ParamDescription):
										PD = 'out'
										print('Enum state? : ' + ParamDescription + '\n')
									elif FlagTypeRe.search(ParamDescription):
										PD = 'in'
										print('Enum state? : ' + ParamDescription + '\n')
									else:
										PD = 'unknown'
										#input(' -> return to continue..')

									if PD == 'in' and FNP == 'in':
										ip.direction = 'input'
									elif PD == 'out' and FNP == 'out':
										ip.direction = 'input'
									else:
										ip.direction = 'unknown'
										print('indeterminate input/output state? : ' + ip.name + ' ..of.. ' +  ParamDescription)
										print('	..in ' + APIname + '\n')


								if ip.name =='unknown':
									fnp = FileNameParse[invParams.index(ip)]
									if fnp[0] == '':
										ip.direction = 'output'
									elif fnp[1] == '':
										ip.direction - 'input'
								if ip.name == 'Return':
									ip.direction = 'output'
								if ip.modifier.find('optional') >= 0:
									ParamOptional = 'optional'
								else:
									ParamOptional = 'required'
								if ip.subtype != 'none':
									varSubType = refPrefix(ip.subtype, ip.subreference)
								else:
									varSubType = 'none'

								# how to map object/class inheritance instances?
								# note VBA .NET style in contrast to OLE Automation.. managed/unmanaged code..

								XMLtableParam = ET.SubElement(XMLtableOLEsyntax,
									ip.direction,
									name = ip.name,
									vartype = refPrefix(ip.basetype, ip.reference),
									varsubtype = varSubType,
									optional = ParamOptional)
								XMLtableParam.text = ParamDescription

						# attach implementation remarks
						if 'Remarks' in helpStrings:
							if helpStrings.index('Remarks') + 1 < len(helpStrings):
								MethodRemarks = helpStrings[helpStrings.index('Remarks') + 1]
								XMLtableMethodRemarks = ET.SubElement(XMLtableMethod, 'remarks')
								XMLtableMethodRemarks.text = MethodRemarks

						if Verbose:
							XMLtable_bs = BeautifulSoup(ET.tostring(XMLtableMethod, method='html'))
							print(XMLtable_bs.prettify())
							print('-----------------------------------------------')

			#____________________________________________________________________________________________________________________
						if MethodDescription:
							MethodDescriptionLine = re.search(r'[\s\S]+\.?', MethodDescription)
							if MethodDescriptionLine:
								MethodDescriptionLine = MethodDescriptionLine.group(0)
								CSVoutput.append(
								# dirName + '\t ' +
								Object + '.' + InventorMethod + '\t ' +
								OLEsyntax.splitlines()[0].split(r'= ')[-1] + '\t ' +
								MethodDescriptionLine + '\n') # comments in syntax field, use tab delimiter
			                    # forgot discrimination between OLEsyntax and VBsyntax in this case
							else:
								   CSVoutput.append(dirName + '\t ' + OLEsyntax.splitlines()[0].split(r'= ')[-1] + '\n') # comments in syntax field, use tab delimiter


with open(os.path.join(WORKDir, 'invAPI_2.csv'), 'w', encoding='utf8') as CSVfile:
	dummy = [CSVfile.write(CSVo) for CSVo in CSVoutput] # dummy => silent output
	#CSVfile.close()

#exit(0)
#____________________________________________________________________________________________________________________


XMLtable_bs = BeautifulSoup(ET.tostring(CAD_XMLtable), "html.parser")
##with open(os.path.join(WORKDir, 'Inventor_A1.xml'), 'w', encoding='utf8') as XMLfile:
##	XMLfile.write(XMLtable_bs.prettify())

def indent(elem, level=0):
	i = "\n" + level*"  "
	if len(elem):
		if not elem.text or not elem.text.strip():
			elem.text = i + "  "
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
		for elem in elem:
			indent(elem, level+1)
		if not elem.tail or not elem.tail.strip():
			elem.tail = i
	else:
		if level and (not elem.tail or not elem.tail.strip()):
			elem.tail = i

indent(CAD_XMLtable)
##with open(os.path.join(WORKDir, 'Inventor_B1.xml'), 'wb') as XMLfile:
##	XMLfile.write(ET.tostring(CAD_XMLtable))#, xml_declaration=True, encoding='utf-8', method="xml"
##	XMLfile.close()
##
##with open(os.path.join(WORKDir, 'Inventor_C1.xml'), 'w', encoding='utf8') as XMLfile:
##	XMLfile.write(bytes.decode(ET.tostring(CAD_XMLtable)))#, xml_declaration=True, encoding='utf-8', method="xml"
##	XMLfile.close()

SS_methodNames = SS_methodNames.lower()
SS_methodNames = re.sub(r'[0-9]\b', r'', SS_methodNames) # strip out numbers
SS_methodNames = re.sub(r'\bi\s+\b', r'', SS_methodNames) # strip out IDispatch prefix
with open(os.path.join(WORKDir, 'InventorAPI_methodNames.txt'), 'w', encoding='utf8') as methodNamesFile:
	methodNamesFile.write(SS_methodNames)
	methodNamesFile.close()

modelSentence = re.sub('-', ' ', modelSentence) # sort out hyphenation
modelSentence = re.sub('[%s]' % re.escape(string.punctuation), '', modelSentence.lower()) # strip punctuation and convert to lowercase
with open(os.path.join(WORKDir, 'InventorAPI_w2v.txt'), 'w', encoding='utf8') as word2vecFile:
	word2vecFile.write(modelSentence)
	word2vecFile.close()

import pickle
pickle.dump(paramNames, open(os.path.join(WORKDir, 'paramNames.p'), 'wb'))
pickle.dump(methodNames, open(os.path.join(WORKDir, 'methodNames.p'), 'wb'))

# Extracting types from Body2__AddProfileBspline.htm
# -> unlikely translation because of integers packed as doubles in unsafe arrays
# can the percentage of likely fails be determined?

#ignore flags, booleans for the present
# take every function with..
# get an edge/point/face/body intersection return

# same for FreeCAD/Rhino
# check first comparisons.. or just looki at data

# take two functions with similar/same body creation
# try the rayintersections and see how long a match takes.

# => requires Rhino/Python rayintersection
# similar listing of functions.

##VT_EMPTY = 0
##VT_NULL = 1
##VT_I2 = 2
##VT_I4 = 3
##VT_R4 = 4
##VT_R8 = 5
##VT_CY = 6
##VT_DATE = 7
##VT_BSTR = 8
##VT_DISPATCH = 9
##VT_ERROR = 10
##VT_BOOL = 11
##VT_VARIANT = 12
##VT_UNKNOWN = 13
##VT_DECIMAL = 14
##VT_I1 = 16
##VT_UI1 = 17
##VT_UI2 = 18
##VT_UI4 = 19
##VT_I8 = 20
##VT_UI8 = 21
##VT_INT = 22
##VT_UINT = 23
##VT_VOID = 24
##VT_HRESULT = 25
##VT_PTR = 26
##VT_SAFEARRAY = 27
##VT_CARRAY = 28
##VT_USERDEFINED = 29
##VT_LPSTR = 30
##VT_LPWSTR = 31
##VT_RECORD = 36
##VT_INT_PTR = 37
##VT_UINT_PTR = 38
##VT_FILETIME = 64
##VT_BLOB = 65
##VT_STREAM = 66
##VT_STORAGE = 67
##VT_STREAMED_OBJECT = 68
##VT_STORED_OBJECT = 69
##VT_BLOB_OBJECT = 70
##VT_CF = 71
##VT_CLSID = 72
##VT_VERSIONED_STREAM = 73
##VT_BSTR_BLOB = 4095
##VT_VECTOR = 4096
##VT_ARRAY = 8192
##VT_BYREF = 16384
##VT_RESERVED = 32768
##VT_ILLEGAL = 65535
##VT_ILLEGALMASKED = 4095
##VT_TYPEMASK = 4095


## http://ahkscript.org/docs/commands/ComObjType.htm
##VT_EMPTY	 =	  0  ; No value
##VT_NULL	  =	  1  ; SQL-style Null
##VT_I2		=	  2  ; 16-bit signed int
##VT_I4		=	  3  ; 32-bit signed int
##VT_R4		=	  4  ; 32-bit floating-point number
##VT_R8		=	  5  ; 64-bit floating-point number
##VT_CY		=	  6  ; Currency
##VT_DATE	  =	  7  ; Date
##VT_BSTR	  =	  8  ; COM string (Unicode string with length prefix)
##VT_DISPATCH  =	  9  ; COM object
##VT_ERROR	 =	0xA  ; Error code (32-bit integer)
##VT_BOOL	  =	0xB  ; Boolean True (-1) or False (0)
##VT_VARIANT   =	0xC  ; VARIANT (must be combined with VT_ARRAY or VT_BYREF)
##VT_UNKNOWN   =	0xD  ; IUnknown interface pointer
##VT_DECIMAL   =	0xE  ; (not supported)
##VT_I1		=   0x10  ; 8-bit signed int
##VT_UI1	   =   0x11  ; 8-bit unsigned int
##VT_UI2	   =   0x12  ; 16-bit unsigned int
##VT_UI4	   =   0x13  ; 32-bit unsigned int
##VT_I8		=   0x14  ; 64-bit signed int
##VT_UI8	   =   0x15  ; 64-bit unsigned int
##VT_INT	   =   0x16  ; Signed machine int
##VT_UINT	  =   0x17  ; Unsigned machine int
##VT_RECORD	=   0x24  ; User-defined type -- NOT SUPPORTED
##VT_ARRAY	 = 0x2000  ; SAFEARRAY
##VT_BYREF	 = 0x4000  ; Pointer to another type of value
##/*
## VT_ARRAY and VT_BYREF are combined with another value (using bitwise OR)
## to specify the exact type. For instance, 0x2003 identifies a SAFEARRAY
## of 32-bit signed integers and 0x400C identifies a pointer to a VARIANT.
##*/


##https://msdn.microsoft.com/en-us/library/windows/desktop/ms221170%28v=vs.85%29.aspx
##enum VARENUM {
##  VT_EMPTY			 = 0,
##  VT_NULL			  = 1,
##  VT_I2				= 2,
##  VT_I4				= 3,
##  VT_R4				= 4,
##  VT_R8				= 5,
##  VT_CY				= 6,
##  VT_DATE			  = 7,
##  VT_BSTR			  = 8,
##  VT_DISPATCH		  = 9,
##  VT_ERROR			 = 10,
##  VT_BOOL			  = 11,
##  VT_VARIANT		   = 12,
##  VT_UNKNOWN		   = 13,
##  VT_DECIMAL		   = 14,
##  VT_I1				= 16,
##  VT_UI1			   = 17,
##  VT_UI2			   = 18,
##  VT_UI4			   = 19,
##  VT_I8				= 20,
##  VT_UI8			   = 21,
##  VT_INT			   = 22,
##  VT_UINT			  = 23,
##  VT_VOID			  = 24,
##  VT_HRESULT		   = 25,
##  VT_PTR			   = 26,
##  VT_SAFEARRAY		 = 27,
##  VT_CARRAY			= 28,
##  VT_USERDEFINED	   = 29,
##  VT_LPSTR			 = 30,
##  VT_LPWSTR			= 31,
##  VT_RECORD			= 36,
##  VT_INT_PTR		   = 37,
##  VT_UINT_PTR		  = 38,
##  VT_FILETIME		  = 64,
##  VT_BLOB			  = 65,
##  VT_STREAM			= 66,
##  VT_STORAGE		   = 67,
##  VT_STREAMED_OBJECT   = 68,
##  VT_STORED_OBJECT	 = 69,
##  VT_BLOB_OBJECT	   = 70,
##  VT_CF				= 71,
##  VT_CLSID			 = 72,
##  VT_VERSIONED_STREAM  = 73,
##  VT_BSTR_BLOB		 = 0xfff,
##  VT_VECTOR			= 0x1000,
##  VT_ARRAY			 = 0x2000,
##  VT_BYREF			 = 0x4000 };


