# DealTalk
a versatile, multi-tenant AI sales assistant platform that transforms business catalogs into intelligent conversation agents. 

# Getting the requirements ready!!

1. Create a virtual env

```python3.12 -m venv venv```

2. In the venv file created add in pip.conf file with the following:

```
[global]
YOUR_PAT=
index-url=https://username%40spinutech.com:YOUR_PAT_FOR_PACKAGE_READ@bsstfs.pkgs.visualstudio.com/DealFlow/_packaging/dealflow/pypi/simple/
trusted-host=bsstfs.pkgs.visualstudio.com
always-trusted=true

[dev]
extra-index-url=https://pypi.org/simple
```

3. Install packages:

```pip install -r requirements.txt```