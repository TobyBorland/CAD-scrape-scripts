# This program parses an unzipped *.chm help file associated with a CAD program into an XML file that parses detailed type/function information
# associated with the function inputs/outputs. (Rhinoscript.chm)
# Built on earlier Solidworks script to extract detailed VARIANT specifications not listed in sldworks.tlb for use with win32com

# TODO: check byrefs, pointers, pointerstopointers,
# beautifulsoup4 installed via "pip3.4 install beautifulsoup4" in cmd terminal
from bs4 import BeautifulSoup, NavigableString, Comment
#from bs4 import SoupStrainer
import os # issues with shadowing open()

# note weird Unicode translation fail with \U in C:\Users.. use \\ or r"string"
#cadDir = r"C:\Users\Foobert\Desktop\PY_DELL2\Rhino_help_XML\Toolbar_Methods"
cadDir = r"C:\Users\Foobert\Desktop\PY_DELL2\Rhino_help_XML"
WORKDir =  r"C:\Users\Foobert\Desktop\PY_DELL2\Rhino_help_XML\API_doc_parse\API_data"

import xml.etree.ElementTree as ET
CAD_XMLtable = ET.Element('CAD_XMLtable_01')
CAD_API = ET.SubElement(CAD_XMLtable, 'apiSet', name = 'Rhinoscript')

import re, string
# handpicked list of Rhino geometrical objects
# useful to get correspondence with CATIA, SolidWorks equivalent etc.
# (extract all comments & description, test for semantic similarity with Wordnet corpus for geometry)
geometricalGUIDobjects = ['surface', 'mesh', 'meshes', 'face', 'vector', 'line', 'point', 'curve', 'polyline', 'knot', 'cloud', 'plane', 'surfaces', 'faces', 'vectors', 'lines', 'points', 'curves', 'polylines', 'knots', 'planes']
geometricalGUIDobjectRe = re.compile(r'\b%s\b' % '\\b|\\b'.join(geometricalGUIDobjects), flags=re.IGNORECASE)
geometricalXYZobjects = ['number', 'direction', 'meshes', 'face', 'vector', 'line', 'point', 'curve', 'polyline', 'knot', 'cloud', '3-D', 'plane', 'UV']
#nonGeometricalXYZobjects = ['matrix']
#arrayNumberIndicators = ['matrix', 'weight', ]
geometricalXYZobjectRe = re.compile(r'\b%s\b' % '\\b|\\b'.join(geometricalXYZobjects), flags=re.IGNORECASE)
# note point input is [x, y, z], but identifier is GUID
nonGeometricalStringObjects = ['path', 'view', 'text', 'hatch', 'layer', 'light', 'material']
nonGeometricalStringObjectRe =  re.compile(r'\b%s\b' % '\\b|\\b'.join(nonGeometricalStringObjects), flags=re.IGNORECASE)
isHTMLcomment = re.compile( r'<!--.*-->')


# create a local corpus of method names, parameter names, unique helpstring words
methodNames = []
descriptionText = []
paramNames = []
modelSentence = ''
helpStringCorpus = '' # dump it all in, convert to a set later
dump = []
CSVoutput = []
Verbose = False
SS_methodNames = ''

def deCamel(camelCase):
	# strip camelcase format
	import re
	camelCase = re.sub(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))', r' \1', camelCase)
	return camelCase

