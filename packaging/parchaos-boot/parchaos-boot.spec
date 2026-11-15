Name:           parchaos-boot
Version:        1.1.0
Release:        2%{?dist}
Summary:        ParchaOS boot menu: new kernels and earlier versions
License:        GPL-3.0-or-later
URL:            https://github.com/Spanglish-Enterprises/parchaos-gnome
Source0:        parchaos-grub-setup
Source1:        parchaos-snapshot-boot
Source2:        11_parchaos_snapshots
Source3:        parchaos-snapshot-module-setup.sh
Source4:        parchaos-snapshot-overlay.sh
Source5:        50-parchaos-snapshot.conf
Source6:        parchaos-snapshot-menu.service
Source7:        parchaos-earlier-version
Source8:        parchaos-earlier-version.desktop
Source9:        org.parchaos.snapshot-boot.policy
Source10:       es.po
Source11:       org.parchaos.EarlierVersion.desktop
Source12:       parchaos-snapshot-relabel.service
Source90:       LICENSE
BuildArch:      noarch

Requires:       grub2-tools
Requires:       grub2-tools-minimal
Requires(post): grub2-tools
Requires(post): grub2-tools-minimal
# Earlier versions in the boot menu (#151).
Requires:       btrfs-progs
Requires:       dracut
Requires:       util-linux
# The window shown when started from an earlier version.
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       polkit
BuildRequires:  gettext
BuildRequires:  systemd-rpm-macros
%{?systemd_requires}

%description
ParchaOS installs run GRUB without BLS. On UEFI, the installer wrote
GRUB's whole configuration to the EFI partition, which kernel updates
never regenerate, so new kernels didn't appear in the boot menu and the
system became unbootable once the original kernel was removed. This
package switches those installs to Fedora's layout (the real
configuration in /boot/grub2/grub.cfg, regenerated on every kernel
update, and a small EFI stub that loads it), and the installer uses the
same script for new installs.

It also adds "Start from an earlier version" to the boot menu: the
system as it was before each of the last few updates (from the
snapshots ParchaOS takes before updating). Starting one changes nothing
on the disk; it can then be kept as the system, and that can be undone.

%prep
cp -p %{SOURCE90} .

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_libexecdir}/parchaos-grub-setup
install -Dm0755 %{SOURCE1} %{buildroot}%{_libexecdir}/parchaos-snapshot-boot
install -Dm0755 %{SOURCE2} %{buildroot}%{_sysconfdir}/grub.d/11_parchaos_snapshots
install -Dm0755 %{SOURCE3} %{buildroot}%{_prefix}/lib/dracut/modules.d/90parchaos-snapshot/module-setup.sh
install -Dm0755 %{SOURCE4} %{buildroot}%{_prefix}/lib/dracut/modules.d/90parchaos-snapshot/parchaos-snapshot-overlay.sh
install -Dm0644 %{SOURCE5} %{buildroot}%{_prefix}/lib/dracut/dracut.conf.d/50-parchaos-snapshot.conf
install -Dm0644 %{SOURCE6} %{buildroot}%{_unitdir}/parchaos-snapshot-menu.service
install -d %{buildroot}%{_unitdir}/multi-user.target.wants
ln -s ../parchaos-snapshot-menu.service %{buildroot}%{_unitdir}/multi-user.target.wants/parchaos-snapshot-menu.service
install -Dm0644 %{SOURCE12} %{buildroot}%{_unitdir}/parchaos-snapshot-relabel.service
install -d %{buildroot}%{_unitdir}/sysinit.target.wants
ln -s ../parchaos-snapshot-relabel.service %{buildroot}%{_unitdir}/sysinit.target.wants/parchaos-snapshot-relabel.service
install -d %{buildroot}%{_sharedstatedir}/parchaos/snapshot-boot
install -Dm0755 %{SOURCE7} %{buildroot}%{_libexecdir}/parchaos-earlier-version
install -Dm0644 %{SOURCE8} %{buildroot}%{_sysconfdir}/xdg/autostart/parchaos-earlier-version.desktop
install -Dm0644 %{SOURCE9} %{buildroot}%{_datadir}/polkit-1/actions/org.parchaos.snapshot-boot.policy
install -Dm0644 %{SOURCE11} %{buildroot}%{_datadir}/applications/org.parchaos.EarlierVersion.desktop
install -d %{buildroot}%{_datadir}/locale/es/LC_MESSAGES
msgfmt --check -o %{buildroot}%{_datadir}/locale/es/LC_MESSAGES/parchaos-boot.mo %{SOURCE10}

