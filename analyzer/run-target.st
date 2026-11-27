"Run a recipe supplied by the study manifest, then analyze its metamodels."
| arguments outputPath recipePath analyzerPath reuse before models allModels selectedModels pendingModels currentModel phase escape writeFailure argumentAfter |
arguments := Smalltalk globals
	at: #FameRemoteEntityAnalysisInvocation
	ifAbsent: [ Error signal: 'Missing analysis invocation' ].
argumentAfter := [ :option | | index |
	index := arguments indexOf: option ifAbsent: [ Error signal: 'Missing argument: ', option ].
	arguments at: index + 1 ].
reuse := arguments includes: '--reuse'.
phase := 'initializing'.
outputPath := argumentAfter value: '--output'.
analyzerPath := argumentAfter value: '--analyzer'.
recipePath := reuse ifFalse: [ argumentAfter value: '--recipe' ].
escape := [ :value | | text | text := value ifNil: [ '' ] ifNotNil: [ value asString ]. '"', ((text copyReplaceAll: '"' with: '""') copyReplaceAll: String cr with: ' '), '"' ].
writeFailure := [ :exception | | file stack |
	stack := [ String streamContents: [ :stream |
		exception signalerContext stack do: [ :context | | receiver |
			receiver := context receiver.
			stream nextPutAll: context method printString;
				nextPutAll: ' on '; nextPutAll: receiver class name.
			(receiver isKindOf: MCMethodDefinition) ifTrue: [
				stream nextPutAll: ' ('; nextPutAll: receiver className;
					nextPutAll: '>>'; nextPutAll: receiver selector asString; nextPut: $) ].
			stream nextPutAll: ' <- ' ] ] ]
		on: Error do: [ :stackError | 'stack unavailable: ', stackError description ].
	file := outputPath asFileReference. file exists ifTrue: [ file delete ].
	file writeStreamDo: [ :stream |
		stream nextPutAll: '"record","modelClass","declaredPackage","declaredSubmetamodelPackages","metric","value","localEntity","localPackage","remoteEntity","remotePackage","property","type","typePackage"'; cr.
		stream nextPutAll: '"error","","","","exception",'; nextPutAll: (escape value: phase, ': ', exception class name, ': ', exception description, ' [', stack, ']'); nextPutAll: ',"","","","","","",""'; cr ] ].
[
	[
		phase := 'reading existing model selection'.
		models := Smalltalk globals at: #FameRemoteEntityAnalysisModels ifAbsent: [ #() ].
		reuse ifFalse: [
			phase := 'capturing model classes before loading the recipe'.
			before := MooseModel withAllSubclasses asSet.
			phase := 'loading the recipe'.
			recipePath asFileReference fileIn.
			phase := 'reading the recipe model selection'.
			models := Smalltalk globals at: #FameRemoteEntityAnalysisModels ifAbsent: [ #() ].
			models isEmpty ifTrue: [
				phase := 'discovering newly loaded model classes'.
				models := (MooseModel withAllSubclasses reject: [ :each | before includes: each ]) select: [ :each | each respondsTo: #metamodel ].
				phase := 'recording newly loaded model classes'.
				Smalltalk globals at: #FameRemoteEntityAnalysisModels put: (models collect: #name) ] ].
		"Include already-present dependency models so base-image models follow the same rule."
		phase := 'including dependency model classes'.
		allModels := MooseModel withAllSubclasses select: [ :each | each respondsTo: #metamodel ].
		selectedModels := OrderedCollection new.
		models do: [ :each |
			(Smalltalk globals at: each asString asSymbol ifAbsent: [ nil ]) ifNotNil: [ :modelClass |
				selectedModels add: modelClass ] ].
		pendingModels := selectedModels copy.
		[ pendingModels isEmpty ] whileFalse: [
			currentModel := pendingModels removeFirst.
			(currentModel respondsTo: #allSubmetamodelsPackagesNames) ifTrue: [
				currentModel allSubmetamodelsPackagesNames do: [ :packageName |
					allModels do: [ :candidate |
						(candidate package name asString = packageName asString and: [ (selectedModels includes: candidate) not ]) ifTrue: [
							selectedModels add: candidate.
							pendingModels add: candidate ] ] ] ] ].
		models := selectedModels collect: #name.
		Smalltalk globals at: #FameRemoteEntityAnalysisModels put: models.
		models isEmpty ifTrue: [ Error signal: 'The recipe did not provide or load any metamodel' ].
		phase := 'running the Fame analysis'.
		Smalltalk globals at: #FameRemoteEntityAnalysisArguments put: { '--output'. outputPath }.
		analyzerPath asFileReference fileIn.
		phase := 'finishing the Fame analysis'.
		Smalltalk snapshot: true andQuit: true
	] on: Warning do: [ :exception |
		writeFailure value: exception.
		Smalltalk snapshot: false andQuit: true ]
] on: Exception do: [ :exception |
	(exception isResumable)
		ifTrue: [ exception resume ]
		ifFalse: [
			writeFailure value: exception.
			Smalltalk snapshot: false andQuit: true ] ].
