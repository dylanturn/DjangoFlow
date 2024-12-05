# This file ensures the templatetags directory is a proper Python package
from django.template import Library

# Explicitly import the dag_filters module to ensure it's loaded
from . import dag_filters
