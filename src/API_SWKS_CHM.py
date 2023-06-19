# This script parses a Solidworks CAD help file into an XML file that identifies the COM variant type associated with the function inputs/outputs.
# This is required for Python integration with the Solidworks API as the VARIANT types in the COM tlb library are underspecified.
# The help files are unpacked from the API *.chm help file distributed with the software.

# TODO: check byrefs, pointers, pointerstopointers,
# beautifulsoup4 installed via "pip3.4 install beautifulsoup4" in cmd terminal
from bs4 import BeautifulSoup, NavigableString, Comment
#from bs4 import SoupStrainer
import os # issues with shadowing open()

# hardcoded directory structures
# note weird Unicode translation fail with \U in C:\Users.. use \\ or r"string"
#swDir = r"C:\Users\Foobert\Desktop\PY_DELL2\SW2010_SP0.0_R\Body2"
#cadDir = r"C:\Users\Foobert\Desktop\PY_DELL2\SWKS_help_XML\SW2010_SP0.0_R\MouseEvents"
#cadDir = r"C:\Users\Foobert\Desktop\PY_DELL2\SWKS_help_XML\SW2010_SP0.0_R\SplitLineFeatureData"

cadDir = r"C:\Users\Foobert\Desktop\PY_DELL2\SWKS_help_XML\SW2010_SP0.0_R"
WORKDir =  r"C:\Users\Foobert\Desktop\PY_DELL2\SWKS_help_XML\API_doc_parse\API_data"

import xml.etree.ElementTree as ET
CAD_XMLtable = ET.Element('CAD_XMLtable_02')
CAD_API = ET.SubElement(CAD_XMLtable, 'apiSet', name = 'SolidWorks2010')

import re, string
LPDISPATCHre = re.compile(r'\bLP[A-Z2-9]+\b', re.IGNORECASE)
dispatchRe = re.compile( r'\bface\d?s?\b|\bedges?\b', re.IGNORECASE)
arrayRe = re.compile( r'\barray\b|\bsafearray\b', re.IGNORECASE)
isValidHTML = re.compile( r'\b([a-z0-9_]+)\.(html?)\b', re.IGNORECASE)
isHTMLcomment = re.compile( r'<!--.*-->')
isHTMLdoctype = re.compile( r'HTML PUBLIC "-//W3C//DTD HTML 4.0 Frameset//EN"')
#swTypeRe = re.compile( r'\(\b([A-Za-z_]+)\b\)')
#swInputRe = re.compile( r'Input:', re.IGNORECASE)
#swOutputRe = re.compile( r'Output:', re.IGNORECASE)
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

unknownObject = []
unknownDispatch = []

# create a local corpus of method names, parameter names, unique helpstring words
methodNames = []
paramNames = []
helpStringCorpus = [] # dump it all in, convert to a set later
typePosition = {}
dump = []
CSVoutput = []
Verbose = False #True
modelSentence = ''
SS_methodNames = ''

NameObjectRe = re.compile( r'(\b\w+\b)\s(?:\bobject\b)', re.IGNORECASE)
ObjectList = []
APIstopwords = ['if', 'to', 'from', 'this', 'that', 'these',
 'those', 'are', 'be',  'have',  'has', 'do', 'does',
 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because',
 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about',
 'against', 'between', 'into', 'during', 'before', 'property', 'method',
 'after', 'above', 'below', 'to', 'from', 'again', 'further', 'then',
 'once', 'here', 'there', 'when', 'where', 'how', 'all', 'any',
 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
 'no', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
 'can', 'will', 'error', 'missing', 'successful', 'command', 'rhino',
 'rhinos', 'see', 'rhinoscript', 'example', 'onto', 'returned',
 'which', 'was', 'use', 'uses', 'used', 'identify', 'identified', 'you'
 'identifier', 'identifiers', 'specify', 'specified', 'it', 'SldWorks', 'sld', 'works']

def deCamel(camelCase):
	# strip camelcase format
	#import re
	camelCase = re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', camelCase)
	return camelCase

