# FOR pom_writer.py
## Run command : py pom_writer.py
## Configuration
Config rules go in config.json. Keys are as follows: 

````
{
    "pom.xml": [
        "<groupId>:<artifactId>": [
            {
                "range": [<string_lowerbound>, <string_upperbound>]
                "fixVersion": <string_fixversion>
            }
        ]
    ]
}
````

Substituted values are enclosed in <>

* '\<groupId>:\<artifactId>': Go figure. Substitute the actual groupId, artifactId of the dependency you want to change 
* range: the lowerbound, upperbound that a fixVersion can apply to. Note that they're discerned by order, so lowerbound must always be at index 0 and upperbound at index 1. Also lowerbound is inclusive (ver >= lowerbound to be in range) but upperbound is exclusive (ver < upperbound to be in range)
* fixVersion: go figure idiot

TODO: THIS does not handle overriding! FCK. Config will need to be refactored to allow for decisionmaking over whether to  add an override or updatE an existing dependency