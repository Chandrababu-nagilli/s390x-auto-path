Name: s390x-auto-path
Version: 1.0.0
Release: 1%{?dist}
Summary: s390x auto lib/lib64 layout fixer
License: Apache-2.0
Group: Development/Tools
BuildArch: noarch
Requires: python3, python3-pip
%description
Utility to auto-fix lib/lib64 paths for s390x builds.

%prep
# no prep

%build
python3 -m pip wheel . -w dist/

%install
python3 -m pip install --root=%{buildroot} dist/*.whl

%files
%doc README.md
%license LICENSE
%{python3_sitelib}/s390x_auto_path

%changelog
* Thu Nov 14 2025 Your Name - 1.0.0-1
- initial
