<!DOCTYPE html>
<html lang="en">

  <head>
    <meta charset="utf-8">
    <title>
    </title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="">
    <meta name="author" content="">
    <!-- Le styles -->
    <link href="assets/css/bootstrap.css" rel="stylesheet">
    <style>
      body { padding-top: 60px; /* 60px to make the container go all the way
      to the bottom of the topbar */}
      .big-code { font-size: 150%; }
    </style>
    <link href="assets/css/bootstrap-responsive.css" rel="stylesheet">
    <!-- Le HTML5 shim, for IE6-8 support of HTML5 elements -->
    <!--[if lt IE 9]>
      <script src="http://html5shim.googlecode.com/svn/trunk/html5.js">
      </script>
    <![endif]-->
    <!-- Le fav and touch icons -->
    <link rel="shortcut icon" href="assets/ico/favicon.ico">
    <link rel="apple-touch-icon-precomposed" sizes="144x144" href="assets/ico/apple-touch-icon-144-precomposed.png">
    <link rel="apple-touch-icon-precomposed" sizes="114x114" href="assets/ico/apple-touch-icon-114-precomposed.png">
    <link rel="apple-touch-icon-precomposed" sizes="72x72" href="assets/ico/apple-touch-icon-72-precomposed.png">
    <link rel="apple-touch-icon-precomposed" href="assets/ico/apple-touch-icon-57-precomposed.png">
    <style>
      undefined
    </style>
  </head>

  <body>
    <div class="navbar navbar-fixed-top navbar-inverse">
      <div class="navbar-inner">
        <div class="container-fluid">
          <a class="btn btn-navbar" data-toggle="collapse" data-target=".nav-collapse">
            <span class="icon-bar">
            </span>
            <span class="icon-bar">
            </span>
            <span class="icon-bar">
            </span>
          </a>
          <a class="brand" href="#">
            Application Repository
          </a>
        </div>
      </div>
    </div>
    <div class="container-fluid">
      <div class="row-fluid">
        <div class="span3">
          <div class="well sidebar-nav affix">
            <ul class="nav nav-list">
              <li class="nav-header">
                Available packages
              </li>
              <li>
              </li>

              % for package in metadata['packages']:
              <li class="">
                <a href="#${package['name']}">${package['display_name']}</a>
              </li>
              % endfor
            </ul>
          </div>
        </div>
        <div class="span9">
          <div class="hero-unit">
            <div>
              <h1>
                Setting up the repository
              </h1>
              <p>
                <br>
              </p>
              <p>
                To set up this repository in your Linux distribution, execute:&nbsp;
              </p>
              <p>
                <code class="big-code">curl ${setup_url} | sh -</code>
                <br>
              </p>
            </div>
          </div>
          % for package in metadata['packages']:
          <hr id="${package['name']}">
          <div class="row-fluid">
            <div class="span9">
                <h2>${package['display_name']}</h2>
                <h4>Installation instructions:</h3>
                <p>
                <div class="row-fluid">
                    <div class="span2">
                    <span class="label label-info">redhat/centos</span>
                    </div>
                    <div class="span10">
                        <code>yum install -y ${package['name']}</code>
                    </div>
                </div>
                <div class="row-fluid">
                    <div class="span2">
                    <span class="label label-info">ubuntu</span>
                    </div>
                    <div class="span10">
                        <code>apt-get install -y ${package['name']}</code>
                    </div>
                </div>
                <div class="row-fluid">
                    <div class="span2">
                    <span class="label label-info">windows/other</span>
                    </div>
                    <div class="span10">
                        Download the package manually from the table below
                    </div>
                </div>
                <table class="table download-links">
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
            </div>
          </div>
          % endfor
          <hr>
        </div>
      </div>
    </div>
    <script src="static/jquery-1.8.1.min.js">
    </script>
    <script src="static/jquery.dataTables.min.js">
    </script>
    <script src="assets/js/bootstrap.js">
    </script>
    <script>
        var options = new Object();
        options.bPaginate = false;
        options.bSort = false;
        options.bProcessing = false;
        options.bInfo = false;
        options.bAutoWidth = true;
        /*options.aoColumnDefs = [ {"asSorting": ['desc']}];*/
        $(document).ready(function() {$(".download-links").dataTable(options);});
    </script>
  </body>

</html>