for (root, dirs, files) in os.walk(cadDir, topdown=False):
	for APIname in files:
		cadFullFilePath = os.path.join(root, APIname)
		isValidHTML = re.compile( r'\b([a-z0-9_]+)\.(html?)\b', re.IGNORECASE)
		isUnderscoreFreeHTML = re.compile( r'\b[A-Za-z0-9]+\b.htm?')
		if (isValidHTML.search(APIname) and isUnderscoreFreeHTML.search(APIname)): # avoid gifs, etc
			CAD_BS = BeautifulSoup(open(cadFullFilePath), 'html.parser') # is lxml having problems with strings?
			 # are files getting closed??
			#SW_bs = BeautifulSoup(open(swFullFilePath, os.O_RDONLY))# updated os.O_RDONLY flag APR15
			comments = CAD_BS.findAll(text=lambda text:isinstance(text, Comment))
			[comment.extract() for comment in comments] # remove comment tag from SW_bs tree
			for text in CAD_BS.findAll(['i', 'b', 'span', 'script', 'a']):
				text.unwrap()
			t=CAD_BS.findAll(['h1', 'h3', 'p'])
			helpStrings = []
			for tt in t:
				hs = ''
				for ttt in tt.children:
					if ttt.string:
						#isHTMLcomment = re.compile( r'<!--.*-->')
						if isHTMLcomment.search(' '.join(ttt.string.split())): #remove comments
							pass
							#ttt.extract()
						else:
							hs = hs + re.sub('\n', '', ttt.string)
							hs = re.sub(' +', ' ', hs)
							hs = re.sub('\xa0', '', hs)
							hs = re.sub('\t', '', hs)
							#hs = re.sub('  ', ' ', hs)
				helpStrings.append(hs)

			helpStrings = list(filter(('').__ne__, helpStrings))
			if Verbose:
				print('\n'.join(helpStrings))
				print('__________________________________________________________________________\n')

			dump = []
			[dump.append(re.findall('[\w\-\_]+', line)) for line in helpStrings] # split into seperate words
			dump = [s for ss in dump for s in ss] # remove sub-lists
			dump = ' '.join(dump)
			helpStringCorpus = helpStringCorpus + ' ' + dump
			#input(' return to continue')

			rhinoFunction = CAD_BS.title.string
			methodNames.append(deCamel(rhinoFunction)) #
			SS_methodNames = SS_methodNames + deCamel(rhinoFunction) + '\n'

			if rhinoFunction == 'AddCone':
				pass

			dirName = root[len(cadDir)+1:]
			if not dirName:
				dirName = ''
			if Verbose:
				print(dirName)
			print(' Extracting types from ' + APIname + ' in ' + dirName)

			XMLtableObject = ET.SubElement(CAD_API, 'object', name = 'Rhino', category = dirName) # Rhino has single parent object
			XMLtableMethod = ET.SubElement(XMLtableObject, 'method', name = rhinoFunction)

			if rhinoFunction.lower() in [h.lower() for h in helpStrings] and rhinoFunction not in helpStrings : # camelcase mistyping exception (HideToolbar)
				for h in helpStrings:
					if rhinoFunction.lower() == h.lower():
						rhinoFunction = h

			if rhinoFunction in helpStrings: # equivalent to "Description" heading
				if helpStrings.index(rhinoFunction) + 1 < len(helpStrings):
					MethodDescription = helpStrings[helpStrings.index(rhinoFunction) + 1]
					XMLtableMethodDescription = ET.SubElement(XMLtableMethod, 'description')
					XMLtableMethodDescription.text = MethodDescription
					descriptionText.append(MethodDescription)
					modelSentence = modelSentence + deCamel(rhinoFunction) + ' ' + MethodDescription + '\n' #


##				if 'Remarks' in helpStrings:
##					if helpStrings.index('Remarks') + 1 < len(helpStrings):
##						swMethodRemarks = helpStrings[helpStrings.index('Remarks') + 1]
##						swXMLtableMethodRemarks = ET.SubElement(swXMLtableMethod, 'remarks')
##						swXMLtableMethodRemarks.text = swMethodRemarks

