<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title></title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="">
        <meta name="author" content="">
        <!-- Le styles -->
        <link href="assets/css/bootstrap.css" rel="stylesheet">
        <link href="assets/css/apprepo.css" rel="stylesheet">
        <style>
            body {
                padding-top: 60px;
                  /* 60px to make the container go all the way to the bottom of the topbar */
            }
            .big-code {
                font-size: 150%;
            }
        </style>
        <link href="assets/css/bootstrap-responsive.css" rel="stylesheet">
        <!-- Le HTML5 shim, for IE6-8 support of HTML5 elements -->
        <!--[if lt IE 9]>
            <script src="http://html5shim.googlecode.com/svn/trunk/html5.js">

            </script>
        <![endif]-->
        <!-- Le fav and touch icons -->
        <link rel="shortcut icon" href="favicon.ico">
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
                 <div class="navbar-header"> PACKAGE  </div><br/>
                 <hr class="nav-line" />
            </div>
        </div>
        <div class="container-fluid">
        <hr class="nav-line-top">
                <div class="span3">
                    <div class="well sidebar-nav affix">
                        <img src='assets/img/top_icon.png' class="logo-icon"/><br/>
                        <ul class="nav nav-list">
                            <li class="">
                                <hr class="nav-line"/>
                                <a href="#hero">Setting up the repository</a>
                                <hr class="nav-line"/>
                            </li>
                            <li class="nav-header">
                                Available packages
                            </li>
                            % for package in metadata['packages']:
                            <li class="">
                                <a href="#${package['name']}">${package['display_name']}</a>
                            </li>
                            % endfor
                    </div>
                </div>

                <div class="span9" id="hero">
                    <div class="hero-unit">
                        <div class='page-header'>Package Repository</div>

                        <div class='setup-header'>Setup Instructions</div>
                        <hr class="nav-line-top">
                        <br><br>
                        <h2>
                            <img src="assets/img/step-icon.png" class="step-icon"/>&nbsp;
                                    Step 1 (first time only)
                        </h2>

                        <div class="row-fluid">
                            <div class="span3">
                                <table class="step-app-table">
                                    <tr>
                                        <td class='os-cell'><img src="assets/img/centos.png" class="os-icon"/>CentOS</td>
                                        <td class='os-cell'><img src="assets/img/redhat.png" class="os-icon"/>Red Hat</td>
                                        <td class='os-cell'><img src="assets/img/ubuntu.png" class="os-icon"/>Ubuntu</td>
                                        <td class='text-cell'>Execute in shell: <code>curl ${setup_url} | sudo sh -</code></td>
                                    </tr>
                                    <tr>
                                        <td class='os-cell'><img src="assets/img/vmware.png" class="os-icon"/>VMware</td>
                                        <td class='os-cell'><img src="assets/img/windows.png" class="os-icon"/>Windows</td>
                                        <td class='os-cell'><img src="assets/img/unkown.jpg" class="os-icon"/>Other OS</td>
                                        <td class='text-cell'>Skip to step 2</td>
                                    </tr>
                                </table>
                            </div>
                        </div>
                        <h2>
                            <img src="assets/img/step-icon.png" class="step-icon"/>&nbsp;
                            Step 2
                        </h2>
                        <p>
                            Choose a package from the list on the left
                        </p>
                    </div>
                    <br>
                    <h1 class="packages-header">
                        Available packages
                    </h1>
                    <hr class="nav-line-top">
                    % for package in metadata['packages']:
                    <hr id="${package['name']}" style="visibility:hidden">
                    <br>
                    <div class="row-fluid">
                        <div class="span9">
                            <h2><img src="assets/img/package.png" class='package-icon'/>&nbsp ${package['display_name']} &nbsp
                                <span class="label ver">${package['releases'][0]['version']}</span>
                            </h2>
                            <h3>Installation instructions</h3>
                            % if any([('redhat' in distribution['platform'] or 'centos' in distribution['platform']) for distribution in package['releases'][0]['distributions']]):
                            <div class="row-fluid">
                                <div>
                                    <table class="step-app-table">
                                        <tr>
                                            <td class='os-cell'><img src="assets/img/redhat.png" class="os-icon"/>Red Hat</td>
                                            <td class='os-cell'><img src="assets/img/centos.png" class="os-icon"/>CentOS</td>
                                            <td class='hidden-cell'></td>
                                            <td class='text-cell'><code>sudo yum install -y ${package['name']}</code></td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                            % endif
                            % if any([('ubuntu' in distribution['platform']) for distribution in package['releases'][0]['distributions']]):
                            <div class="row-fluid">
                                <div>
                                    <table class="step-app-table">
                                        <tr>
                                            <td class='os-cell'><img src="assets/img/ubuntu.png" class="os-icon"/>Ubuntu</td>
                                            <td class='hidden-cell'></td><td class='hidden-cell'></td>
                                            <td class='text-cell'><code>sudo apt-get install -y ${package['name']}</code></td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                            % endif
                            % if any([('windows' in distribution['platform']) for distribution in package['releases'][0]['distributions']]):
                            <div class="row-fluid">
                                <div>
                                     <table class="step-app-table">
                                        <tr>
                                            <td class='os-cell'> <img src="assets/img/windows.png" class="os-icon"/>Windows</td>
                                            <td class='hidden-cell'></td><td class='hidden-cell'></td>
                                            <td class='text-cell'>
                                                <%
                                                [x86] = [item for item in package['releases'][0]['distributions']
                                                                  if item['platform'] == 'windows' and item['architecture'] == 'x86'] or [None]
                                                [x64] = [item for item in package['releases'][0]['distributions']
                                                                  if item['platform'] == 'windows' and item['architecture'] == 'x64'] or [None]
                                                %>
                                                <span class="windows-x86" style="display:none;">
                                                    % if x86:
                                                    Download and install the <a href="${ftp_url}${x86['filepath']}"> package for 32-bit Windows</a>
                                                    % else:
                                                    There is no package for 32-bit windows.
                                                    % endif
                                                </span>
                                                <span class="windows-x64" style="display:none;">
                                                    % if x64:
                                                    Download and install the <a href="${ftp_url}${x64['filepath']}"> package for 64-bit Windows</a>
                                                    % else:
                                                    There is no package for 64-bit windows.
                                                    % endif
                                                </span>
                                                <span class="windows-undef" style="display:none;">
                                                    % if x86 is None and x64 is None:
                                                    There are no packages available for Windows.
                                                    % else:
                                                    <%
                                                    available_packages = []
                                                    if x86:
                                                        available_packages.append(dict(filepath=x86['filepath'],
                                                                                  description = 'package for 32-bit Windows'))
                                                    if x64:
                                                        available_packages.append(dict(filepath=x64['filepath'],
                                                                                  description = 'package for 64-bit Windows'))
                                                    formatted = ' or '.join(['<a href="{}{}">{}</a>'.format(ftp_url, item['filepath'], item['description']) for item in available_packages])
                                                    %>
                                                    % endif
                                                    Download and install the ${formatted}.
                                                </span>
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                            % endif
                            % if any([('vmware' in distribution['platform']) for distribution in package['releases'][0]['distributions']]):
                            <div class="row-fluid">
                                <div >
                                    <table class="step-app-table">
                                        <tr>
                                            <td class='os-cell'><img src="assets/img/vmware.png" class="os-icon"/>VMware</td>
                                            <td class='hidden-cell'></td><td class='hidden-cell'></td>
                                            <td class='text-cell'>
                                                <%
                                                [distribution] = [distribution for distribution in package['releases'][0]['distributions']
                                                                  if distribution['platform'] == 'vmware-esx' and distribution['architecture'].endswith('OVF10')]
                                                 %>
                                                Download and deploy <a href="${ftp_url}${distribution['filepath']}">this</a> appliance in vCenter.
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                            % endif
                            <h3>Upgrade instructions</h3>
                            % if any([('redhat' in distribution['platform'] or 'centos' in distribution['platform']) for distribution in package['releases'][0]['distributions']]):
                            <div class="row-fluid">
                                <div>
                                    <table class="step-app-table">
                                        <tr>
                                            <td class='os-cell'><img src="assets/img/redhat.png" class="os-icon"/>Red Hat</td>
                                            <td class='os-cell'><img src="assets/img/centos.png" class="os-icon"/>CentOS</td>
                                            <td class='hidden-cell'></td>
                                            <td class='text-cell'><code>sudo yum makecache; sudo yum update -y ${package['name']}</code></td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                            % endif
                            % if any([('ubuntu' in distribution['platform']) for distribution in package['releases'][0]['distributions']]):
                            <div class="row-fluid">
                                <div>
                                    <table class="step-app-table">
                                        <tr>
                                            <td class='os-cell'><img src="assets/img/ubuntu.png" class="os-icon"/>Ubuntu</td>
                                            <td class='hidden-cell'></td><td class='hidden-cell'></td>
                                            <td class='text-cell'><code>sudo apt-get update; sudo apt-get install -y ${package['name']}</code></td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                            % endif
                            % if any([('windows' in distribution['platform']) for distribution in package['releases'][0]['distributions']]):
                            <div class="row-fluid">
                                <div>
                                    <table class="step-app-table">
                                        <tr>
                                            <td class='os-cell'><img src="assets/img/windows.png" class="os-icon"/>Windows</td>
                                            <td class='hidden-cell'></td><td class='hidden-cell'></td>
                                            <td class='text-cell'>
                                                <%
                                                [x86] = [item for item in package['releases'][0]['distributions']
                                                                  if item['platform'] == 'windows' and item['architecture'] == 'x86'] or [None]
                                                [x64] = [item for item in package['releases'][0]['distributions']
                                                                  if item['platform'] == 'windows' and item['architecture'] == 'x64'] or [None]
                                                %>
                                                <span class="windows-x86" style="display:none;">
                                                    % if x86:
                                                    Download and install the <a href="${ftp_url}${x86['filepath']}"> package for 32-bit Windows</a>
                                                    % else:
                                                    There is no package for 32-bit windows.
                                                    % endif
                                                </span>
                                                <span class="windows-x64" style="display:none;">
                                                    % if x64:
                                                    Download and install the <a href="${ftp_url}${x64['filepath']}"> package for 64-bit Windows</a>
                                                    % else:
                                                    There is no package for 64-bit windows.
                                                    % endif
                                                </span>
                                                <span class="windows-undef" style="display:none;">
                                                    % if x86 is None and x64 is None:
                                                    There are no packages available for Windows.
                                                    % else:
                                                    <%
                                                    available_packages = []
                                                    if x86:
                                                        available_packages.append(dict(filepath=x86['filepath'],
                                                                                  description = 'package for 32-bit Windows'))
                                                    if x64:
                                                        available_packages.append(dict(filepath=x64['filepath'],
                                                                                  description = 'package for 64-bit Windows'))
                                                    formatted = ' or '.join(['<a href="{}{}">{}</a>'.format(ftp_url, item['filepath'], item['description']) for item in available_packages])
                                                    %>
                                                    % endif
                                                    Download and install the ${formatted}.
                                                </span>
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                            % endif
                            % if any([('vmware' in distribution['platform']) for distribution in package['releases'][0]['distributions']]):
                            <div class="row-fluid">
                                <div>
                                    <table class="step-app-table">
                                        <tr>
                                            <td class='os-cell'><img src="assets/img/vmware.png" class="os-icon"/>VMware</td>
                                            <td class='hidden-cell'></td><td class='hidden-cell'></td>
                                            <td class='text-cell'>
                                                <%
                                                [distribution] = [distribution for distribution in package['releases'][0]['distributions']
                                                                  if distribution['platform'] == 'vmware-esx' and distribution['architecture'].endswith('OVF10')]
                                                 %>
                                                Upgrade the appliance through vCenter by using the VMware Update Manager Plug-in.
                                                <br>
                                                If vCenter does not have internet connectivity to this repository, you can download a ZIP/ISO update file from the list below and upload it to the VMware Update Manager.
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                            </div>
                            % endif

                            <br>
                            <div class="show-other">
                                <i class="icon-chevron-right"></i> Other versions and platforms...
                            </div>
                            <br>
                            <div class="table_wrapper">
                                <table class="table table-bordered table-hover download-links">
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
                        </div>
                        % endfor

                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="static/jquery-1.8.1.min.js"></script>
        <script src="static/jquery.dataTables.min.js"></script>
        <script src="assets/js/bootstrap.js"></script>
        <script>
            var options = new Object();
            options.bPaginate = true;
            options.bSort = false;
            options.bProcessing = false;
            options.bInfo = false;
            options.bAutoWidth = true;
            /*options.aoColumnDefs = [{"asSorting ": ['desc']}];*/
            $(document).ready(function() {
                $.fn.dataTableExt.oStdClasses.sPagePrevEnabled = "btn btn-info";
                $.fn.dataTableExt.oStdClasses.sPagePrevDisabled = "btn btn-info disabled";
                $.fn.dataTableExt.oStdClasses.sPageNextEnabled = "btn btn-info";
                $.fn.dataTableExt.oStdClasses.sPageNextDisabled = "btn btn-info disabled";
                $(".download-links").dataTable(options);
            });
        </script>
        <script>
            $(function() {
                $(".show-other").click(function() {
                    var table = $(".table_wrapper", $(this).parent());
                    if (table.is(':visible')) {
                        $('i', this).removeClass('icon-chevron-down').addClass('icon-chevron-right');
                        table.slideUp();
                    }
                    else {
                        $('i', this).removeClass('icon-chevron-right').addClass('icon-chevron-down');
                        table.slideDown();
                    }
                })
            })
        </script>
        <script>
            var OSName="Unknown OS";
            if (navigator.appVersion.indexOf("Win")!=-1) {
                if (navigator.userAgent.indexOf('WOW64')>-1 || window.navigator.platform=='Win64') {
                    $(".windows-x64").show();
                }
                else {
                    $(".windows-x86").show();
                }
            }
            else {
                $(".windows-undef").show();
            }

            // Set the size of the sidebar
            function resize_sidebar() {
                $('.sidebar-nav').height($(window).height() - 120);
            }
            resize_sidebar();
            $(window).on('resize', resize_sidebar);

        </script>
    </body>
</html>
