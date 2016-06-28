_system() {
    echo `uname -o 2>/dev/null || uname -s`
}

_processor() {
    echo `uname -p`
}

_release() {
    echo `uname -r`
}

_machine() {
    echo `uname -m`
}

_osversion() {
    echo `uname -v`
}

_solaris_download() {
    # input:  <package> <version>
    # output: <filename>
    name="$1"
    version="$2"
    processor="$(_processor)"
    case "$processor" in
        "i386") arch="x64"
            ;;
        "sparc") arch="sparc"
            ;;
        *) echo "unsupported solaris architecture" 1>&2;
            exit 1
            ;;
    esac

    release="$(_release)"
    case "$release" in
        "5.11") release="11"
            ;;
        "5.10") release="10"
            ;;
        *) echo "unsupported solaris release" 1>&2;
            exit 1
            ;;
    esac

    packages_base_url="{{ host_url }}/packages/{{ index_name }}/index/packages"
    os="solaris-$release"
    uri="$name/releases/$version/distributions/$os/architectures/$arch/extensions/pkg.gz"
    fname="$name-$version-$os-$arch.pkg.gz"
    url="$packages_base_url/$uri/$fname"
    _curl $url > $fname

    if [ "$?" != "0" ]; then
        echo "file not found: $url" 1>&2;
        exit 1
    fi

    echo $fname
}

_aix_download() {
    # input:  <package> <version>
    # output: <filename>
    name="$1"
    version="$2"
    processor="$(_processor)"
    case "$processor" in
        "powerpc") arch="powerpc"
            ;;
        *) echo "unsupported aix architecture" 1>&2;
            exit 1
            ;;
    esac

    release="$(_osversion).$(_release)"
    case "$release" in
        "7.1") release="7.1"
            ;;
        "7.2") release="7.2"
            ;;
        *) echo "unsupported aix release" 1>&2;
            exit 1
            ;;
    esac

    packages_base_url="{{ host_url }}/packages/{{ index_name }}/index/packages"
    os="aix-$release"
    uri="$name/releases/$version/distributions/$os/architectures/$arch/extensions/rpm"
    fname="$name-$version-$os-$arch.rpm"
    url="$packages_base_url/$uri/$fname"
    _curl $url > $fname

    if [ "$?" != "0" ]; then
        echo "file not found: $url" 1>&2;
        exit 1
    fi

    echo $fname
}

_cygwin_download() {
    # input:  <package> <version>
    # output: <filename>
    name="$1"
    version="$2"
    processor="$(_machine)"
    case "$processor" in
        "i686") arch="x86"
            ;;
        "x86_64") arch="x64"
            ;;
        *) echo "unsupported cygwin architecture" 1>&2;
            exit 1
            ;;
    esac

    packages_base_url="{{ host_url }}/packages/{{ index_name }}/index/packages"
    os="windows"
    uri="$name/releases/$version/distributions/$os/architectures/$arch/extensions/msi"
    fname="$name-$version-$os-$arch.msi"
    url="$packages_base_url/$uri/$fname"
    _curl $url > $fname

    if [ "$?" != "0" ]; then
        echo "file not found: $url" 1>&2;
        exit 1
    fi

    echo $fname
}

_sh() {
    echo "executing shell... this can take a while..." 1>&2;
    sh "$1" >&2;
}

_gunzip() {
    echo "extracting... this can take a while..." 1>&2;
    gunzip -f "$1" 1>&2;
}

_pkgadd() {
    pkgadd $* 1>&2;
    if [ "$?" != "0" ]; then
        echo "installation failed; command-line was pkgadd $*" 1>&2;
        exit 1
    fi
}

_rpm() {
    rpm $* 1>&2;
    if [ "$?" != "0" ]; then
        echo "installation failed; command-line was rpm $*" 1>&2;
        exit 1
    fi
}