##				# get OLE Automation methods - cf. *.tlb extraction
##				if 'Syntax (OLE Automation)' in helpStrings:
##					if helpStrings.index('Syntax (OLE Automation)') + 1 < len(helpStrings):
##						swOLEsyntax = helpStrings[helpStrings.index('Syntax (OLE Automation)') + 1]
##						swXMLtableOLEsyntax = ET.SubElement(swXMLtableMethod, 'ole_syntax')
##						swXMLtableOLEsyntax.text = swOLEsyntax

			# get OLE Automation methods - cf. *.tlb extraction
			if 'Syntax' in helpStrings:
				if helpStrings.index('Syntax') + 1 < len(helpStrings):
					if not 'Parameters' in helpStrings:
						print('No \'Parameters\' field in ' + rhinoFunction)

					elif helpStrings[helpStrings.index('Syntax') + 2] == 'Parameters':
						XMLtableOLEsyntax = ET.SubElement(XMLtableMethod, 'ole_syntax')
						OLEsyntax = helpStrings[helpStrings.index('Syntax') + 1]
						XMLtableOLEsyntax = ET.SubElement(XMLtableMethod, 'ole_syntax')
						XMLtableOLEsyntax.text = OLEsyntax + '\n'
						rhinoFunctionSanity = re.search(r'\b(?:Rhino.)(\w+)', OLEsyntax)
						if rhinoFunctionSanity:
							rhinoFunctionSanity = rhinoFunctionSanity.group(1)
							if rhinoFunctionSanity != rhinoFunction:
								print('Mismatch of function name: ' + rhinoFunction + ', ' + rhinoFunctionSanity)

					else: # weird case of multiple syntaxes
						XMLtableOLEsyntax = ET.SubElement(XMLtableMethod, 'ole_syntax')
						XMLtableOLEsyntax.text = ''
						for instance in range(helpStrings.index('Syntax') + 1, helpStrings.index('Parameters')):
							OLEsyntax = helpStrings[instance]
							rhinoFunctionSanity = re.search(r'\b(?:Rhino.)(\w+)', OLEsyntax)
							if rhinoFunctionSanity:
								XMLtableOLEsyntax.text = XMLtableOLEsyntax.text + OLEsyntax + '\n'

