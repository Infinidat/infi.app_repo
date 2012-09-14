<!DOCTYPE html>
<html lang="en">
<head>
    <title>Application Repository</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link src="/static/reset.css"></script>
    <link href="assets/css/bootstrap-responsive.css" rel="stylesheet">
    <link href="/static/bootstrap/css/bootstrap.min.css" rel="stylesheet">
    <script src="/static/jquery-1.8.1.min.js"></script>
    <script src="/static/bootstrap/js/bootstrap.min.js"></script>
</head>
<body data-spy="scroll" data-target="#home">
    <div class="navbar navbar-inverse navbar-fixed-top" id="home">
        <div class="navbar-inner">
            <a class="brand">Application Repository</a>
            <ul class="nav nav-list inventory-sidenav">
            % for package in metadata['packages']:
                <li>
                    <a href="#${package['name']}">
                        <i class="icon-chevron-right"></i>
                        ${' '.join([item.capitalize() for item in package['name'].split('-')])}
                    </a>
                </li>
            % endfor
            </ul>
        </div>
    </div>
    <div class="header">
        <div class="hero-unit" id="setup">
            <h1>Automatic Setup</h1>
            <p>To set up this repository in your Linux distribution, execute: <code>curl ${setup_url} | sh -</code></p>
        </div>
    </div>
    <div class="container">
        <div class="row" id="inventory">
            <div class="span12">
                % for package in metadata['packages']:
                <section id="${package['name']}">
                    <div class="page-header">
                        <h1>${' '.join([item.capitalize() for item in package['name'].split('-')])}</h1>
                    </div>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>version</th>
                                <th>platform</th>
                                <th>architecture</th>
                                <th>link</th>
                            </tr>
                        </thead>
                        <tbody>
                            % for release in package['releases']:
                            % for distribution in release['distributions']:
                            <tr>
                                <td>${release['version']}</td>
                                <td>${distribution['platform']}</td>
                                <td>${distribution['architecture']}</td>
                                <td><a href="${ftp_url}${distribution['filepath']}">download</a></td>
                            </tr>
                            % endfor
                            % endfor
                        </tbody>
                    </table>
                </section>
                % endfor
            </div>
        </div>
    </div>
</body>
</html>
