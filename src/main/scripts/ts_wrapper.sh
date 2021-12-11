#!/bin/bash
java -cp $HOME/.local/termsuite/termsuite-core-3.0.10.jar fr.univnantes.termsuite.tools.TerminologyExtractorCLI \
-t $HOME/.local/treetagger --tsv-properties 'pilot,lemma,spec,freq' -l fr -c $1 --tsv $2
