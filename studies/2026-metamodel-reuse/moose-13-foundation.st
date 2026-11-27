Metacello new baseline: 'PharoBackwardCompatibility'; repository: 'github://jecisc/PharoBackwardCompatibility:a021a7f6d8c05fa529a9deab38eab2af847fafa4/src'; onConflictUseIncoming; load; lock.

Metacello new baseline: 'Hashtable'; repository: 'github://pharo-contributions/Hashtable:b9e28ac0bbc7058b5603606db7f1b3e2674071bf/src'; onConflictUseIncoming; load: 'Core'; lock.

Metacello new baseline: 'Iterators'; repository: 'github://juliendelplanque/Iterators:6600067f1bde7fd66d6d351d8299d7c1aeaaea75/src'; onConflictUseIncoming; load: #( 'core' 'collections' 'shell-dsl' 'inspector-extensions' ); lock.

Metacello new baseline: 'TreeQuery'; repository: 'github://juliendelplanque/TreeQuery:cf24ec8567e8c0ca03d290909d389358d022953d/src'; onConflictUseIncoming; load: 'core'; lock.

Metacello new baseline: 'Fame'; repository: 'github://moosetechnology/Fame:afc932cc53ab3448d484321fedecaaf2e203c0a4/src'; onConflictUseIncoming; load: 'Core'; lock.

Metacello new baseline: 'CollectionExtensions'; repository: 'github://pharo-contributions/CollectionExtensions:7d61095afdead8d6949b7f0d5412964b200837a5/src'; onConflictUseIncoming; load: 'Core'; lock.

Metacello new baseline: 'DeepTraverser'; repository: 'github://pharo-contributions/DeepTraverser:14f02866220a859e9298f07de9fd30aacf717ed3/src'; onConflictUseIncoming; load: 'Core'; lock.

Metacello new baseline: 'SingularizePluralize'; repository: 'github://pharo-contributions/SingularizePluralize:0b3b48fb56a2b4c2594c151d3d02d5da1586b842/src'; onConflictUseIncoming; load; lock.

Metacello new githubUser: 'moosetechnology' project: 'Famix' commitish: 'c89e0e48958172f9e641d0d1f0c1b8e25864689b' path: 'src'; baseline: 'Famix'; onConflictUseIncoming; onWarning: [ :warning | warning resume ]; load: 'ModelJava'; lock.