_msiexec() {
    msiexec $* 1>&2;
    if [ "$?" != "0" ]; then
        echo "installation failed; command-line was msiexec $*" 1>&2;
        exit 1
    fi
}

_curl() {
    echo "downloading... this can take a while..." 1>&2;
    curl -f "$1"
}

_solaris_install() {
    # input:  <name> <version> <file>

    _extract_package() {
        # input:  <file>
        _gunzip "$1"
        if [ "$?" != "0" ]; then
            echo "extraction failed" 1>&2;
            exit 1
        fi
    }

    _write_admin_file() {
        echo partial=nocheck > admin.file
        echo runlevel=nocheck >> admin.file
        echo idepend=nocheck >> admin.file
        echo rdepend=nocheck >> admin.file
        echo setuid=nocheck >> admin.file
        echo action=nocheck >> admin.file
        echo partial=nocheck >> admin.file
        echo conflict=nocheck >> admin.file
        echo authentication=quit >> admin.file
        echo instance=overwrite >> admin.file
        echo basedir=default >> admin.file
    }

    _install() {
        echo "installing... this can take a while..." 1>&2;
        # input: <name> <file>
        _pkgadd -n -a "admin.file" -d "${2%.*}" "$1"
        if [ "$?" != "0" ]; then
            exit 1
        fi
    }

    _write_admin_file
    _extract_package "$3"
    if [ "$?" != "0" ]; then
        exit 1
    fi
    _install "$1" "$3"
    if [ "$?" != "0" ]; then
        exit 1
    fi
}

_aix_install() {
    # input:  <name> <version> <file>
    _rpm -Uvh "$3"
    if [ "$?" != "0" ]; then
        exit 1
    fi
}

_cygwin_install() {
    # input:  <name> <version> <file>
    _msiexec /i "$3" /passive /norestart
    if [ "$?" != "0" ]; then
        exit 1
    fi
}

parse_commandline() {
    # input:  <script-name> <package> [<version>]
    argc=$#
    progname="$0"
    if [ $argc -eq 0 -o $argc -gt 2 ]; then
        echo "usage: $progname <package> [<version>]" 1>&2;
        exit 1
    fi
}

get_version() {
    # input:  <package> [<version>]
    # output: <version>
    argc=$#
    packages_base_url="{{ host_url }}/packages/{{ index_name }}/index/packages"
    if [ $argc -eq 1 ]; then
        latest_release="$packages_base_url/$1/latest_release.txt"
        version=$(_curl "$latest_release")
        if [ "$?" != "0" ]; then
            echo "package not found" 1>&2;
            exit 1
        fi
    else
        version=$2
    fi
    echo $version

}

download() {
    # input:  <package> <version>
    # output: <filename>
    argc=$#
    name="$1"
    version="$2"
    uname="$(_system)"

    if [ $uname = "SunOS" -o $uname = "Solaris" ]; then
        fname=$(_solaris_download $name $version)
        if [ "$?" != "0" ]; then
        exit 1
        fi
        echo $fname
    elif [ $uname = "Cygwin" ]; then
        fname=$(_cygwin_download $name $version)
        if [ "$?" != "0" ]; then
        exit 1
        fi
        echo $fname
    elif [ $uname = "AIX" ]; then
        fname=$(_aix_download $name $version)
        if [ "$?" != "0" ]; then
        exit 1
        fi
        echo $fname
    else
        echo "operating system not supported" 1>&2;
        exit 1
    fi

}

install() {
    # input: <package> <version> <file>
    uname="$(_system)"

    if [ $uname = "SunOS" -o $uname = "Solaris" ]; then
        _solaris_install "$1" "$2" "$3"
    elif [ $uname = "Cygwin" ]; then
        _cygwin_install "$1" "$2" "$3"
    elif [ $uname = "AIX" ]; then
        _aix_install "$1" "$2" "$3"
    else
        echo "operating system not supported"
        exit 1
    fi
}