%post
# Safe to run every time: only acts on UEFI installs without BLS whose
# EFI config isn't a stub yet.
%{_libexecdir}/parchaos-grub-setup || :
# The installer of older images left a stray initramfs behind (Fedora's
# calamares example config named it initramfs-freebsd.img). No package
# owns it and nothing boots it.
rm -f /boot/initramfs-freebsd.img || :

%posttrans
# Snapshots can only be started with the initramfs module. Rebuild the
# initramfs of the installed kernels when this package version is new to
# the machine, so the next snapshot taken before an update carries the
# current module and can be started from the boot menu.
mark=%{_sharedstatedir}/parchaos/snapshot-boot/initramfs-done
if [ "$(cat $mark 2>/dev/null)" != "%{version}-%{release}" ]; then
    dracut -f --regenerate-all >/dev/null 2>&1 && \
        echo "%{version}-%{release}" > $mark || :
fi

%files
%license LICENSE
%{_libexecdir}/parchaos-grub-setup
%{_libexecdir}/parchaos-snapshot-boot
%config(noreplace) %{_sysconfdir}/grub.d/11_parchaos_snapshots
%{_prefix}/lib/dracut/modules.d/90parchaos-snapshot/
%{_prefix}/lib/dracut/dracut.conf.d/50-parchaos-snapshot.conf
%{_unitdir}/parchaos-snapshot-menu.service
%{_unitdir}/multi-user.target.wants/parchaos-snapshot-menu.service
%{_unitdir}/parchaos-snapshot-relabel.service
%{_unitdir}/sysinit.target.wants/parchaos-snapshot-relabel.service
%dir %{_sharedstatedir}/parchaos
%dir %{_sharedstatedir}/parchaos/snapshot-boot
%{_libexecdir}/parchaos-earlier-version
%config(noreplace) %{_sysconfdir}/xdg/autostart/parchaos-earlier-version.desktop
%{_datadir}/polkit-1/actions/org.parchaos.snapshot-boot.policy
%{_datadir}/applications/org.parchaos.EarlierVersion.desktop
%{_datadir}/locale/es/LC_MESSAGES/parchaos-boot.mo

%changelog
* Sun Nov 15 2026 ParchaOS packaging - 1.1.0-2
- With SELinux on, a start from an earlier version labelled its temporary
  layer as memory (tmpfs_t) and services were denied. An early service
  now restores the real labels once the policy is loaded.
* Sun Nov 15 2026 ParchaOS packaging - 1.1.0-1
- Ticket #151: "Start from an earlier version" in the boot menu, with the
  system as it was before the last few updates. Starts with a temporary
  writable layer (new dracut module); "parchaos-snapshot-boot keep"
  makes it the system, "undo" goes back. At login, an "Earlier Version"
  window says which version is running and offers Keep This Version,
  Restart Normally, or Go Back to the Newer Version (English, Spanish).
- Remove the stray /boot/initramfs-freebsd.img left by the installer.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-2
- Ship the license text (%license) with an accurate SPDX License tag.
* Sat Sep 26 2026 ParchaOS packaging - 1.0.0-1
- First release: move UEFI installs to Fedora's GRUB layout so kernel
  updates reach the boot menu.
