<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title></title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="">
        <meta name="author" content="">
        <!-- Le styles -->
        <link href="${url_for('static', filename='css/bootstrap.css')}" rel="stylesheet">
        <link href="${url_for('static', filename='css/apprepo.css')}" rel="stylesheet">
        <style>
            body {
                padding-top: 60px;
                  /* 60px to make the container go all the way to the bottom of the topbar */
            }
            .big-code {
                font-size: 150%;
            }
        </style>
        <link href="${url_for('static', filename='css/bootstrap-responsive.css')}" rel="stylesheet">
        <!-- Le HTML5 shim, for IE6-8 support of HTML5 elements -->
        <!--[if lt IE 9]>
            <script src="http://html5shim.googlecode.com/svn/trunk/html5.js">

            </script>
        <![endif]-->
        <!-- Le fav and touch icons -->
        <link rel="shortcut icon" href="favicon.ico">
        <link rel="apple-touch-icon-precomposed" sizes="144x144" href="${url_for('static', filename='ico/apple-touch-icon-144-precomposed.png')}">
        <link rel="apple-touch-icon-precomposed" sizes="114x114" href="${url_for('static', filename='ico/apple-touch-icon-114-precomposed.png')}">
        <link rel="apple-touch-icon-precomposed" sizes="72x72" href="${url_for('static', filename='ico/apple-touch-icon-72-precomposed.png')}">
        <link rel="apple-touch-icon-precomposed" href="${url_for('static', filename='ico/apple-touch-icon-57-precomposed.png')}">
        <style>
            undefined
        </style>
    </head>
    <body>
        <div class="navbar navbar-fixed-top navbar-inverse">
            <div class="navbar-inner">
            </div>
        </div>
        <div class="container-fluid">
            <div class="row-fluid">
                <div class="span3">
                    <div class="well sidebar-nav affix" style="overflow-y: scroll;">
                        <ul class="nav nav-list">
                            <li class="">
                                <a href="#hero">Setting up the repository</a>
                            </li>
                            <li class="nav-header">
                                Available packages
                            </li>
                    </div>
                </div>
                <div class="span9" id="hero">
                    <div class="hero-unit">
                        <h1>Setup Instructions</h1>
                        <br>
                        <h2>
                            Step 1 (first time only)
                        </h2>
                        <div class="row-fluid">
                            <div class="span3">
                                <span class="label label-important">redhat</span>
                                <span class="label label-important">oracle</span>
                                <span class="label label-important">centos</span>
                                <span class="label label-warning">ubuntu</span>
                            </div>
                            <div class="span9">
                                Execute in shell: <code>curl ${setup_url} | sudo sh -</code>
                            </div>
                        </div>
                        <hr style="margin:0px; margin-bottom: 10px;">
                        <div class="row-fluid">
                            <div class="span3">
                                <span class="label label-info">vmware</span>
                                <span class="label label-success">windows</span>
                                <span class="label label-inverse">other</span>
                            </div>
                            <div class="span9">
                                Skip to step 2
                            </div>
                        </div>
                        <br>
                        <h2>
                            Step 2
                        </h2>
                        <p>
                            Choose a package from the list on the left
                        </p>
                    </div>
                    <br>
                    <div style="height: 1080px">
                    </div>
                    <h1>
                        Available packages
                    </h1>
                        <hr>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script src="${url_for('static', filename='jquery-1.8.1.min.js')}"></script>
        <script src="${url_for('static', filename='jquery.dataTables.min.js')}"></script>
        <script src="${url_for('static', filename='js/bootstrap.js')}"></script>
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
