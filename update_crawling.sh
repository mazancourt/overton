#!/bin/bash

source $HOME/.config/politexts

cd $HOME/projects/politexts
source venv/bin/activate

cd poliscrap
scrapy crawl rn
scrapy crawl vie_publique
