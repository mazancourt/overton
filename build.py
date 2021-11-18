#   -*- coding: utf-8 -*-
from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.flake8")
use_plugin("python.coverage")
use_plugin("python.distutils")


name = "overton"
default_task = "publish"
version = "1.0.dev1"
description = 'Crawling, indexing and parsing political texts'
long_description = """
This package provides basic tools to crawl sites, index data in ElasticSearch, manage indexes, create dashboards based
on linguistic analysis. The Politexts is part of the Overton project, aimed at analyzing French political speeches, 
especially for the 2022 election
"""
license = """
Copyright (c) 2021, Mazancourt Conseil

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License
"""
url = "http://www.mazancourt.com"


@init
def set_properties(project):
    # Don't fail if coverage is not sufficient
    project.set_property('coverage_break_build', False)
