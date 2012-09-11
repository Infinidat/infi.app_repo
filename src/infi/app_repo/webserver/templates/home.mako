<html>
<head>
</head>
<body>
    <div>
        <h1>Setting up APT repository</h1>
        <p>curl ${apt_url} | sh -</p>
    </div>
    <div>
        <h1>Setting up YUM repository</h1>
        <p>curl ${yum_url} | sh -</p>
    <div>
        <h1>Packages</h1>
        % for package in metadata['packages']:
        <div>
        <h2>${' '.join([item.capitalize() for item in package['name'].split('-')])}</h2>
            % for release in package['releases']:
            <div>
                <h3>Version ${release['version']}</h3>
                % for distribution in release['distributions']:
                <div>
                    <a href="${ftp_url}${distribution['filepath']}">${distribution['platform']} ${distribution['architecture']}</a>
                </div>
                % endfor
            </div>
            % endfor
        </div>
        % endfor
    </div>
</body>
</html>