def testVTtype(s):
	#ArrayRe = re.compile( r'\barray\b|\bsafearray\b', re.IGNORECASE)
	#Array = ArrayRe.search(s)

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

for (root, dirs, files) in os.walk(cadDir, topdown=False):
	for APIname in files:
		if Verbose:
			print('Opening ' + APIname)
		#cadFullFilePath = os.path.join(root, APIname)
		cadFullFilePath = os.path.join(u'\\\\?\\' + root, APIname) # string added to bypass 256 character path limit in windows 7 OS

		#cadFullFilePath = os.path.join(r'C:\Users\Foobert\Desktop\PY_DELL2\SWKS_help_XML\SW2010_SP0.0_R\Annotation', 'Annotation__CheckSpelling.htm')
		#cadFullFilePath = os.path.join(r'C:\Users\Foobert\Desktop\PY_DELL2\SWKS_help_XML\SW2010_SP0.0_R\Annotation', 'Annotation__GetDisplayData.htm')
		#cadFullFilePath = os.path.join(root, 'Face2__Check.htm')
		#isValidHTML = re.compile( r'\b([a-z0-9_]+)\.(html?)\b', re.IGNORECASE)
		#isUnderscoreFreeHTML = re.compile( r'\b[A-Za-z0-9]+\b.htm?')

		if isValidHTML.search(APIname): # avoid gifs, etc
			#CAD_BS = BeautifulSoup(open(cadFullFilePath)) # are files getting closed??
			#CAD_BS = BeautifulSoup(os.open(cadFullFilePath, os.O_RDONLY)) # are files getting closed??
			#SW_bs = BeautifulSoup(open(swFullFilePath, os.O_RDONLY))# updated os.O_RDONLY flag APR15

			with open(cadFullFilePath) as FileHandle:
				CAD_BS = BeautifulSoup(FileHandle, "html.parser")
				# pip install --upgrade html5lib==1.0b8
				#CAD_BS = BeautifulSoup(FileHandle, "html5lib")

			dirName = root[len(cadDir)+1:]
			if not dirName:
				dirName = ''
			if Verbose:
				print(dirName)
			print('Extracting types from ' + APIname + ' in ' + dirName)

			comments = CAD_BS.findAll(text=lambda text:isinstance(text, Comment))
			[comment.extract() for comment in comments] # remove comment tag from bs tree

			for text in CAD_BS.findAll(['i', 'b', 'span', 'script', 'a']):
				text.unwrap()

			# strip script and style elements
			for script in CAD_BS(["script", "style"]):
				script.extract()

            # strip out human-readable text
			#helpStrings = [a for a in re.sub('[\t\n\xa0]+','\n', CAD_BS.getText()).split('\n') if a != ''] # strip newlines, tabs, empty strings
			#isHTMLcomment = re.compile( r'<!--.*-->')
			helpStrings = [tt.getText() for tt in CAD_BS.findAll(['h1', 'h3', 'p'])]
			helpStrings = [re.sub('[\t\n\xa0]+','', hS) for hS in helpStrings]
			helpStrings = list(filter(('').__ne__, helpStrings))
			helpStrings = [re.sub( '\s+', ' ', hS).strip() for hS in helpStrings if not isHTMLcomment.search(hS)]

			# issues with Solidworks text extraction
##			for text in CAD_BS.findAll(['i', 'b', 'span', 'script', 'a']):
##				text.unwrap()
##			t=CAD_BS.findAll(['h1', 'h3', 'p'])
##			helpStrings = []
##			for tt in t:
##				hs = ''
##				for ttt in tt.children:
##					if ttt.string:
##						#isHTMLcomment = re.compile( r'<!--.*-->')
##						if isHTMLcomment.search(' '.join(ttt.string.split())): #remove comments
##							print('GOTCHA---->'+' '.join(ttt.string.split()))
##							pass
##							#ttt.extract()
##						elif isHTMLdoctype.search(' '.join(ttt.string.split())):
##							print('GOTCHA---->'+' '.join(ttt.string.split()))
##							pass
##						else:
##							hs = hs + re.sub('\n', '', ttt.string)
##							hs = re.sub(' +', ' ', hs)
##							hs = re.sub('\xa0', '', hs)
##							hs = re.sub('\t', '', hs)
##				if (hs != ''):
##					helpStrings.append(hs)

			if Verbose:
				print('\n'.join(helpStrings))
				print('__________________________________________________________________________\n')

			dump = []
			[dump.append(re.findall('[\w\-\_]+', line)) for line in helpStrings] # split into seperate words
			dump = [s for ss in dump for s in ss] # remove sub-lists
			dump = ' '.join(dump)
			helpStringCorpus.append(dump + '\n')
			#input(' return to continue')


