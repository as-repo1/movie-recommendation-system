Name:           reclens
Version:        2.1.0
Release:        1%{?dist}
Summary:        AI-Powered Movie Discovery & Recommendation Platform (GTK4/Libadwaita)

License:        MIT
URL:            https://github.com/as-repo1/movie-recommendation-system
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
Requires:       python3
Requires:       python3-gobject
Requires:       libadwaita
Requires:       gtk4
Requires:       python3-pandas
Requires:       python3-numpy
Requires:       python3-httpx

%description
RecLens is a native modern Linux movie recommendation application built with GTK4
and Libadwaita. Powered by an ultra-portable Top-K sparse similarity model and
snappy Parquet catalog, it delivers instant recommendations (<5ms latency).

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/reclens
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
mkdir -p %{buildroot}%{_metainfodir}

install -m 755 linux/run.sh %{buildroot}%{_bindir}/reclens
install -m 644 linux/data/org.reclens.RecLens.desktop %{buildroot}%{_datadir}/applications/
install -m 644 linux/data/icons/org.reclens.RecLens.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/
install -m 644 linux/data/org.reclens.RecLens.metainfo.xml %{buildroot}%{_metainfodir}/

%files
%{_bindir}/reclens
%{_datadir}/applications/org.reclens.RecLens.desktop
%{_datadir}/icons/hicolor/scalable/apps/org.reclens.RecLens.svg
%{_metainfodir}/org.reclens.RecLens.metainfo.xml

%changelog
* Sun Aug 30 2026 RecLens Team <team@reclens.org> - 2.1.0-1
- Initial native GTK4/Libadwaita Linux release
