# ampush: Hassle-free automount map management for Active Directory

ampush lets you manage automount maps in Active Directory without the hassle of GUI tools and building LDIFs.

## Version

0.3, 14-Sep-2017. Copyright (C) 2016-2017 Research Computing Group, Simon Fraser University.


## Why Active Directory and ampush?

  - It's 2016. Get rid of NIS. Active Directory is inevitable in heterogeneous environments.
  - You probably already have the AD schema you need to serve automounts.
  - Use classic flat file automount tables instead of ADSI Edit's 13-click, 4-stage Wizard(tm).


### Tools

 - **ampush**: the main course
 - **dump_admaps**, **dump_ffmaps**: list the contents of your AD automount container and the flat file maps in maps/.
 - **verify_admaps**, **verify_ffmaps**: quick and dirty map validation
 - **amcat**: list your automounts from AD.


## Setup

 - Create a container in AD.
 - Populate ampush.conf.
 - Populate auto.master and auto.{x,y,z} in maps/.
 - Run ./ampush --dry-run --sync and watch push.log.




### Requirements: Active Directory
 -  **Active Directory with rfc2307 Unix schema extensions**. These are built into Windows Server 2012 and [will probably remain so][1] in future Windows Server releases.  Tested with Windows Server 2008R2+IDU and Windows Server 2012. Probably works a lot further back.
 -  **A container** (not an OU) where the automounts will live.
 - **A limited privilege AD user**. Restrict this user so that it can only change the automount container and all descendant objects. **We are not responsible if you accidentally delete your entire AD** because you didn't listen to us.


### Requirements: ampush
 - A box with Python 2.6 or 2.7.
 - [python-ad](https://github.com/sfu-rcg/python-ad)
 - [python-ldap](https://pypi.python.org/pypi/python-ldap) (currently not compatible with Python 3.x)

Not tested on Windows.


### Requirements: Unix clients
 - Must be joined to the AD domain.
 - [SSSD](https://fedorahosted.org/sssd/) or autofs_ldap (not tested).



## ampush vs. FreeIPA automount management
ampush is built for environments where FreeIPA is not present. Assuming you could make `ipa` talk directly to AD, FreeIPA's automount facilities are built around rfc2307bis (automountMap objects) which are [not native to Active Directory](https://fedorahosted.org/sssd/ticket/1341).


## Version History

 - v0.3, 14-Sep-2017: Seek and destroy conflict (cn=\*\\0aCNF:\*) objects.
 - v0.21, 07-Apr-2016: Fix function call. Clarify error message and requirements in README. Thanks, Ben!
 - v0.2, 23-Mar-2016: Complete rewrite. First public release.
 - v0.1, 24-Sep-2013: (internal) First working release.



#### You code like a sysadmin.

[I choose to take that as a compliment.](https://www.usenix.org/conference/lisa14/conference-program/presentation/minter)


#### License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


[1]: https://blogs.technet.microsoft.com/activedirectoryua/2016/02/09/identity-management-for-unix-idmu-is-deprecated-in-windows-server/