##				# import COM methods
##				if 'Syntax (COM)' in helpStrings:
##					if helpStrings.index('Syntax (COM)') + 1 < len(helpStrings):
##						swCOMsyntax = helpStrings[helpStrings.index('Syntax (COM)') + 1]
##						swXMLtableCOMsyntax = ET.SubElement(swXMLtableMethod, 'com_syntax')
##						swXMLtableCOMsyntax.text = swCOMsyntax

			# test for multiple instances of Parameters/Returns, note Rhinoscript limits return to an equivalent of HRESULT
			if 'Parameters' in helpStrings:
				if not 'Returns' in helpStrings:
					print('No \'Returns\' field in '+rhinoFunction)
				else:
					for instance in range(helpStrings.index('Parameters') + 1, helpStrings.index('Returns') - 1, 2):

					# in Rhino, format is:
					# 'Parameters'
					# parameterName 1
					# isParameterOptional. parameterType. parameterComment
					# parameterName N
					# isParameterOptional. parameterType. parameterComment

						paramName = helpStrings[instance] # str* reveals object GUID
						paramNames.append(paramName)
						paramFields = helpStrings[instance + 1]
						#if paramFields == '\xa0':
						#	paramFields = ''
						#paramFields = re.sub('\n', '', paramFields)
						#if APIname == 'PointDivide.htm':
							#check weird case
							#print('PointDivide.htm')
							#input('check')

						# Second level description e.g. AddObjectMesh 'Value', 'Description'
						rhinoParamFields = re.search(r'\b(\w+)\.[\s]*\b(\w+)\..[\s]*([\s\n\S]+)', paramFields)
						if not rhinoParamFields:
							# test for a set of numbers specifying control options
							rhinoSubParamNumberField = re.search( r'\b[\d]+\b', paramName)
							rhinoSubParamBooleanField = re.search( r'\bTrue|False\b', paramName)
							if rhinoSubParamBooleanField:
								paramComment = paramFields
								XMLtableSubParam = ET.SubElement(XMLtableParam, 'input-subset', name = paramName, vartype = paramType, optional = paramOptional)
								XMLtableSubParam.text = paramComment
							elif rhinoSubParamNumberField:
								paramComment = paramFields
								XMLtableSubParam = ET.SubElement(XMLtableParam, 'input-subset', name = paramName, vartype = paramType, optional = paramOptional)
								XMLtableSubParam.text = paramComment
							else:
								if not paramFields == 'Description':
									print(" regexp rhinoSubParamNumberField fail: " + dirName + '-' + rhinoFunction + ' - ' + paramFields)
									print('\n')
									#input('check')

						else:
							paramOptional = rhinoParamFields.group(1)
							paramType = rhinoParamFields.group(2)
							paramComment = rhinoParamFields.group(3)
							if paramType == 'Number':
								# determine is integer or double/float from Rhino naming convention
								if paramName[0:3] == 'int':
									paramType = 'integer'
								elif (paramName[0:3] == 'dbl' or paramName[0:3] == 'dlb'):
									paramType = 'double'
								elif paramName[0:3] == 'bln': # boolean is 0, >0 in CheckNewObjects?
									paramType = 'boolean'
								elif paramName[0:3] == 'lng': # long used for colour
									paramType = 'long'
								else:
									print('Unidentified Number type: '+paramName)
							if paramType == 'Array':
								# require variable subType
								isGeom = geometricalGUIDobjectRe.search(paramComment)
								isNonGeom = nonGeometricalStringObjectRe.search(paramComment)
								stringRe = re.compile( r'\bstrings?\b|\bBSTR\b', re.IGNORECASE)
								isString = stringRe.search(paramComment)
								numberRe = re.compile( r'\bnumbers?\b', re.IGNORECASE)
								isNumber = numberRe.search(paramComment)
								booleanRe = re.compile( r'\bBOOLE?A?N?\b', re.IGNORECASE)
								isBoolean = booleanRe.search(paramComment)
								pointXYZre = re.compile(r'\bpoint\b',  flags=re.IGNORECASE)
								isSinglePoint = pointXYZre.search(paramComment)
								pluralPointXYZre = re.compile(r'\bpoints\b',  flags=re.IGNORECASE)
								isPluralPoint = pluralPointXYZre.search(paramComment) # required for XYZ array within points array
								if isSinglePoint:
									paramType = 'single-xyz-array'
								elif isPluralPoint:
									paramType = 'multiple-xyz-array'
								elif isString:
									if isGeom and not isNonGeom:
										paramType = 'geometrical-string-array'
									elif isNonGeom and not isGeom:
										paramType = 'nongeometrical-string-array'
									else:
										paramType = 'unknown-string-array'
										print('Unknown string array type: '+paramName+', '+paramFields+', '+paramComment)
								elif isNumber:
									paramType = 'number-array' # geom, non-geom?
									# check is subarrays of XYZ, or plane of, 3-D vector
								elif isBoolean:
									paramType = 'boolean-array'
								elif isGeom:
									paramType = 'geometrical-string-array'
									print('Underdefined Geom string array type: '+paramName+', '+paramFields+', '+paramComment)
								elif isNonGeom:
									paramType = 'nongeometrical-string-array'
									print('Underdefined NonGeom string array type: '+paramName+', '+paramFields+', '+paramComment)
								else:
									paramType = 'unknown-type-array'
									print('Unknown array type: '+paramName+', '+paramFields+', '+paramComment)

								# check for length of array - extract digits
								arrayLength = re.search(r'\b[0-9]+\b', paramComment) # check against actual comment
								if arrayLength:
									paramType =  paramType + '-of-' + arrayLength.group(0) # assumed safearray?
								else:
									paramType = paramType + '-of-unfixed-length' # assumed safearray?
								#if VTtype:
									#VTtype = VTtype + 0x2000


							XMLtableParam = ET.SubElement(XMLtableOLEsyntax, 'input', name = paramName, vartype = paramType, optional = paramOptional)
							XMLtableParam.text = paramComment


			if 'Returns' in helpStrings:
				if not 'Example' in helpStrings:
					print('No \'Example\' field in '+rhinoFunction)
				else:
					for instance in range(helpStrings.index('Returns') + 1, helpStrings.index('Example') - 1, 2):

						# in Rhino, return format is:
						# 'Returns'
						# parameterType
						# parameterComment
						# NULL
						# HRESULT fail parameterComment

						paramName = 'missing'
						paramType = helpStrings[instance]
						paramComment = helpStrings[instance + 1]
						if ('error' in paramComment) and (paramType != 'Null'):
							print(' Default error check - '+paramComment+', '+paramType+'\n')
						paramOptional = 'Optional' # if result can return NULL on error
						XMLtableParam = ET.SubElement(XMLtableOLEsyntax, 'output', name = paramName, vartype = paramType, optional = paramOptional)
						XMLtableParam.text = paramComment


			
			if Verbose:
				XMLtable_bs = BeautifulSoup(ET.tostring(XMLtableMethod, method='html'))
				print(XMLtable_bs.prettify())
				print('\n__________________________________________________________________________\n')
			MethodDescriptionLine = re.search(r'[\s\S]+\.?', MethodDescription)
			if MethodDescriptionLine:
				MethodDescriptionLine = MethodDescriptionLine.group(0)
				CSVoutput.append(dirName + '\t ' + OLEsyntax[6:] + '\t ' + MethodDescriptionLine + '\n') # comments in syntax field, use tab delimiter
			else:
				CSVoutput.append(dirName + '\t ' + OLEsyntax[6:] + '\n') # comments in syntax field, use tab delimiter

