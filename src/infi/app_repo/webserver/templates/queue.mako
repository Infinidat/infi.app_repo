<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title></title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="description" content="">
        <meta name="author" content="">
        <!-- Le styles -->
        <link href="/assets/css/bootstrap.css" rel="stylesheet">
        <style>
            body {
                padding-top: 60px;
                  /* 60px to make the container go all the way to the bottom of the topbar */
            }
            .big-code {
                font-size: 150%;
            }
        </style>
        <link href="/assets/css/bootstrap-responsive.css" rel="stylesheet">
        <!-- Le HTML5 shim, for IE6-8 support of HTML5 elements -->
        <!--[if lt IE 9]>
            <script src="http://html5shim.googlecode.com/svn/trunk/html5.js">

            </script>
        <![endif]-->
        <!-- Le fav and touch icons -->
        <link rel="shortcut icon" href="/favicon.ico">
        <link rel="apple-touch-icon-precomposed" sizes="144x144" href="/assets/ico/apple-touch-icon-144-precomposed.png">
        <link rel="apple-touch-icon-precomposed" sizes="114x114" href="/assets/ico/apple-touch-icon-114-precomposed.png">
        <link rel="apple-touch-icon-precomposed" sizes="72x72" href="/assets/ico/apple-touch-icon-72-precomposed.png">
        <link rel="apple-touch-icon-precomposed" href="/assets/ico/apple-touch-icon-57-precomposed.png">
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
                    <a class="brand" href="#"></a>
                </div>
            </div>
        </div>
        <form method="post">
            <div class="container-fluid">
                <div class="row-fluid">
                    <div class="span2"></div>
                    <div class="span8">
                        <div class="span12">
                            <h1>Task queue:</h1>
                        </div>
                        % for task in tasks:
                        <div class="span12">
                            <div class="span3">
                                ${task['name'].replace('_', ' ').split('.')[-1].capitalize()}
                            </div>
                            <div class="span6">
                                % if task['name'].endswith('_package'):
                                ${eval(task['args'])[-1].split('/')[-1].rsplit('.', 1)[0]}
                                % endif
                            </div>
                            <div class="span3">
                                ${'Running' if task['worker_pid'] else 'Pending'}
                            </div>
                        </div>
                        % endfor
                    </div>
                    <div class="span2"></div>
                </div>
            </div>
        </form>
        <script src="/static/jquery-1.8.1.min.js"></script>
        <script src="/static/jquery.dataTables.min.js"></script>
        <script src="/assets/js/bootstrap.js"></script>

    </body>
</html>
