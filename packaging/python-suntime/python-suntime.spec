# ==============================================================================
# Small dependency needed for Yin-Yang (auto dark/light theme switching
# with real sunrise/sunset support, packaging/parchaos-yin-yang/) --
# not packaged for Fedora under any name (`dnf list python3-suntime`:
# no matches). A tiny (~7KB), single-file, pure-Python library with a
# real GitHub repo and a proper pyproject.toml, so this is a standard
# Fedora Python package, nothing unusual.
# ==============================================================================

%global pypi_name suntime

Name:           python-%{pypi_name}
Version:        1.4.0
Release:        1%{?dist}
Summary:        Simple sunset and sunrise time calculation python library

License:        LGPL-3.0-or-later
URL:            https://github.com/SatAgro/suntime
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{pypi_name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

%description
Simple sunset and sunrise time calculation python library, used by
Yin-Yang for real sunrise/sunset-based dark/light theme switching.

%package -n python3-%{pypi_name}
Summary:        %{summary}
%description -n python3-%{pypi_name}
Simple sunset and sunrise time calculation python library.

%prep
%autosetup -n %{pypi_name}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files %{pypi_name}

%files -n python3-%{pypi_name} -f %{pyproject_files}
%license LICENSE
%doc README.md

%changelog
* Tue Sep 22 2026 ParchaOS packaging - 1.4.0-1
- Initial package.