helpStringCorpus = re.sub("[^\w]", " ",  helpStringCorpus).split()
helpStringCorpus = list(set(helpStringCorpus))
for mN in methodNames:
	for pN in paramNames:
		if pN in helpStringCorpus:
			helpStringCorpus.remove(pN)
	for hsc in helpStringCorpus:
		if re.search("[0-9]+", hsc):
			helpStringCorpus.remove(hsc)

import pickle
# pickle.dump(helpStringCorpus, open(os.path.join(WORKDir, 'helpStringCorpus.p'), 'wb'))
# pickle.dump(methodNames, open(os.path.join(WORKDir, 'methodNames.p'), 'wb'))
# pickle.dump(paramNames, open(os.path.join(WORKDir, 'paramNames.p'), 'wb'))

paramNamePrefix = []
paramNameTypes = []
for pN in paramNames:
	if len(pN) > 3:
		if str.isupper(pN[3]):
			paramNamePrefix.append(pN[:3])
			paramNameTypes.append(pN[3:])

paramNamePrefix = list(set(paramNamePrefix))
#print(paramNamePrefix)
paramNameTypes = list(set(paramNameTypes))
#print(paramNameTypes)

pickle.dump(paramNamePrefix, open(os.path.join(WORKDir, 'paramNamePrefix.p'), 'wb'))
pickle.dump(paramNameTypes, open(os.path.join(WORKDir, 'paramNameTypes.p'), 'wb'))

# with open(os.path.join(WORKDir, 'rhinoscriptAPI.csv'), 'w', encoding='utf8') as CSVfile:
# 	dummy = [CSVfile.write(CSVo) for CSVo in CSVoutput] # dummy => silent output
# 	CSVfile.close()

#methodNames = list(set(methodNames))
#paramNames = list(set(paramNames))
#helpStringCorpus = list(set(helpStringCorpus))

SS_methodNames = SS_methodNames.lower()
SS_methodNames = re.sub(r'[0-9]\b', r'', SS_methodNames) # strip out numbers
SS_methodNames = re.sub(r'\bi\s+\b', r'', SS_methodNames) # strip out IDispatch prefix
# with open(os.path.join(WORKDir, 'RhinoAPI_methodNames.txt'), 'w', encoding='utf8') as methodNamesFile:
# 	methodNamesFile.write(SS_methodNames)
# 	methodNamesFile.close()

modelSentence = re.sub('-', ' ', modelSentence) # sort out hyphenation
modelSentence = re.sub('[%s]' % re.escape(string.punctuation), '', modelSentence.lower()) # strip punctuation and convert to lowercase
with open(os.path.join(WORKDir, 'rhinoscriptAPI_w2v.txt'), 'w', encoding='utf8') as word2vecFile:
	word2vecFile.write(modelSentence)
	word2vecFile.close()

#XMLtable_bs = BeautifulSoup(ET.tostring(CAD_API, method='html')) # malformed XML closing braces on <input>
XMLtable_bs = BeautifulSoup(ET.tostring(CAD_XMLtable))
# with open(os.path.join(WORKDir, 'rhinoIntermediate_A0.xml'), 'w', encoding='utf8') as XMLfile:
# 	XMLfile.write(XMLtable_bs.prettify())
# 	XMLfile.close()

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
# with open(os.path.join(WORKDir, 'rhinoIntermediate_B0.xml'), 'wb') as XMLfile:
# 	XMLfile.write(ET.tostring(CAD_XMLtable))#, xml_declaration=True, encoding='utf-8', method="xml"
# 	XMLfile.close()

