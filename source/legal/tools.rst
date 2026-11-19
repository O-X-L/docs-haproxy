.. _legal_tools:

============
Docs Toolset
============

Tools used by the Documentation
*******************************

* The build-process is covered in this repository: `O-X-L/docs-haproxy <https://github.com/O-X-L/docs-haproxy>`_

* The tool `haproxy-dconv <https://github.com/cbonte/haproxy-dconv>`_ is used to partly parse `the text-based HAProxy-community documentation <https://github.com/haproxy/haproxy/tree/master/doc>`_.

* It is converted to reStructuredText by using `pandoc <https://pandoc.org/>`_

* The documentation is converted to HTML by `Sphinx <https://www.sphinx-doc.org>`_

* The modern styling is provided by `https://github.com/jbms/sphinx-immaterial <https://https://github.com/jbms/sphinx-immaterial>`_

* The documentation is served using `nginx <https://nginx.org/en/>`_, proxied using `HAProxy <https://www.haproxy.com/>`_, secured by the `Coraza WAF <https://coraza.io>`_ and firewalled using `NFTables <https://netfilter.org/projects/nftables/>`_.