##			# First pass: use regexp to catch all the object instances
##			for h in helpStrings:
##				if NameObjectRe.match(h):
##					[ObjectList.append(hh)for hh in NameObjectRe.findall(h) if hh not in ObjectList and hh not in APIstopwords]
##
##			# Second pass: detect architecture of objects via literal context proximity
##			punctuationExclude = set(string.punctuation)
##			for i_hsc, hsc in enumerate(helpStringCorpus):
##				# strip punctuation from sentences
##				hsc = ''.join(ch for ch in s if ch not in punctuationExclude)
##				for ol in ObjectList:
##					# rearrange as list of words, find position(s) of object name in string
##					if ol in hsc:
##						objectPosition = [ol in w for w in re.split("\W+", hsc)]
##						objectPosition = set([i_op for i_op, op in enumerate(objectPosition) if op])
##
##						# typePosition == {objectName:{helpStringCorpusLine: objectPosition}}
##						if ol in typePosition.keys():
##							typePosition[ol].update({i_hsc:objectPosition})
##						else:
##							typePosition.update({ol:{}})
##
##			# presumably faster to work on the set of types that have been identified

### seek set intersection combinations
### https://docs.python.org/2/library/itertools.html#recipes
##from itertools import combinations, chain
##def powerset(iterable):
##    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
##    s = list(iterable)
##    #from itertools import chain
##    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))

			# 'object::method'
			ObjectMethod = re.search( r'(\b\w+)::(\w+\b)', CAD_BS.title.string)
			if ObjectMethod:
				Object = ObjectMethod.group(1)
				Method = ObjectMethod.group(2)
				methodNames.append(deCamel(Method))
				SS_methodNames = SS_methodNames + deCamel(Method) + '\n'

				if Object not in ObjectList:
					ObjectList.append(Object)

				XMLtableObject = ET.SubElement(CAD_API, 'object', name = Object, category = dirName)
				#XMLtableObject = ET.SubElement(CAD_API, 'object', name = Object)
				XMLtableMethod = ET.SubElement(XMLtableObject, 'method', name = Method)

				if not 'Description' in helpStrings:
					MethodDescription = [] # clear from last page for possible Remarks
				else:
					if helpStrings.index('Description') + 1 < len(helpStrings):
						MethodDescription = helpStrings[helpStrings.index('Description') + 1]
						modelSentence = modelSentence + deCamel(Method) + ' ' + MethodDescription + '\n' #
						if 'Remarks' in helpStrings:
							if helpStrings.index('Remarks') + 1 < len(helpStrings):
								MethodDescription = MethodDescription + helpStrings[helpStrings.index('Remarks') + 1]
						XMLtableMethodDescription = ET.SubElement(XMLtableMethod, 'description')
						XMLtableMethodDescription.text = MethodDescription

				# import OLE Automation methods - cf. *.tlb extraction
				if 'Syntax (OLE Automation)' in helpStrings:
					if helpStrings.index('Syntax (OLE Automation)') + 1 < len(helpStrings):
						OLEsyntax = helpStrings[helpStrings.index('Syntax (OLE Automation)') + 1]
						if (helpStrings[helpStrings.index('Syntax (OLE Automation)') + 2] not in ['Input:', 'Output:', 'Return:', 'Syntax (COM)']):
							# occasional use of both VB and C++ syntax e.g. Face2__Check.htm
							# also catch case of no OLE interface, e.g. SplitLineFeatureData::IGetContours
							OLEsyntax = OLEsyntax + '\n\t' + helpStrings[helpStrings.index('Syntax (OLE Automation)') + 2]

						XMLtableOLEsyntax = ET.SubElement(XMLtableMethod, 'ole_syntax')
						XMLtableOLEsyntax.text = OLEsyntax + '\n'

				# import COM methods
				if 'Syntax (COM)' in helpStrings:
					if helpStrings.index('Syntax (COM)') + 1 < len(helpStrings):
						COMsyntax = helpStrings[helpStrings.index('Syntax (COM)') + 1]
						XMLtableCOMsyntax = ET.SubElement(XMLtableMethod, 'com_syntax')
						XMLtableCOMsyntax.text = COMsyntax + '\n'

				# test for multiple instances of Input/Output/Properties
				# Property is a referenced COM accessible parameter that is changed, (i.e. input AND output)
				for paramString in ['Property:', 'Input:', 'Output:', 'Return:']:
					if paramString in helpStrings:
						lastInstanceIndex = 0
						for instance in range(0, helpStrings.count(paramString)):
							instanceIndex = helpStrings.index(paramString, lastInstanceIndex + 1)
							param = helpStrings[instanceIndex + 1]
							paramNames.append(param)
							paramComment = helpStrings[instanceIndex + 2]
							if paramComment == '\xa0':
								paramComment = ''
							paramComment = re.sub('\n', '', paramComment)

							# regexp parameters via pointer notation

							#paramRe = re.compile( r'\(\b(\&?\**\w+\**)\s?\)\s*(\&?\**\w+)\b', re.IGNORECASE)
							# old ParamRe = re.compile( r'\(\b(\w+\b\*?\*?\&?)\).(\&?\*?\*?\w+)\b', re.IGNORECASE)
							paramFields = paramRe.search(param)
							if not paramFields:
								print(" regexp ParamRe fail: "+param)
							else:
								paramName = paramFields.group(2) # strip out &,* paramName = re.search(r'\w+', paramName)
								paramType = paramFields.group(1)

							[VTtype, paramTypeString] = testVTtype(paramType)

							if not VTtype: # unrecognised object
								VTtype = 0x9
								#if Verbose:
								print('UNKNOWN type '+ paramName + ' in '+ str(CAD_BS.title.string))

							if (paramType == 'VARIANT') or (paramType == 'object'):
								[VTtype, paramTypeString] = testVTtype(paramComment)
								# try to identify known Dispatch pointer objects from description

								dispatch = dispatchRe.search(paramComment)
								if dispatch:
									VTtype = 0x9
									paramTypeString = str(dispatch.group(0)) + '-dispatch-pointer'
									if Verbose:
										print('Dispatch type '+ str(dispatch.group(0))+ ' in '+ str(CAD_BS.title.string))
								LPDISPATCH = LPDISPATCHre.search(paramComment)
								if LPDISPATCH:
									VTtype = 0x9
									paramTypeString = 'dispatch-'+ str(LPDISPATCH.group(0))
									if Verbose:
										print('LPDISPATCH type '+ str(LPDISPATCH.group(0))+ ' in '+ str(CAD_BS.title.string))

									if arrDispatchRe.search(paramComment):
										unknownDispatch.append(paramComment) #-------------------kaput?

								#if paramType == 'pointer':
								#	[VTtype, paramTypeString] = testVTtype(paramComment)
								#	# try to identify known pointer objects from description

								Object = ObjectRe.search(paramComment)
								if Object:
									VTtype = 0x9
									paramTypeString = 'pointer-to'+ str(Dispatch.group(1))
									if Verbose:
										print('pointer to object [ '+ paramComment + ' ] in '+ str(CAD_BS.title.string))



							arrayType = arrayRe.search(paramComment)
							if arrayType: # SafeArray detection happen outside testVTtype()
								# check for length of array - extract digits
								arrayLength = re.search(r'\b[0-9]+\b', paramComment) # check against actual comment
								if arrayLength:
									paramTypeString =  paramTypeString + '-' + 'array-of-' + arrayLength.group(0) # assumed safearray?
								else:
									paramTypeString = paramTypeString + '-array-of-unfixed-length' # assumed safearray?
								if VTtype:
									VTtype = VTtype + 0x2000

							# because pointer declaration can be (type*) variable, or (type) *variable
							# disambiguation is carried out here
							#
							if re.search(r'\w+\*',paramType) or re.search(r'\*\w+',paramName):
								#PtrPtrTo = re.search(r'\b\*\*\w+',s)
								if VTtype:
									VTtype = VTtype + 0x4000
								paramTypeString = 'pointer-to-' + paramTypeString
								#print("Please check pointer to pointer.. always array of Dispatch/COM objects?: "+s)
								#if PtrPtrTo: # cannot distinguish between "pointer to" and "pointer to pointer to"?

							if not VTtype:
								#print('UNKNOWN type '+ paramName + ' in '+ str(CAD_BS.title.string))
								print('No VTtype determined for ' + Method + ' : ' + paramName)


									##http://help.solidworks.com/2014/english/api/sldworksapiprogguide%5Coverview%5Csafearray_template_class.htm
									##//common array types
									##typedef SafeArray<VARIANT_BOOL, VT_BOOL>		SafeBooleanArray;
									##typedef SafeArray<double,	   VT_R8>		  SafeDoubleArray ;
									##typedef SafeArray<long,		 VT_I4>		  SafeLongArray ;
									##typedef SafeArray<BSTR,		 VT_BSTR>		SafeBSTRArray ;
									##typedef SafeArray<LPDISPATCH,   VT_DISPATCH>	SafeDISPATCHArray;
									##typedef SafeArray<LPVARIANT,	VT_VARIANT>	 SafeVARIANTArray;
									##V_VT(m_input) = VT_ARRAY | type;

							for s in helpStrings: # replace malformed strings
								if COMre.search(s):
									helpStrings[helpStrings.index(s)] = 'Syntax (COM)'
								if OLEre.search(s):
									helpStrings[helpStrings.index(s)] = 'Syntax (OLE Automation)'

							# determine if after OLE declaration and before COM declaration, or after COM declaration
							if ('Syntax (COM)' not in helpStrings) and ('Syntax (OLE Automation)' not in helpStrings):
								print('NO COM/OLE DEFINED IN '+ str(CAD_BS.title.string))
							elif (instanceIndex < helpStrings.index('Syntax (COM)') and instanceIndex > helpStrings.index('Syntax (OLE Automation)')) or \
								(instanceIndex > helpStrings.index('Syntax (OLE Automation)') and 'Syntax (COM)' not in helpStrings):
								#XMLtable_parm = ET.SubElement(XMLtableOLEsyntax, paramString[0:-1], name = paramName, variant = str(VTtype))
								#XMLtableParam = ET.SubElement(XMLtableOLEsyntax, paramString[0:-1], name = paramName, optional = "Required", variant = str(VTtype), vartype = paramType)
								XMLtableParam = ET.SubElement(XMLtableOLEsyntax, paramString[0:-1].lower(), name = paramName.lower(), optional = "required", variant = str(VTtype), vartype = paramTypeString)
							elif (instanceIndex > helpStrings.index('Syntax (COM)') and instanceIndex > helpStrings.index('Syntax (OLE Automation)')) or \
								(instanceIndex > helpStrings.index('Syntax (COM)') and 'Syntax (OLE Automation)' not in helpStrings):
								#XMLtable_parm = ET.SubElement(XMLtableCOMsyntax, paramString[0:-1], name = paramName, type = str(VTtype))
								XMLtableParam = ET.SubElement(XMLtableCOMsyntax, paramString[0:-1].lower(), name = paramName.lower(), optional = "required", variant = str(VTtype), vartype = paramTypeString)
							else:
								print('Unknown syntax of '+paramString[0:-1]+' in file '+ name)
							XMLtableParam.text = paramComment
							lastInstanceIndex = instanceIndex

				# attach implementation remarks
				if 'Remarks' in helpStrings:
					if helpStrings.index('Remarks') + 1 < len(helpStrings):
						remarks = helpStrings[helpStrings.index('Remarks') + 1]
						if remarks == '\xa0':
							remarks = ''
						remarks = re.sub('\n', '', remarks)

						XMLtableRemarks = ET.SubElement(XMLtableMethod, 'remarks')
						XMLtableRemarks.text = remarks


				if Verbose:
					XMLtable_bs = BeautifulSoup(ET.tostring(XMLtableMethod, method='html'))
					print(XMLtable_bs.prettify())
					print('-----------------------------------------------')