with open(os.path.join(WORKDir, 'rhinoIntermediate_D0.xml'), 'w', encoding='utf8') as XMLfile:
	XMLfile.write(bytes.decode(ET.tostring(CAD_XMLtable)))#, xml_declaration=True, encoding='utf-8', method="xml"
	XMLfile.close()

# second level of variable type intrerpretation required, e.g. 'array of string' is collection of objects

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

# def testCADtype(s):
	# #arrayRe = re.compile( r'\barray\b|\bsafearray\b', re.IGNORECASE)
	# #array = arrayRe.search(s)
	# stringRe = re.compile( r'\bstrings?\b|\bBSTR\b', re.IGNORECASE)
	# string = stringRe.search(s) # C types
	# shortRe = re.compile( r'\bshorts?\b', re.IGNORECASE)
	# short = shortRe.search(s)
	# intRe = re.compile( r'\bints?\b', re.IGNORECASE)
	# int = intRe.search(s)
	# longRe = re.compile( r'\blongs?\b', re.IGNORECASE)
	# long = longRe.search(s)
	# floatRe = re.compile( r'\bfloats?\b', re.IGNORECASE)
	# float = floatRe.search(s)
	# doubleRe = re.compile( r'\bdoubles?\b', re.IGNORECASE)
	# double = doubleRe.search(s)

	# VARIANT = re.search(r'\bVARIANT\b', s)
	# VARIANT_BOOL = re.search(r'\bVARIAN?T?_BOOLE?A?N?\b', s)
	# BOOL = re.search(r'\bBOOLE?A?N?\b', s)
	# HRESULT = re.search(r'\bHRESULT\b', s)
	# LPDISPATCH = re.search(r'\bLP[A-Z2-9]+\b', s)
	# #http://www.quickmacros.com/help/Tables/IDP_VARIANT.html
	# pointerTo = re.search(r'\b\*\w+',s)
	# ptrPtrTo = re.search(r'\b\*\*\w+',s)

	# VT = None
	# if VARIANT:
		# VT = 0xC # VARIANT is replaced by other type in subsequent search, relevant to comment parsing
	# if short:
		# VT = 0x2
	# if int or long:
		# VT = 0x3
	# if float:
		# VT = 0x4
	# if double:
		# VT = 0x5
	# if string:
		# VT = 0x8 # VT_BSTR
	# if LPDISPATCH: # acess to underlying IDispatch pointer
		# VT = 0x9
	# if VARIANT_BOOL or swBOOL:
		# VT = 0xB
		# print("VARIANT_BOOL or BOOL?: "+s)
	# if HRESULT:
		# VT = 0x19
	# #if Array: # is it possible to identify between safearray (0x27) and C style array (0x28)
	# #	VT = 0x27
	# if pointerTo:
		# VT = VT + 0x4000
	# if ptrPtrTo: # cannot distinguish between "pointer to" and "pointer to pointer to"?
		# VT = VT + 0x4000
		# print("Please check pointer to pointer.. always array of Dispatch/COM objects?: "+s)
	# if not VT:
		# print('Unknown type (testSWtype): '+s)
	# return VT


##S1=CAD_BS.find("h3", text="Syntax")
##S2=CAD_BS.find("h3", text="Returns")
##codeStrings = []
##Sn = S1.nextSibling
##while Sn != S2:
##	if (Sn != '\n')and(Sn.string != []):
##		codeStrings.append(Sn.string)
##	Sn = Sn.nextSibling
##
##for section in CAD_BS.find_all('h3'):
##	header3 = section.find_all(text=True)[0].split('.')
##	content = u""
##	for p in section.find_next_siblings():
##		if p.name == 'h3':
##			break
##
##		if p.span:
##			p.span.unwrap()  # ... remove 'span' tags
##
##		del p['class'] # ... delete paragraph class
##		content += unicode(p).replace("n", u' ') # newline characters -> Unicode
##		content += '<br/>'  # Newline tag to properly separate paragraphs
##
##	entries.append({ 'header': header, 'content': content}) # Add new header plus its content into array
##
##print(entries)
