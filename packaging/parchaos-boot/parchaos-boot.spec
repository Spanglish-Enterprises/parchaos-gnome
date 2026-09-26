Name:           parchaos-boot
Version:        1.0.0
Release:        2%{?dist}
Summary:        Keeps new kernels in the ParchaOS boot menu
License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-grub-setup
Source90:       LICENSE
BuildArch:      noarch

Requires:       grub2-tools
Requires:       grub2-tools-minimal
Requires(post): grub2-tools
Requires(post): grub2-tools-minimal

%description
ParchaOS installs run GRUB without BLS. On UEFI, the installer wrote
GRUB's whole configuration to the EFI partition, which kernel updates
never regenerate, so new kernels didn't appear in the boot menu and the
system became unbootable once the original kernel was removed. This
package switches those installs to Fedora's layout (the real
configuration in /boot/grub2/grub.cfg, regenerated on every kernel
update, and a small EFI stub that loads it), and the installer uses the
same script for new installs.

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_libexecdir}/parchaos-grub-setup

%post
# Safe to run every time: only acts on UEFI installs without BLS whose
# EFI config isn't a stub yet.
%{_libexecdir}/parchaos-grub-setup || :

%files
%license LICENSE
%{_libexecdir}/parchaos-grub-setup

%changelog
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-2
- Ship the license text (%license) with an accurate SPDX License tag.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-1
- First release: move UEFI installs to Fedora's GRUB layout so kernel
  updates reach the boot menu.
