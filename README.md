# politexts

Scrapping and indexation of political speeches.

This project contains basic utilities to connect to ElasticSearch and use 
a classification model from Huggingface. It also provides scrapping scripts
(using `scrapy.io`) for different French political and news sites.

# How to use

The build is managed by `pybuilder` which generates the python packages, handles 
unit tests etc. The description of the project is in the `build.py` file.

The following steps are required:

1. build the `overton` package
2. install it
3. create the index
4. use `scrapy` to scrap and index websites

## Build

Simply type:

```shell
pyb
```

This will create a `overton` package in the `target/dist` directory

## Install

The package created by `pybuilder` can be directly installed through `pip`

```shell
pip install target/dist/overton-1.0.dev1
```

(replace version with the correct one)

## Create index
The following code will create the index and the corresponding mappings

```python
from overton.elasticsearch import Polindex

Polindex.connect(servers="***", user="***", password="***")
Polindex.create_index()
```

## Scrap and index

Scrapping is handled by [scrapy](https://scrapy.org). The provided pipelines index the speeches directly in ElasticSearch, using [elasticsearch_dsl](https://elasticsearch-dsl.readthedocs.io/en/latest/). The classes corresponding to the political speeches are defined in `src/main/python/politexts/elasticsearch`. The `politexts`package allows to use them freely in any client application.

You must provide the following variables in your environment or directly in `poliscrap/poliscrap/settings.py` (the same that were used for index creation)

- `ELASTICSEARCH_HOSTS` : (list of) ES hosts
- `ELASTICSEARCH_USERNAME`,
- `ELASTICSEARCH_PASSWORD`: credentials to access ES server

You can then use the standard `scrapy` commands, especially for crawling:

```shell
cd poliscrap
scrapy crawl vie_publique
```

There are currently two crawlers defined (that can be used as arguments to the `scrapy crawl` command):

* `vie_publique`: political speeches from https://www.vie-publique.fr/discours
* `rn`: speeches from the French Rassemblement National website (https://rassemblementnational.fr)

All crawlers implement a `DEPTH_LIMIT` value to restrict the crawling if needed. This can be set through the environment variable with the same name.

_Warning_: if you plan to index the whole `vie_publique` site, plan to iterate two or three times: the web servers appears to crash for some reason after an important number of requests. Look at the logs to see at which page you should restart your crawling. This is may be a preventive policy, but doesn't look like it. 