#____________________________________________________________________________________________________________________
				if MethodDescription:
					MethodDescriptionLine = re.search(r'[\s\S]+\.?', MethodDescription)
					if Object is None:
						Object = ''
					else:
						Object = Object + '.'
					if MethodDescriptionLine and Object != [] and Method != []:
						MethodDescriptionLine = MethodDescriptionLine.group(0)
						CSVoutput.append(
						# dirName + '\t ' +
						Object + Method + '\t ' +
						OLEsyntax.splitlines()[0].split(r'= ')[-1] + '\t ' +
						MethodDescriptionLine + '\n') # comments in syntax field, use tab delimiter
						# forgot discrimination between OLEsyntax and VBsyntax in this case
					else:
						CSVoutput.append(dirName + '\t ' + OLEsyntax.splitlines()[0].split(r'= ')[-1] + '\n') # comments in syntax field, use tab delimiter

with open(os.path.join(WORKDir, 'swksAPI_1.csv'), 'w', encoding='utf8') as CSVfile:
	dummy = [CSVfile.write(CSVo) for CSVo in CSVoutput] # dummy => silent output
	CSVfile.close()


exit(0)
#____________________________________________________________________________________________________________________


XMLtable_bs = BeautifulSoup(ET.tostring(CAD_XMLtable))
with open(os.path.join(WORKDir, 'swksIntermediate_A0.xml'), 'w', encoding='utf8') as XMLfile:
	XMLfile.write(XMLtable_bs.prettify())

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
##with open(os.path.join(WORKDir, 'swksIntermediate_B0.xml'), 'wb') as XMLfile:
##	XMLfile.write(ET.tostring(CAD_XMLtable))#, xml_declaration=True, encoding='utf-8', method="xml"
##	XMLfile.close()
##
##with open(os.path.join(WORKDir, 'swksIntermediate_C0.xml'), 'w', encoding='utf8') as XMLfile:
##	XMLfile.write(bytes.decode(ET.tostring(CAD_XMLtable)))#, xml_declaration=True, encoding='utf-8', method="xml"
##	XMLfile.close()

SS_methodNames = SS_methodNames.lower()
SS_methodNames = re.sub(r'[0-9]\b', r'', SS_methodNames) # strip out numbers
SS_methodNames = re.sub(r'\bi\s+\b', r'', SS_methodNames) # strip out IDispatch prefix
##with open(os.path.join(WORKDir, 'SolidworksAPI_methodNames.txt'), 'w', encoding='utf8') as methodNamesFile:
##	methodNamesFile.write(SS_methodNames)
##	methodNamesFile.close()

modelSentence = re.sub('-', ' ', modelSentence) # sort out hyphenation
modelSentence = re.sub('[%s]' % re.escape(string.punctuation), '', modelSentence.lower()) # strip punctuation and convert to lowercase
##with open(os.path.join(WORKDir, 'SolidworksAPI_w2v.txt'), 'w', encoding='utf8') as word2vecFile:
##	word2vecFile.write(modelSentence)
##	word2vecFile.close()

import pickle
##pickle.dump(paramNames, open(os.path.join(WORKDir, 'paramNames.p'), 'wb'))
##pickle.dump(methodNames, open(os.path.join(WORKDir, 'methodNames.p'), 'wb'))

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

