=======
History
=======

0.3.0 (2024-09-xx)
-----------------
* Add support for running __main__ without appending scripts
* Change and add some type annotations
* Support for getting packages installed via site_packages
* Encodes code in Base64, no more escaping problems now
* Add suport for disabling importing a package by default, even with only one package
* A couple bugfixes

0.2.1 (2018-08-02?)
------------------
* Add some support for python 3

0.2.0 (2016-04-03)
------------------

* Add support for incompatible loaders to coexists.
* Generate and use pyc files for modules.
* Add support for the filename to be different than the package.
* Now __main__ works directly from the package as expected.

0.1.1 (2016-03-29)
------------------

* Fix missing template file when installing
* Reduce memory footprint to keep the package structure and code.
* Include tagging of beginning of files in the output.

0.1.0 (2016-03-27)
------------------

* Show code when debugging and on tracebacks
* Improve internal package and module names
* Fix line numbers (off by 1)
* Package's root namespace is no longer polluted by pinliner
* Original filename for package/modules is stored so it will be reported by
  exceptions and logging.

0.0.1 (2016-03-26)
------------------

* Basic functionality.
