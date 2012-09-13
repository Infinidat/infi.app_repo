<!DOCTYPE html>
<html lang="en">
<head>
    <title>Application Repository</title>
    <link src="/static/reset.css"></script>
    <link href="/static/bootstrap/css/bootstrap.min.css" rel="stylesheet">
    <script src="/static/jquery-1.8.1.min.js"></script>
    <script src="/static/bootstrap/js/bootstrap.min.js"></script>
</head>
<body>
    <div class="navbar" id="home">
        <div class="navbar-inner">
            <a class="brand">Application Repository</a>
            <ul class="nav">
                <li class="active"><a href="#home">Home</a></li>
                <li><a href="#setup">Setup</a></li>
                <li><a href="#inventory">Inventory</a></li>
            </ul>
        </div>
    </div>
    <div class="row" id="setup">
        <div class="span12">
            <h1>Setting up APT/YUM repository</h1>
            <p>To set up this repository in your Linux distribution, execute: <code>curl ${setup_url} | sh -</code></p>
        </div>
    </div>
    <div class="row" id="inventory">
        <div class="span12">
            <h1>Package Inventory</h1>
            % for package in metadata['packages']:
            <div class="row">
                <div class="span12">
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
            </div>
            % endfor
        </div>
    </div>
</body>
</html>
