#!/bin/sh

{% include 'functions.sh' %}

{% if package %}
{% if version %}
set -- "{{ package }}" "{{ version }}"
{% else %}
set -- "{{ package }}"
{% endif %}
{% endif %}

parse_commandline $*
package="$1"

version="$(get_version $1 $2)"
if [ "$?" != "0" ]; then
    exit 1
fi

file="$(download "$package" "$version")"
if [ "$?" != "0" ]; then
    exit 1
fi

install "$package" $"version" "$file"
if [ "$?" != "0" ]; then
    exit 1
fi
exit 0
