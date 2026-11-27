"Measure the reuse of Fame metamodels.
Run: pharo-vm image st --quit analyzer/measure.st --output report.csv [ModelClass ...]"

| arguments outputPath outputFile modelNames escape writeRow metricRow analyze reportFailure discoveredModels fromTargetLoader |
arguments := ((Smalltalk globals includesKey: #FameRemoteEntityAnalysisArguments)
	ifTrue: [ Smalltalk globals at: #FameRemoteEntityAnalysisArguments ]
	ifFalse: [ Smalltalk arguments ]) asArray.
modelNames := OrderedCollection new.
fromTargetLoader := Smalltalk globals includesKey: #FameRemoteEntityAnalysisArguments.
fromTargetLoader
	ifTrue: [
		((arguments size < 2) or: [ arguments first ~= '--output' ]) ifTrue: [
			Error signal: 'Usage: measure.st --output report.csv [ModelClass ...]' ].
		outputPath := arguments second.
		3 to: arguments size do: [ :index | modelNames add: (arguments at: index) ] ]
	ifFalse: [
		((arguments size < 4) or: [ (arguments at: 3) ~= '--output' ]) ifTrue: [
			Error signal: 'Usage: measure.st --output report.csv [ModelClass ...]' ].
outputPath := arguments at: 4.
		5 to: arguments size do: [ :index | modelNames add: (arguments at: index) ] ].
outputFile := outputPath asFileReference.
modelNames ifEmpty: [
	discoveredModels := Smalltalk globals
		at: #FameRemoteEntityAnalysisModels
		ifAbsent: [ #() ].
	discoveredModels isEmpty
	ifTrue: [ modelNames add: 'FamixJavaModel' ]
	ifFalse: [ discoveredModels do: [ :each | modelNames add: each asString ] ] ].
"FAST-Core-Test-Model is test support, not a metamodel under study."
modelNames := modelNames reject: [ :modelName |
	| modelClass |
	modelClass := Smalltalk globals at: modelName asSymbol ifAbsent: [ nil ].
	modelClass notNil and: [ modelClass package name = 'FAST-Core-Test-Model' ] ].

escape := [ :value |
	| text |
	text := value ifNil: [ '' ] ifNotNil: [ value asString ].
	'"', ((text copyReplaceAll: '"' with: '""') copyReplaceAll: String cr with: ' '), '"' ].

reportFailure := [ :exception |
	outputFile exists ifTrue: [ outputFile delete ].
	outputFile writeStreamDo: [ :stream |
		writeRow := [ :fields |
			fields doWithIndex: [ :field :index |
				index > 1 ifTrue: [ stream nextPut: $, ].
				stream nextPutAll: (escape value: field) ].
			stream cr ].
		writeRow value: #(record modelClass declaredPackage declaredSubmetamodelPackages metric value localEntity localPackage remoteEntity remotePackage property type typePackage).
		writeRow value: { 'error'. ''. ''. ''. 'exception'. exception class name, ': ', exception description. ''. ''. ''. ''. ''. ''. '' } ] ].

[
outputFile exists ifTrue: [ outputFile delete ].
outputFile writeStreamDo: [ :stream |
	writeRow := [ :fields |
		fields doWithIndex: [ :field :index |
			index > 1 ifTrue: [ stream nextPut: $, ].
			stream nextPutAll: (escape value: field) ].
		stream cr ].
	writeRow value: #(record modelClass declaredPackage declaredSubmetamodelPackages metric value localEntity localPackage remoteEntity remotePackage property type typePackage).
	metricRow := [ :fields |
		writeRow value: { 'metric'. fields first. fields second. fields third. fields fourth. fields fifth. ''. ''. ''. ''. ''. ''. '' } ].
	analyze := [ :modelName |
		| modelClass metamodel package modelPackageName classes traits behaviors localProperties remoteProperties remoteTraitUses remoteInheritances extensions dependencyPackages dependencies metrics basePackageNames |
		modelClass := Smalltalk globals at: modelName asSymbol ifAbsent: [
			Error signal: 'Unknown model class: ', modelName ].
		metamodel := modelClass metamodel.
		modelPackageName := (modelClass name endsWith: 'Model')
			ifTrue: [ modelClass name allButLast: 'Model' size ]
			ifFalse: [ '' ].
		package := metamodel packages
			detect: [ :each | each name = modelClass package name ]
			ifNone: [ metamodel packages
				detect: [ :each | each name = modelPackageName ]
				ifNone: [ Error signal: 'No Fame package for model class: ', modelName ] ].
		dependencyPackages := (modelClass respondsTo: #allSubmetamodelsPackagesNames)
			ifTrue: [ modelClass allSubmetamodelsPackagesNames collect: #asString ]
			ifFalse: [ #() ].
		dependencies := '|' join: dependencyPackages.
		classes := metamodel classes select: [ :each | each package = package ].
		traits := metamodel traits select: [ :each | each package = package ].
		behaviors := classes , traits.
		localProperties := metamodel properties select: [ :property |
			property package isNil and: [ property mmClass package = package ] ].
		remoteProperties := metamodel properties reject: [ :property |
			property package isNil and: [ property mmClass package = package ] ].
		basePackageNames := #( 'Moose' ) asSet.
		remoteTraitUses := OrderedCollection new.
		behaviors do: [ :local |
			local traits do: [ :remote |
				remote package ~= package ifTrue: [ remoteTraitUses add: { local. remote } ] ] ].
		"Remote inheritance is a superclass in another package, excluding the Moose platform
		 base where MooseEntity and MooseModel live: every metamodel root inherits from it, so
		 counting it would add a constant to every row and say nothing about reuse. We filter on
		 that base rather than on the declared submetamodel names, because those are matched as
		 strings and a metamodel may spell its Fame package differently from its declaration
		 (Famix-Angular declares FamixTypeScriptGenerator while its Fame package is
		 FamixTypeScript). Verified in a Moose 13 image to give the same counts as the former
		 name-based rule for Famix-Java, Famix-Pharo, Famix-C and Famix-Cpp."
		remoteInheritances := classes select: [ :local |
			local superclass isNotNil and: [
				local superclass package ~= package and: [
					(basePackageNames includes: local superclass package name asString) not ] ] ].
		extensions := package extensions.
		metrics := {
			{ 'declaredPackages'. 1 }. { 'allPackages'. metamodel packages size }.
			{ 'declaredClasses'. classes size }. { 'allClasses'. metamodel classes size }.
			{ 'declaredTraits'. traits size }. { 'allTraits'. metamodel traits size }.
			{ 'declaredProperties'. localProperties size }. { 'remoteProperties'. remoteProperties size }.
			{ 'remoteTraitUsages'. remoteTraitUses size }. { 'remoteInheritances'. remoteInheritances size }.
			{ 'remotePropertyExtensions'. extensions size } }.
		metrics do: [ :metric |
			metricRow value: { modelClass name. package name. dependencies. metric first. metric second } ].
		metamodel packages do: [ :eachPackage |
			| packageClasses packageTraits |
			packageClasses := metamodel classes select: [ :each | each package = eachPackage ].
			packageTraits := metamodel traits select: [ :each | each package = eachPackage ].
			writeRow value: { 'packageBehavior'. modelClass name. eachPackage name. dependencies. 'entities'. packageClasses size. ''. ''. ''. ''. ''. ''. '' }.
			writeRow value: { 'packageBehavior'. modelClass name. eachPackage name. dependencies. 'traits'. packageTraits size. ''. ''. ''. ''. ''. ''. '' }.
			packageTraits do: [ :each |
				writeRow value: { 'packageTrait'. modelClass name. eachPackage name. dependencies. ''. ''. each name. eachPackage name. ''. ''. ''. ''. '' } ] ].
		remoteTraitUses do: [ :edge |
			writeRow value: { 'remoteTraitUse'. modelClass name. package name. dependencies. ''. ''. edge first name. edge first package name. edge second name. edge second package name. ''. ''. '' } ].
		remoteInheritances do: [ :local |
			writeRow value: { 'remoteInheritance'. modelClass name. package name. dependencies. ''. ''. local name. local package name. local superclass name. local superclass package name. ''. ''. '' } ].
		remoteProperties do: [ :property |
			| type typeName typePackage |
			type := property type.
			typeName := type ifNil: [ '' ] ifNotNil: [ :each | each name ].
			typePackage := type ifNil: [ '' ] ifNotNil: [ :each |
				((each respondsTo: #package) and: [ each package isNotNil ])
					ifTrue: [ each package name ] ifFalse: [ '' ] ].
			writeRow value: { 'remoteProperty'. modelClass name. package name. dependencies. ''. ''. ''. ''. property mmClass name. property mmClass package name. property name. typeName. typePackage } ].
		extensions do: [ :property |
			| type typeName typePackage |
			type := property type.
			typeName := type ifNil: [ '' ] ifNotNil: [ :each | each name ].
			typePackage := type ifNil: [ '' ] ifNotNil: [ :each |
				((each respondsTo: #package) and: [ each package isNotNil ])
					ifTrue: [ each package name ] ifFalse: [ '' ] ].
			writeRow value: { 'remotePropertyExtension'. modelClass name. package name. dependencies. ''. ''. ''. ''. property mmClass name. property mmClass package name. property name. typeName. typePackage } ] ].
		modelNames do: [ :modelName |
			[ analyze value: modelName ]
				on: Exception
				do: [ :exception |
					exception isResumable
						ifTrue: [ exception resume ]
						ifFalse: [
							writeRow value: { 'error'. modelName. ''. ''. 'exception'. exception class name, ': ', exception description. ''. ''. ''. ''. ''. ''. '' } ] ] ] ]
] on: Exception do: [ :exception |
	exception isResumable
		ifTrue: [ exception resume ]
		ifFalse: [
			reportFailure value: exception ] ].
