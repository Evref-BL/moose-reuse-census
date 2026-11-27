Metacello new baseline: 'NeoJSON'; repository: 'github://svenvc/NeoJSON:11e274dd96dc9636cab90929937b7cd09719de7c/repository'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'TinyLogger'; repository: 'github://jecisc/TinyLogger:06ef704825e9f46dfb09d83efa892f269ff3d258/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'MoreLogger'; repository: 'github://badetitou/MoreLogger:96c2a1c2283e6606f803d4a1605f930d61770f76/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'Mocketry'; repository: 'github://dionisiydk/Mocketry:5dd5e76ec7b0fe9f3777f4b68fc48f64d484ff30'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'BitmapCharacterSet'; repository: 'github://pharo-contributions/BitmapCharacterSet:62ee106d7960646fa5b85577fe83f920a6bb6672/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'OrderPreservingDictionary'; repository: 'github://pharo-contributions/OrderPreservingDictionary:7b3ab363379e35a3e0e0183b6c2d193a675f898f/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'XMLWriter'; repository: 'github://pharo-contributions/XML-XMLWriter:68489c67c22a433c4a0edd1c6e6610b33a1c4dad/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'XMLParser'; repository: 'github://pharo-contributions/XML-XMLParser:02fa5ed7cc720af09f0930a3670be60a17979141/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'JSON'; repository: 'github://Evref-BL/Json-BackwardCompatibility:16a67adc690be29ba84c7236d0ea8108dddd0288/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'AWS'; repository: 'github://Evref-BL/aws-sdk-smalltalk:76ed2cb258af7bef449a20e9cbe7b635ac9eef6e/pharo-repository'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'MongoTalk'; repository: 'github://pharo-nosql/mongotalk:3300780c336ee22222c58465d0eb36990358c9b6/mc'; onConflictUseIncoming; load: 'Client'; lock.
Metacello new baseline: 'SimpleRene'; repository: 'github://pharo-contributions/SimpleRene:de059fc2e3732594fc6e0320e25c966b58a7ba64/src'; onConflictUseIncoming; load: 'Core'; lock.
Metacello new baseline: 'Voyage'; repository: 'github://pharo-nosql/voyage:cfc2118851f3f25f41392be1320ea36626edf521/mc'; onConflictUseIncoming; load: 'mongo'; lock.
Metacello new baseline: 'GitBridge'; repository: 'github://jecisc/GitBridge:c93801983443a55e1690be777a7d488241c924d8/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'GitlabAPI'; repository: 'github://Evref-BL/Gitlab-Pharo-API:da02b1c2bde033837c92aaebd092d4de81bdfd43/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'GithubAPI'; repository: 'github://Evref-BL/github-Pharo-API:156d0975b3cc7e894bdb4f529126335a95af85d2/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'BitbucketPharoAPI'; repository: 'github://Evref-BL/Bitbucket-Pharo-API:9109c4db50c27fdad1ebc11a1f36fe1b0132ac9d/src'; onConflictUseIncoming; load; lock.
Metacello new baseline: 'JiraPharoAPI'; repository: 'github://Evref-BL/Jira-Pharo-API:5cbb1144865633560fc22df6caf839a858bbc7e9/src'; onConflictUseIncoming; load; lock.
Metacello new repository: 'github://moosetechnology/GitProjectHealth:2.1.0/src'; baseline: 'GitLabHealth'; onConflict: [ :ex | ex useLoaded ]; onUpgrade: [ :ex | ex useIncoming ]; onDowngrade: [ :ex | ex useLoaded ]; load: #( 'Core' 'Famix' 'Jira' ).
